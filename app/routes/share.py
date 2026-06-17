"""Share routes — public PNG/SVG cards and HTML pages with OG tags."""
import secrets
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Highlight
from app.services.highlight_card import generate_card, svg_to_png

router = APIRouter(tags=["share"])

_jinja = None


def init(templates):
    global _jinja
    _jinja = templates


def _generate_share_token() -> str:
    """Generate a URL-safe share token."""
    return secrets.token_urlsafe(16)  # 22 chars, URL-safe


async def _get_highlight_by_token(token: str, db: AsyncSession) -> Highlight | None:
    """Look up a highlight by its share token."""
    # Strip .png or .svg suffix for lookup
    key = token
    for suffix in (".png", ".svg"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break
    result = await db.execute(
        select(Highlight).where(Highlight.share_token == key)
    )
    return result.scalar_one_or_none()


@router.get("/share/{share_token}.png")
async def share_png(share_token: str, db: AsyncSession = Depends(get_db)):
    """Return the highlight as a PNG image for social sharing."""
    hl = await _get_highlight_by_token(share_token, db)
    if not hl:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    svg = generate_card(
        highlight_text=hl.text or "",
        book_title=hl.book_title or "",
        book_author=hl.book_author or "",
        note=hl.note or "",
        highlight_id=hl.id,
    )
    png = svg_to_png(svg.encode("utf-8"))
    if png is None:
        return Response(status_code=500, content="PNG conversion unavailable")
    return Response(content=png, media_type="image/png")


@router.get("/share/{share_token}.svg")
async def share_svg(share_token: str, db: AsyncSession = Depends(get_db)):
    """Return the highlight as raw SVG."""
    hl = await _get_highlight_by_token(share_token, db)
    if not hl:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    svg = generate_card(
        highlight_text=hl.text or "",
        book_title=hl.book_title or "",
        book_author=hl.book_author or "",
        note=hl.note or "",
        highlight_id=hl.id,
    )
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/share/{share_token}", response_class=HTMLResponse)
async def share_page(share_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """HTML page with OpenGraph/Twitter card meta tags."""
    hl = await _get_highlight_by_token(share_token, db)
    if not hl:
        return _jinja.TemplateResponse(request, "share.html", {"error": "Not found"}, status_code=404)

    base_url = str(request.base_url).rstrip("/")
    png_url = f"{base_url}/share/{hl.share_token}.png"
    page_url = f"{base_url}/share/{hl.share_token}"

    return _jinja.TemplateResponse(
        request,
        "share.html",
        {
            "highlight": hl,
            "page_url": page_url,
            "png_url": png_url,
            "title": f"\"{hl.text[:80]}{'...' if len(hl.text) > 80 else ''}\"",
            "description": f"From {hl.book_title or 'Unknown Book'}{' by ' + hl.book_author if hl.book_author else ''}",
        },
    )


# ── Helper used by other routes to generate tokens ────────────────────────

def get_share_token() -> str:
    return _generate_share_token()
