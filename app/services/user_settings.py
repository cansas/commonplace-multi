"""DB-backed per-user settings service.

Replaces file-based ``settings_service.py`` for user-scoped settings
(theme, review_count, hardcover_api_key, push prefs, etc.).
Global settings (Mailjet config, digest prefs) stay in the file-backed
``settings_service.py`` module.

Usage::

    from app.services.user_settings import get, set_

    theme = await get(db, user_id, "theme", "modern")
    await set_(db, user_id, "theme", "dark")
"""

import json
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserSetting


async def get(
    db: AsyncSession,
    user_id: int,
    key: str,
    default: Any = None,
) -> Any:
    """Fetch a per-user setting by key.

    Returns the parsed JSON value, or *default* when the key is not set.
    """
    result = await db.execute(
        select(UserSetting).where(
            UserSetting.user_id == user_id,
            UserSetting.key == key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return default
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, TypeError, ValueError):
        return row.value


async def set_(
    db: AsyncSession,
    user_id: int,
    key: str,
    value: Any,
) -> None:
    """Upsert a per-user setting.

    Value is JSON-serialised for storage so we can store strings, numbers,
    booleans, and lists uniformly.
    """
    from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

    serialised = json.dumps(value, ensure_ascii=False)

    stmt = sqlite_upsert(UserSetting).values(
        user_id=user_id,
        key=key,
        value=serialised,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "key"],
        set_={"value": stmt.excluded.value},
    )
    await db.execute(stmt)


async def get_all(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Return all settings for a user as a flat dict."""
    result = await db.execute(
        select(UserSetting).where(UserSetting.user_id == user_id)
    )
    out: dict[str, Any] = {}
    for row in result.scalars().all():
        try:
            out[row.key] = json.loads(row.value)
        except (json.JSONDecodeError, TypeError, ValueError):
            out[row.key] = row.value
    return out


async def delete(db: AsyncSession, user_id: int, key: str) -> None:
    """Remove a setting by key (no error if key doesn't exist)."""
    from sqlalchemy import delete as sqla_delete

    await db.execute(
        sqla_delete(UserSetting).where(
            UserSetting.user_id == user_id,
            UserSetting.key == key,
        )
    )


async def migrate_from_file(db: AsyncSession, user_id: int) -> int:
    """Seed *user_settings* from the existing file-backed ``.settings.json``.

    Only migrates keys that belong to the user-scoped domain.
    Returns the number of settings migrated.
    """
    from app.services.settings_service import get_all as get_file_settings

    file_settings = get_file_settings()

    # Keys that belong to the user (not global)
    USER_KEYS = {
        "theme", "review_count", "hardcover_api_key",
        "push_enabled", "push_reminder_time",
        "push_streak_alert_enabled", "push_streak_alert_time",
        "last_push_reminder_sent", "last_push_streak_alert_sent",
        "bookorbit_url", "bookorbit_username", "bookorbit_password",
        "bookorbit_sync_enabled", "bookorbit_last_synced_id",
        "bookorbit_last_synced_at", "bookorbit_disabled_reason",
    }

    count = 0
    for key in USER_KEYS:
        if key in file_settings:
            await set_(db, user_id, key, file_settings[key])
            count += 1
    if count:
        await db.flush()
    return count
