"""Daily review and spaced repetition routes."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Highlight, ReviewLog
from app.services.resurface import get_random_highlights, get_due_highlights
from app.services.spaced_repetition import sm2_calc, get_next_review_date
from app.schemas import ReviewRating
from datetime import datetime

router = APIRouter(tags=["review"])

_jinja = None


def init(templates):
    global _jinja
    _jinja = templates


@router.get("/review", response_class=HTMLResponse)
async def review_page(
    request: Request,
    mode: str = Query(default="random"),
    db: AsyncSession = Depends(get_db),
):
    count = 10

    if mode == "spaced":
        highlights = await get_due_highlights(db, count)
    else:
        highlights = await get_random_highlights(db, count)

    # Build review session list
    review_list = []
    for h in highlights:
        # Check if already reviewed today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        existing = await db.execute(
            select(func.count(ReviewLog.id)).where(
                ReviewLog.highlight_id == h.id,
                ReviewLog.reviewed_at >= today_start,
            )
        )
        reviewed_today = existing.scalar() or 0

        review_list.append({
            "id": h.id,
            "text": h.text,
            "note": h.note,
            "page": h.page,
            "chapter": h.chapter,
            "book_title": h.book_title,
            "book_author": h.book_author,
            "tags": [t.name for t in h.tags],
            "reviewed_today": reviewed_today > 0,
        })

    return _jinja.TemplateResponse(
        request,
        "review.html",
        {
            "active_page": "review",
            "highlights": review_list,
            "review_mode": mode,
            "total_count": len(review_list),
        },
    )


@router.post("/api/review/{hl_id}")
async def rate_highlight(
    hl_id: int,
    data: ReviewRating,
    db: AsyncSession = Depends(get_db),
):
    hl = await db.get(Highlight, hl_id)
    if not hl:
        return {"error": "Highlight not found"}, 404

    # Get last review for this highlight
    last_review = await db.execute(
        select(ReviewLog)
        .where(ReviewLog.highlight_id == hl_id)
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(1)
    )
    last = last_review.scalar_one_or_none()

    prev_ease = last.ease_factor if last else 2.5
    prev_interval = last.interval if last else 0
    prev_reps = last.repetitions if last else 0

    ease, interval, reps = sm2_calc(data.rating, prev_ease, prev_interval, prev_reps)

    log = ReviewLog(
        highlight_id=hl_id,
        rating=data.rating,
        ease_factor=ease,
        interval=interval,
        repetitions=reps,
        next_review_at=get_next_review_date(interval),
    )
    db.add(log)
    await db.commit()

    return {
        "ok": True,
        "ease_factor": ease,
        "interval": interval,
        "repetitions": reps,
        "next_review_at": log.next_review_at.isoformat() if log.next_review_at else None,
    }


@router.get("/api/review/next")
async def next_highlight(
    mode: str = "random",
    db: AsyncSession = Depends(get_db),
):
    count = 1
    if mode == "spaced":
        hls = await get_due_highlights(db, count)
    else:
        hls = await get_random_highlights(db, count)

    if not hls:
        return {"done": True}

    h = hls[0]
    return {
        "id": h.id,
        "text": h.text,
        "note": h.note,
        "book_title": h.book_title,
        "book_author": h.book_author,
        "tags": [t.name for t in h.tags],
    }


from sqlalchemy import select, func
