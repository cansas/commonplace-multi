"""Achievement definitions and unlock logic.

Achievements are awarded once per milestone and persisted in the
user_achievements table. Each has a key, label, and witty message.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import UserAchievement

# ── Achievement definitions ─────────────────────────────────────────────────
# Keys are used for idempotent checks. Messages are the witty unlock text.
# The streak threshold is the minimum streak length to unlock.

ACHIEVEMENTS = [
    {
        "key": "streak_7",
        "label": "Streak Starter",
        "icon": "🌱",
        "threshold": 7,
        "message": "Seven days! You've officially outlasted a trial of a streaming service.",
    },
    {
        "key": "streak_30",
        "label": "Whole Month",
        "icon": "🌿",
        "threshold": 30,
        "message": "30 days! You've been highlighting longer than most New Year's resolutions last.",
    },
    {
        "key": "streak_90",
        "label": "The Quarter Pounder",
        "icon": "🌳",
        "threshold": 90,
        "message": "90 days! That's a full season of bad TV you could have watched. Good choice.",
    },
    {
        "key": "streak_180",
        "label": "Half a Year",
        "icon": "🏛️",
        "threshold": 180,
        "message": "Six months! You are more committed than most houseplants get watered.",
    },
    {
        "key": "streak_365",
        "label": "The Yearling",
        "icon": "👑",
        "threshold": 365,
        "message": "A full year! You have officially been consistent longer than the author's writing schedule.",
    },
]


def _get_achievement(key: str) -> dict | None:
    """Look up an achievement definition by key."""
    for a in ACHIEVEMENTS:
        if a["key"] == key:
            return a
    return None


async def check_and_unlock(db: AsyncSession, current_streak: int) -> list[dict]:
    """Check if any new achievements should be unlocked based on the
    current streak. Returns a list of newly unlocked achievements.

    Called after each review submission. Idempotent — will not re-award.
    """
    newly_unlocked = []

    for ach in ACHIEVEMENTS:
        if current_streak < ach["threshold"]:
            continue

        # Check if already unlocked
        existing = await db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == 1,
                UserAchievement.achievement_key == ach["key"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Award it
        db.add(UserAchievement(
            user_id=1,
            achievement_key=ach["key"],
            message=ach["message"],
        ))
        await db.commit()

        newly_unlocked.append({
            "key": ach["key"],
            "label": ach["label"],
            "icon": ach["icon"],
            "message": ach["message"],
        })

    return newly_unlocked


async def get_all_achievements(db: AsyncSession) -> list[dict]:
    """Return all achievement definitions with unlock status."""
    # Fetch unlocked for user 1
    result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == 1)
    )
    unlocked = {ua.achievement_key: ua for ua in result.scalars().all()}

    output = []
    for ach in ACHIEVEMENTS:
        ua = unlocked.get(ach["key"])
        output.append({
            "key": ach["key"],
            "label": ach["label"],
            "icon": ach["icon"],
            "message": ach["message"] if not ua else ua.message,
            "unlocked": ua is not None,
            "unlocked_at": ua.unlocked_at.isoformat() if ua else None,
        })
    return output


async def backfill_achievements(db: AsyncSession, current_streak: int) -> int:
    """On startup, check and award any achievements already earned.
    Returns the number of newly backfilled achievements.
    """
    count = 0
    for ach in ACHIEVEMENTS:
        if current_streak < ach["threshold"]:
            continue
        existing = await db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == 1,
                UserAchievement.achievement_key == ach["key"],
            )
        )
        if not existing.scalar_one_or_none():
            db.add(UserAchievement(
                user_id=1,
                achievement_key=ach["key"],
                message=ach["message"],
            ))
            count += 1
    if count > 0:
        await db.commit()
    return count
