"""Daily review and spaced repetition routes."""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Highlight, ReviewLog
from app.services.resurface import get_random_highlights, get_due_highlights
from app.services.spaced_repetition import sm2_calc, get_next_review_date
from app.schemas import ReviewRating
from app.routes.settings import _settings as review_settings
from datetime import datetime

router = APIRouter(tags=["review"])

_jinja = None


def init(templates):
    global _jinja
    _jinja = templates


def _today_start() -> datetime:
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


async def _count_unreviewed(db) -> int:
    """Count highlights not yet reviewed today."""
    today_start = _today_start()
    reviewed_today = (
        select(ReviewLog.highlight_id)
        .where(ReviewLog.reviewed_at >= today_start)
    )
    result = await db.execute(
        select(func.count(Highlight.id))
        .where(Highlight.id.notin_(reviewed_today))
    )
    return result.scalar() or 0


async def _pick_unreviewed(db, mode: str):
    """Pick one highlight not yet reviewed today."""
    today_start = _today_start()

    if mode == "spaced":
        candidates = await get_due_highlights(db, 20)
    else:
        candidates = await get_random_highlights(db, 20)

    for c in candidates:
        result = await db.execute(
            select(func.count(ReviewLog.id)).where(
                ReviewLog.highlight_id == c.id,
                ReviewLog.reviewed_at >= today_start,
            )
        )
        if (result.scalar() or 0) == 0:
            return c
    return None


@router.get("/review", response_class=HTMLResponse)
async def review_page(
    request: Request,
    mode: str = "",
    db: AsyncSession = Depends(get_db),
):
    if not mode:
        mode = review_settings.get("review_mode", "random")

    total_remaining = await _count_unreviewed(db)
    hl = await _pick_unreviewed(db, mode)

    highlight_data = None
    if hl:
        highlight_data = {
            "id": hl.id,
            "text": hl.text,
            "note": hl.note,
            "page": hl.page,
            "chapter": hl.chapter,
            "book_title": hl.book_title,
            "book_author": hl.book_author,
            "source_type": hl.source_type,
            "tags": [t.name for t in hl.tags],
        }

    return _jinja.TemplateResponse(
        request,
        "review.html",
        {
            "active_page": "review",
            "highlight": highlight_data,
            "review_mode": mode,
            "current_index": 1,
            "total_count": total_remaining or 0,
        },
    )


@router.post("/review/next")
async def review_next(mode: str = ""):
    url = f"/review?mode={mode}" if mode else "/review"
    return RedirectResponse(url=url, status_code=303)


@router.post("/review/skip")
async def review_skip(mode: str = ""):
    url = f"/review?mode={mode}" if mode else "/review"
    return RedirectResponse(url=url, status_code=303)


@router.post("/review/rate")
async def review_rate(
    highlight_id: int = Form(...),
    rating: int = Form(...),
    mode: str = "",
    db: AsyncSession = Depends(get_db),
):
    hl = await db.get(Highlight, highlight_id)
    if not hl:
        return RedirectResponse(url="/review", status_code=303)

    last_review = await db.execute(
        select(ReviewLog)
        .where(ReviewLog.highlight_id == highlight_id)
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(1)
    )
    last = last_review.scalar_one_or_none()
    prev_ease = last.ease_factor if last else 2.5
    prev_interval = last.interval if last else 0
    prev_reps = last.repetitions if last else 0

    ease, interval, reps = sm2_calc(rating, prev_ease, prev_interval, prev_reps)

    log = ReviewLog(
        highlight_id=highlight_id,
        rating=rating,
        ease_factor=ease,
        interval=interval,
        repetitions=reps,
        next_review_at=get_next_review_date(interval),
    )
    db.add(log)
    await db.commit()

    url = f"/review?mode={mode}" if mode else "/review"
    return RedirectResponse(url=url, status_code=303)


# ── API endpoints ──────────────────────────────────────────────────────────


@router.post("/api/review/{hl_id}")
async def rate_highlight_api(
    hl_id: int,
    data: ReviewRating,
    db: AsyncSession = Depends(get_db),
):
    hl = await db.get(Highlight, hl_id)
    if not hl:
        return {"error": "Not found"}, 404

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
async def next_highlight_api(
    mode: str = "random",
    db: AsyncSession = Depends(get_db),
):
    if not mode:
        mode = review_settings.get("review_mode", "random")

    hl = await _pick_unreviewed(db, mode)

    if not hl:
        return {"done": True}

    return {
        "id": hl.id,
        "text": hl.text,
        "note": hl.note,
        "book_title": hl.book_title,
        "book_author": hl.book_author,
        "tags": [t.name for t in hl.tags],
    }


from sqlalchemy import select, func
