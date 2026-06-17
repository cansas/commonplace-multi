"""Daily review — flash-card style. Simple: Favorite, Delete, or Next."""
from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Highlight, ReviewLog
from app.services.resurface import get_random_highlights
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


async def _build_session(db) -> list[int]:
    """Pick highlights not yet reviewed today, up to the user's session count."""
    today_start = _today_start()
    count = review_settings.get("review_count", 10)

    candidates = await get_random_highlights(db, count * 2)

    session_ids = []
    for c in candidates:
        if len(session_ids) >= count:
            break
        result = await db.execute(
            select(func.count(ReviewLog.id)).where(
                ReviewLog.highlight_id == c.id,
                ReviewLog.reviewed_at >= today_start,
            )
        )
        if (result.scalar() or 0) == 0:
            session_ids.append(c.id)

    return session_ids


async def _get_highlight(db, hl_id: int):
    result = await db.execute(
        select(Highlight).where(Highlight.id == hl_id)
    )
    return result.scalar_one_or_none()


@router.get("/review", response_class=HTMLResponse)
async def review_page(
    request: Request,
    s: str = "",  # comma-separated highlight IDs for the session
    i: int = 0,   # current index into s
    db: AsyncSession = Depends(get_db),
):
    # Parse or build session
    if s:
        session_ids = [int(x) for x in s.split(",") if x.strip().isdigit()]
    else:
        session_ids = await _build_session(db)

    if not session_ids or i >= len(session_ids):
        total_remaining = await _count_unreviewed(db)
        return _jinja.TemplateResponse(
            request,
            "review.html",
            {
                "active_page": "review",
                "highlight": None,
                "total_count": total_remaining,
            },
        )

    hl = await _get_highlight(db, session_ids[i])
    if not hl:
        # Highlight was deleted since session was built — skip it
        i += 1
        s_str = ",".join(str(x) for x in session_ids)
        return RedirectResponse(
            url=f"/review?s={s_str}&i={i}", status_code=303
        )

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
        "favorite": hl.favorite,
    }

    session_str = ",".join(str(x) for x in session_ids)

    return _jinja.TemplateResponse(
        request,
        "review.html",
        {
            "active_page": "review",
            "highlight": highlight_data,
            "session_ids": session_str,
            "current_index": i + 1,
            "total_count": len(session_ids),
        },
    )


def _next_url(session_ids: str, i: int) -> str:
    """Build the redirect URL advancing to the next highlight."""
    ids = [x for x in session_ids.split(",") if x.strip().isdigit()]
    next_i = i + 1
    if next_i >= len(ids):
        return "/review"
    return f"/review?s={session_ids}&i={next_i}"


@router.post("/review/next")
async def review_next(
    s: str = Form(""),
    i: int = Form(0),
):
    return RedirectResponse(url=_next_url(s, i), status_code=303)


@router.post("/review/skip")
async def review_skip(
    s: str = Form(""),
    i: int = Form(0),
):
    return RedirectResponse(url=_next_url(s, i), status_code=303)


@router.post("/review/favorite")
async def review_favorite(
    s: str = Form(""),
    i: int = Form(0),
    db: AsyncSession = Depends(get_db),
):
    ids = [int(x) for x in s.split(",") if x.strip().isdigit()]
    if i < len(ids):
        hl = await _get_highlight(db, ids[i])
        if hl:
            hl.favorite = 0 if hl.favorite else 1
            await db.commit()
    return RedirectResponse(url=_next_url(s, i), status_code=303)


@router.post("/review/delete")
async def review_delete(
    s: str = Form(""),
    i: int = Form(0),
    db: AsyncSession = Depends(get_db),
):
    ids = [int(x) for x in s.split(",") if x.strip().isdigit()]
    if i < len(ids):
        hl = await _get_highlight(db, ids[i])
        if hl:
            await db.delete(hl)
            await db.commit()
    return RedirectResponse(url=_next_url(s, i), status_code=303)


from sqlalchemy import select, func
