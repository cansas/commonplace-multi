"""
Scheduler for push notification review reminders.

Uses APScheduler to check every 5 minutes whether a reminder or
streak-at-risk alert should be sent. Iterates over all users and
checks each user's per-user push settings. Tracks last-sent dates
in the user_settings table to avoid multiple sends per day.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

_CENTRAL = ZoneInfo("America/Chicago")

logger = logging.getLogger(__name__)

_SCHEDULER = None


async def _check_reminder_for_user(db, user_id: int):
    """Send review reminder for one user if it's time."""
    from app.services.user_settings import get as _get

    push_enabled = await _get(db, user_id, "push_enabled", False)
    if not push_enabled:
        return

    today_str = datetime.now(_CENTRAL).date().isoformat()
    last_sent = await _get(db, user_id, "last_push_reminder_sent", "")
    if last_sent == today_str:
        return

    # Check if current time >= configured reminder time
    now = datetime.now(_CENTRAL)
    reminder_time = await _get(db, user_id, "push_reminder_time", "09:00")
    try:
        hour, minute = map(int, reminder_time.split(":"))
    except (ValueError, AttributeError):
        return

    if now.hour < hour or (now.hour == hour and now.minute < minute):
        return

    # ── Time to check! ──
    from app.routes.review import _reviewed_today_count
    from app.services.user_settings import set_ as _set
    from app.services.push_service import send_push_to_all

    done = await _reviewed_today_count(db, user_id)
        if done > 0:
        # Already reviewed — mark sent so we don't keep reminding
        await _set(db, user_id, "last_push_reminder_sent", today_str)
        await db.commit()
        return

    result = await send_push_to_all(
        title="⏰ Time for your daily review!",
        body="You haven't reviewed any highlights today. Keep your streak alive!",
        db=db,
        url="/review",
        user_id=user_id,
    )
    logger.info("Push reminder for user %d: %s", user_id, result)

    await _set(db, user_id, "last_push_reminder_sent", today_str)
    await db.commit()


async def _check_streak_alert_for_user(db, user_id: int):
    """Send streak-at-risk alert for one user if it's time."""
    from app.services.user_settings import get as _get

    alert_enabled = await _get(db, user_id, "push_streak_alert_enabled", False)
    if not alert_enabled:
        return

    today_str = datetime.now(_CENTRAL).date().isoformat()
    last_sent = await _get(db, user_id, "last_push_streak_alert_sent", "")
    if last_sent == today_str:
        return

    now = datetime.now(_CENTRAL)
    alert_time = await _get(db, user_id, "push_streak_alert_time", "20:00")
    try:
        hour, minute = map(int, alert_time.split(":"))
    except (ValueError, AttributeError):
        return

    if now.hour < hour or (now.hour == hour and now.minute < minute):
        return

    # ── Time to check! ──
    from app.routes.review import _reviewed_today_count
    from app.services.streaks import calculate_streaks
    from app.services.user_settings import set_ as _set
    from app.services.push_service import send_push_to_all

    streaks = await calculate_streaks(db, user_id)
    current_streak = streaks.get("current", 0)
    if current_streak == 0:
        return

    done = await _reviewed_today_count(db, user_id)
        if done > 0:
        return

    result = await send_push_to_all(
        title="🔥 Your streak is at risk!",
        body=f"You'll lose your {current_streak}-day streak! Just one highlight can save it.",
        db=db,
        url="/review",
        user_id=user_id,
    )
    logger.info("Push streak alert for user %d: %s", user_id, result)

    await _set(db, user_id, "last_push_streak_alert_sent", today_str)
    await db.commit()


async def _check_all():
    """Run both push checks for every user — called every 5 minutes."""
    from app.database import async_session
    from app.models import User
    from sqlalchemy import select

    try:
        async with async_session() as db:
            users_result = await db.execute(select(User).order_by(User.id))
            users = users_result.scalars().all()

            for user in users:
                try:
                    await _check_reminder_for_user(db, user.id)
                except Exception as e:
                    logger.error("Push reminder for user %d failed: %s", user.id, e)
                try:
                    await _check_streak_alert_for_user(db, user.id)
                except Exception as e:
                    logger.error("Push streak alert for user %d failed: %s", user.id, e)
    except Exception as e:
        logger.error("Push scheduler iteration failed: %s", e)


def start_scheduler():
    """Start the background scheduler that checks for push delivery."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        return

    _SCHEDULER = AsyncIOScheduler()
    _SCHEDULER.add_job(_check_all, "interval", minutes=5, id="push_check")
    _SCHEDULER.start()
    logger.info("Push scheduler started (checking every 5 minutes)")


def stop_scheduler():
    """Shut down the scheduler cleanly."""
    global _SCHEDULER
    if _SCHEDULER:
        _SCHEDULER.shutdown(wait=False)
        _SCHEDULER = None
        logger.info("Push scheduler stopped")
