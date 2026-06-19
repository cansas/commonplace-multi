"""Achievements page routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.achievements import get_all_achievements
from app.csrf import template_context

router = APIRouter(tags=["achievements"])

_jinja = None


def init(templates):
    global _jinja
    _jinja = templates


@router.get("/api/achievements")
async def api_achievements(db: AsyncSession = Depends(get_db)):
    """Return all achievements with unlock status."""
    return await get_all_achievements(db)


@router.get("/achievements", response_class=HTMLResponse)
async def achievements_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Achievements display page."""
    achievements = await get_all_achievements(db)
    unlocked_count = sum(1 for a in achievements if a["unlocked"])

    # Check for new achievements from session
    new_achievements = request.session.pop("new_achievements", [])

    return _jinja.TemplateResponse(
        request,
        "achievements.html",
        template_context(
            request,
            active_page="achievements",
            achievements=achievements,
            unlocked_count=unlocked_count,
            total_count=len(achievements),
            new_achievements=new_achievements,
        ),
    )
