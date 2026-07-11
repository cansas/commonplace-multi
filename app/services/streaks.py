"""Streak tracking — daily review streaks and stat milestones."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ReviewLog

_CENTRAL = ZoneInfo("America/Chicago")


async def calculate_streaks(db: AsyncSession, user_id: int = 1) -> dict:
    """Return current streak and best-ever streak based on ReviewLog.

    Both are calendar-day streaks in Central time (matching the daily
    review reset).  The current streak counts consecutive days ending
    with today *or* yesterday (so you don't lose it if you miss a day
    but haven't broken the habit).

    Best streak is persisted per-user in user_settings.
    """
    # Fetch all raw reviewed_at datetimes (full precision, not func.date())
    result = await db.execute(
        select(ReviewLog.reviewed_at,)
        .where(ReviewLog.user_id == user_id)
        .order_by(ReviewLog.reviewed_at.desc())
    )
    rows = result.all()
    if not rows:
        return {"current": 0, "best": await _load_best_streak(db, user_id)}

    # Convert each UTC datetime to Central date in Python
    central_dates = set()
    for row in rows:
        dt = row[0]
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        central_dates.add(
            dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(_CENTRAL).date()
        )

    # Sort unique central dates descending
    sorted_dates = sorted(central_dates, reverse=True)

    # --- Current streak ---
    today = datetime.now(_CENTRAL).date()
    yesterday = today - timedelta(days=1)
    current = 0

    if sorted_dates and sorted_dates[0] in (today, yesterday):
        current = 1
        for i in range(1, len(sorted_dates)):
            expected = sorted_dates[0] - timedelta(days=i)
            if sorted_dates[i] == expected:
                current += 1
            else:
                break

    # Persist best streak per-user
    best = await _load_best_streak(db, user_id)
    if current > best:
        best = current
        await _save_best_streak(db, user_id, best)

    return {"current": current, "best": best}


async def _load_best_streak(db: AsyncSession, user_id: int) -> int:
    """Read the persisted best streak per-user."""
    from app.services.user_settings import get as _ug
    val = await _ug(db, user_id, "best_streak", 0)
    return int(val) if val else 0


async def _save_best_streak(db: AsyncSession, user_id: int, value: int) -> None:
    from app.services.user_settings import set_ as _us
    await _us(db, user_id, "best_streak", value)
    await db.commit()
