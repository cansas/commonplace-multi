"""Scheduler for daily email digest + BookOrbit sync.

Uses APScheduler to check every 5 minutes whether the digest should be sent,
and every 15 minutes whether BookOrbit sync should run.
Relies on ``app.services.settings_service`` as the single source of truth
for all configuration.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.settings_service import get, set as set_setting

logger = logging.getLogger(__name__)

_SCHEDULER = None
_BOOKORBIT_SYNC_INTERVAL = 15  # minutes between BookOrbit sync checks


async def check_and_send_digest():
    """Check if it's time to send the digest and send if so."""
    if not get("email_digest_enabled", False):
        return
    if not get("mailjet_api_key") or not get("mailjet_secret_key"):
        return
    if not get("email_to_addr"):
        return

    # Check already-sent date
    _CENTRAL = ZoneInfo("America/Chicago")
    today_str = datetime.now(_CENTRAL).date().isoformat()
    if get("last_digest_sent_date") == today_str:
        return  # Already sent today

    # Check if current time >= configured send time
    now = datetime.now(_CENTRAL)
    send_time_str = get("email_digest_time", "07:00")
    try:
        send_hour, send_min = map(int, send_time_str.split(":"))
    except (ValueError, AttributeError):
        return  # Invalid time config

    if now.hour < send_hour or (now.hour == send_hour and now.minute < send_min):
        return  # Too early

    # ── Time to send! ──
    logger.info("Sending daily email digest...")

    api_key = get("mailjet_api_key")
    secret_key = get("mailjet_secret_key")
    from_name = get("email_from_name", "Commonplace")
    from_email = get("email_from_addr", "")
    to_email = get("email_to_addr")

    if not from_email:
        logger.warning("Cannot send digest: from_email is not set")
        return

    try:
        from app.database import async_session
        from app.services.email_digest import send_email_via_mailjet, build_digest_html

        async with async_session() as db:
            html_content = await build_digest_html(db)

        if not html_content or "No highlights" in html_content:
            logger.info("No highlights to send in digest today")
            # Still mark as sent so we don't keep trying
        else:
            result = await send_email_via_mailjet(
                api_key, secret_key, from_name, from_email, to_email,
                "Commonplace — Your Daily Review",
                html_content,
            )
            logger.info("Digest sent: %s", result.get("Messages", [{}])[0].get("Status", "?"))

        # Mark as sent today
        set_setting("last_digest_sent_date", today_str)

    except Exception as e:
        logger.error("Failed to send digest: %s", e)


async def check_and_run_bookorbit_sync():
    """Check BookOrbit sync for every user and run it if enabled."""
    from app.database import async_session
    from app.models import User
    from sqlalchemy import select

    async with async_session() as db:
        users = (await db.execute(select(User))).scalars().all()
    user_ids = [u.id for u in users] if users else [1]

    for uid in user_ids:
        try:
            async with async_session() as db:
                from app.services.bookorbit_sync import sync_from_bookorbit
                config_enabled = await _get_user_setting(db, uid, "bookorbit_sync_enabled", False)
                if not config_enabled:
                    continue
                result = await sync_from_bookorbit(db, user_id=uid)
                if result["posted"] > 0 or result["errors"] > 0:
                    logger.info(
                        "BookOrbit sync (user %d): posted=%d skipped=%d errors=%d",
                        uid, result["posted"], result["skipped"], result["errors"],
                    )
        except Exception as e:
            logger.error("BookOrbit sync failed for user %d: %s", uid, e)


async def _get_user_setting(db, user_id: int, key: str, default=None):
    from app.services.user_settings import get as _ug
    return await _ug(db, user_id, key, default)


def start_scheduler():
    """Start the background scheduler that checks for digest delivery and BookOrbit sync."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        return

    _SCHEDULER = AsyncIOScheduler()
    # Check digest every 5 minutes
    _SCHEDULER.add_job(check_and_send_digest, "interval", minutes=5, id="digest_check")
    # Check BookOrbit sync every 15 minutes
    _SCHEDULER.add_job(check_and_run_bookorbit_sync, "interval", minutes=_BOOKORBIT_SYNC_INTERVAL, id="bookorbit_sync")
    _SCHEDULER.start()
    logger.info("Scheduler started (digest: 5min, BookOrbit sync: %dmin)", _BOOKORBIT_SYNC_INTERVAL)


def stop_scheduler():
    """Shut down the scheduler cleanly."""
    global _SCHEDULER
    if _SCHEDULER:
        _SCHEDULER.shutdown(wait=False)
        _SCHEDULER = None
        logger.info("Digest scheduler stopped")
