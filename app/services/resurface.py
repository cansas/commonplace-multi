"""Daily resurface logic — selects highlights for today's review session."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Highlight, ReviewLog, Source
from app.services.settings_service import get_review_count
from app.dates import today_start_utc


async def get_random_highlights(db: AsyncSession, count: int = 10, exclude_ids: list = None):
    """Random selection for daily review."""
    # Count total matching, pick random offset
    total_q = select(func.count(Highlight.id))
    if exclude_ids:
        total_q = total_q.where(Highlight.id.notin_(exclude_ids))
    result = await db.execute(total_q)
    total = result.scalar() or 0
    if total == 0:
        return []
    offset = random.randint(0, max(0, total - count))
    query = select(Highlight)
    if exclude_ids:
        query = query.where(Highlight.id.notin_(exclude_ids))
    query = query.offset(offset).limit(count)
    result = await db.execute(query)
    return result.scalars().all()


async def get_dashboard_counts(db: AsyncSession, user_id: int = 0):
    """Return stats for the dashboard, scoped to user_id if provided."""
    # Total highlights
    q = select(func.count(Highlight.id))
    if user_id:
        q = q.where(Highlight.user_id == user_id)
    result = await db.execute(q)
    total = result.scalar() or 0

    # Distinct books
    q = select(func.count(func.distinct(Highlight.book_title)))
    if user_id:
        q = q.where(Highlight.user_id == user_id)
    result = await db.execute(q)
    books = result.scalar() or 0

    # Reviews done today
    today_start = today_start_utc()
    result = await db.execute(
        select(func.count(ReviewLog.id))
        .where(ReviewLog.reviewed_at >= today_start)
    )
    done_today = result.scalar() or 0

    # Daily remaining = min(limit - done, total_unreviewed)
    daily_limit = get_review_count()
    remaining = max(0, daily_limit - done_today)

    return total, books, remaining


async def get_recent_sources(db: AsyncSession, user_id: int = 0, limit: int = 5):
    """Recent import sources for a specific user."""
    q = select(Source)
    if user_id:
        q = q.where(Source.user_id == user_id)
    result = await db.execute(
        q.order_by(Source.last_import_at.desc().nullslast())
        .limit(limit)
    )
    return result.scalars().all()
