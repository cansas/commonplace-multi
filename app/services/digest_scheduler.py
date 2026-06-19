"""
Scheduler for daily email digest.

Uses APScheduler to check every 5 minutes whether the digest should be sent.
Avoids sending multiple times per day by tracking the last-sent date in .settings.json.
"""
import json
import logging
import os
from datetime import datetime, date

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_SCHEDULER = None

_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", ".settings.json"
)


def _read_settings() -> dict:
    try:
        with open(_SETTINGS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_settings(s: dict):
    try:
        os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
        with open(_SETTINGS_FILE, "w") as f:
            json.dump(s, f)
    except Exception as e:
        logger.warning("Failed to write settings: %s", e)


async def _check_and_send():
    """Check if it's time to send the digest and send if so."""
    settings = _read_settings()

    if not settings.get("email_digest_enabled", False):
        return
    if not settings.get("mailjet_api_key") or not settings.get("mailjet_secret_key"):
        return
    if not settings.get("email_to_addr"):
        return

    # Check already-sent date
    today_str = date.today().isoformat()
    if settings.get("last_digest_sent_date") == today_str:
        return  # Already sent today

    # Check if current time >= configured send time
    now = datetime.now()
    send_time_str = settings.get("email_digest_time", "07:00")
    try:
        send_hour, send_min = map(int, send_time_str.split(":"))
    except (ValueError, AttributeError):
        return  # Invalid time config

    if now.hour < send_hour or (now.hour == send_hour and now.minute < send_min):
        return  # Too early

    # ── Time to send! ──
    logger.info("Sending daily email digest...")

    api_key = settings["mailjet_api_key"]
    secret_key = settings["mailjet_secret_key"]
    from_name = settings.get("email_from_name", "Commonplace")
    from_email = settings.get("email_from_addr", "")
    to_email = settings["email_to_addr"]

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
                "📖 Your Daily Commonplace Review",
                html_content,
            )
            logger.info("Digest sent successfully: %s", result.get("Messages", [{}])[0].get("Status", "?"))

        # Mark as sent today
        settings["last_digest_sent_date"] = today_str
        _write_settings(settings)

    except Exception as e:
        logger.error("Failed to send digest: %s", e)


def start_scheduler():
    """Start the background scheduler that checks for digest delivery."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        return

    _SCHEDULER = AsyncIOScheduler()
    # Check every 5 minutes
    _SCHEDULER.add_job(_check_and_send, "interval", minutes=5, id="digest_check")
    _SCHEDULER.start()
    logger.info("Digest scheduler started (checking every 5 minutes)")


def stop_scheduler():
    """Shut down the scheduler cleanly."""
    global _SCHEDULER
    if _SCHEDULER:
        _SCHEDULER.shutdown(wait=False)
        _SCHEDULER = None
        logger.info("Digest scheduler stopped")
