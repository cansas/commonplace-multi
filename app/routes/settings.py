"""Settings page routes."""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Highlight
from app.auth import get_token, regenerate_token

router = APIRouter(tags=["settings"])

_jinja = None

# In-memory settings (no DB for preferences yet)
_settings = {"review_mode": "random", "review_count": 10}


def init(templates):
    global _jinja
    _jinja = templates


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    saved: str = "",
):
    result = await db.execute(select(func.count(Highlight.id)))
    total = result.scalar() or 0

    result = await db.execute(select(func.count(func.distinct(Highlight.book_title))))
    books = result.scalar() or 0

    return _jinja.TemplateResponse(
        request,
        "settings.html",
        {
            "active_page": "settings",
            "api_token": get_token(),
            "total_highlights": total,
            "total_books": books,
            "review_mode": _settings.get("review_mode", "random"),
            "review_count": _settings.get("review_count", 10),
            "version": "0.1.0",
            "saved": saved,
        },
    )


@router.post("/settings/review-mode")
async def set_review_mode(spaced_mode: str = Form(default="")):
    _settings["review_mode"] = "spaced" if spaced_mode == "1" else "random"
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@router.post("/settings/review-count")
async def set_review_count(count: int = Form(default=10)):
    _settings["review_count"] = max(5, min(30, count))
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@router.post("/api/settings/regenerate-token")
async def regenerate_api_token():
    new_token = regenerate_token()
    return {"token": new_token}


@router.get("/settings/reset")
async def reset_database(request: Request, db: AsyncSession = Depends(get_db)):
    """Delete all highlights and review history."""
    from app.models import Highlight, ReviewLog, Source, Tag, highlight_tags
    # Delete in FK-safe order: association table, review logs, highlights, tags, sources
    await db.execute(highlight_tags.delete())
    await db.execute(ReviewLog.__table__.delete())
    await db.execute(Highlight.__table__.delete())
    await db.execute(Tag.__table__.delete())
    await db.execute(Source.__table__.delete())
    await db.commit()
    return RedirectResponse(url="/", status_code=303)
