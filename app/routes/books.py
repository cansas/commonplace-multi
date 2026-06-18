"""Books browse route — list books by title/author with highlight counts."""

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, or_
from app.database import get_db
from app.models import Highlight, BookCover
from app.services.book_covers import search_cover
from app.csrf import template_context
from typing import Optional
import math
import os
import re


def _escape_ilike(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def _safe_filename(name: str) -> str:
    return re.sub(r'[^\w.-]', '_', name)[:128]


router = APIRouter(tags=["books"])

_jinja = None
COVERS_DIR = os.environ.get("COVERS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "covers"))


def init(templates):
    global _jinja
    _jinja = templates


@router.get("/books", response_class=HTMLResponse)
async def books_page(
    request: Request,
    search: Optional[str] = Query(default=""),
    sort: str = Query(default="highlights"),
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    per_page = 30

    # Build query for distinct books with counts
    query = (
        select(
            Highlight.book_title,
            Highlight.book_author,
            sa_func.count(Highlight.id).label("highlight_count"),
            sa_func.max(Highlight.highlighted_at).label("last_highlighted"),
            sa_func.max(Highlight.id).label("sample_hl_id"),
        )
        .group_by(Highlight.book_title, Highlight.book_author)
    )

    if search:
        query = query.where(
            or_(
                Highlight.book_title.ilike(f"%{_escape_ilike(search)}%", escape="\\"),
                Highlight.book_author.ilike(f"%{_escape_ilike(search)}%", escape="\\"),
            )
        )

    # Count total distinct books
    count_q = select(sa_func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total / per_page))

    # Sort
    if sort == "title":
        query = query.order_by(Highlight.book_title.asc())
    elif sort == "author":
        query = query.order_by(Highlight.book_author.asc().nullslast())
    elif sort == "recent":
        query = query.order_by(sa_func.max(Highlight.highlighted_at).desc().nullslast())
    else:  # highlights (default)
        query = query.order_by(sa_func.count(Highlight.id).desc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    rows = result.all()

    # Bulk-fetch covers to avoid N+1
    cover_keys = [(row.book_title, row.book_author or "") for row in rows]
    cover_map = {}
    if cover_keys:
        cover_result = await db.execute(
            select(BookCover).where(
                or_(*[
                    (BookCover.book_title == t) & (BookCover.book_author == a)
                    for t, a in cover_keys
                ]) if cover_keys else False
            )
        )
        for cover in cover_result.scalars().all():
            cover_map[(cover.book_title, cover.book_author)] = cover

    books = []
    for row in rows:
        cover = cover_map.get((row.book_title, row.book_author or ""))
        books.append({
            "title": row.book_title,
            "author": row.book_author or "Unknown",
            "highlight_count": row.highlight_count,
            "last_highlighted": row.last_highlighted.strftime("%Y-%m-%d") if row.last_highlighted else "",
            "cover_url": cover.cover_url if cover else None,
            "cover_source": cover.cover_source if cover else "none",
            "highlight_id": row.sample_hl_id,
        })

    return _jinja.TemplateResponse(
        request,
        "books.html",
        template_context(
            request,
            active_page="books",
            books=books,
            search=search,
            sort=sort,
            page=page,
            total_pages=total_pages,
            total_books=total,
        ),
    )


@router.post("/api/books/cover/fetch")
async def fetch_cover(title: str = Form(...), author: str = Form(default=""), source: str = Form(default="auto"), db: AsyncSession = Depends(get_db)):
    try:
        url, cover_source = await search_cover(title, author)
        if not url:
            return {"ok": False, "error": "No cover found on Open Library, Hardcover, or Goodreads"}

        result = await db.execute(
            select(BookCover).where(
                BookCover.book_title == title,
                BookCover.book_author == author,
            )
        )
        cover = result.scalar_one_or_none()
        if cover:
            cover.cover_url = url
            cover.cover_source = cover_source
        else:
            db.add(BookCover(book_title=title, book_author=author, cover_url=url, cover_source=cover_source))
        await db.commit()
        return {"ok": True, "cover_url": url, "source": cover_source}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Magic bytes for image validation
_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"RIFF": ".webp",  # WebP starts with RIFF
}


def _validate_image_header(data: bytes) -> str | None:
    """Check magic bytes and return detected extension, or None if invalid."""
    for sig, ext in _IMAGE_SIGNATURES.items():
        if data[:len(sig)] == sig:
            if ext == ".webp" and data[8:12] != b"WEBP":
                return None
            return ext
    return None


@router.post("/api/books/cover/upload")
async def upload_cover(title: str = Form(...), author: str = Form(default=""), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        return JSONResponse({"ok": False, "error": "Only JPG, PNG, and WebP are accepted"}, status_code=400)

    # Read and validate size
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        return JSONResponse({"ok": False, "error": f"File too large ({len(content) // 1024 // 1024}MB). Max is 10MB."}, status_code=400)
    if len(content) < 100:
        return JSONResponse({"ok": False, "error": "File appears to be empty or too small"}, status_code=400)

    # Validate image magic bytes
    detected_ext = _validate_image_header(content)
    if not detected_ext:
        return JSONResponse({"ok": False, "error": "File is not a valid image (bad header bytes)"}, status_code=400)
    ext = detected_ext  # trust the actual bytes, not the extension

    # Build destination path
    dest = os.path.join(COVERS_DIR, f"{_safe_filename(title)}_{_safe_filename(author)}{ext}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    # Write file
    try:
        with open(dest, "wb") as f:
            f.write(content)
        if not os.path.isfile(dest):
            return JSONResponse({"ok": False, "error": "File write succeeded but file not found on disk"}, status_code=500)
    except OSError as e:
        return JSONResponse({"ok": False, "error": f"Failed to write file: {e}"}, status_code=500)

    cover_url = f"/static/covers/{os.path.basename(dest)}"

    # Update DB
    result = await db.execute(
        select(BookCover).where(
            BookCover.book_title == title,
            BookCover.book_author == author,
        )
    )
    cover = result.scalar_one_or_none()
    if cover:
        # Clean up old file if it exists and is different
        old_path = os.path.join(COVERS_DIR, os.path.basename(cover.cover_url or ""))
        if old_path != dest and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
        cover.cover_url = cover_url
        cover.cover_source = "upload"
    else:
        db.add(BookCover(book_title=title, book_author=author, cover_url=cover_url, cover_source="upload"))
    await db.commit()
    return {"ok": True, "cover_url": cover_url}


@router.post("/api/books/rename")
async def rename_book(
    old_title: str = Form(...),
    old_author: str = Form(default=""),
    new_title: str = Form(...),
    new_author: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Rename a book across all highlights. Updates metadata and cover records.

    Shows a warning to the user that future imports with the old title
    will create a separate book entry.
    """
    if not new_title.strip():
        return JSONResponse({"ok": False, "error": "New title is required"}, status_code=400)

    old_author = old_author or ""
    new_author = new_author or ""

    # Count highlights affected
    count_result = await db.execute(
        select(sa_func.count(Highlight.id)).where(
            Highlight.book_title == old_title,
            Highlight.book_author == old_author,
        )
    )
    affected = count_result.scalar() or 0

    if affected == 0:
        return JSONResponse({"ok": False, "error": "No highlights found with that title"}, status_code=404)

    # Update all highlights
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(Highlight)
        .where(
            Highlight.book_title == old_title,
            Highlight.book_author == old_author,
        )
        .values(book_title=new_title.strip(), book_author=new_author)
    )

    # Update BookCover if one exists
    cover_result = await db.execute(
        select(BookCover).where(
            BookCover.book_title == old_title,
            BookCover.book_author == old_author,
        )
    )
    cover = cover_result.scalar_one_or_none()
    if cover:
        cover.book_title = new_title.strip()
        cover.book_author = new_author

    await db.commit()

    return {
        "ok": True,
        "affected": affected,
        "old_title": old_title,
        "new_title": new_title.strip(),
        "warning": "Highlights imported later with the old title will appear as a separate book.",
    }


@router.post("/api/books/cover/backfill")
async def backfill_covers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Highlight.book_title, Highlight.book_author)
        .distinct()
    )
    books = result.all()
    fetched = 0
    for row in books:
        existing = await db.execute(
            select(BookCover).where(
                BookCover.book_title == row.book_title,
                BookCover.book_author == (row.book_author or ""),
            )
        )
        if existing.scalar_one_or_none():
            continue
        url, cover_source = await search_cover(row.book_title, row.book_author or "")
        if url:
            db.add(BookCover(book_title=row.book_title, book_author=row.book_author or "", cover_url=url, cover_source=cover_source))
            fetched += 1
            await db.commit()
    return {"ok": True, "fetched": fetched}


@router.post("/api/books/cover/fetch/{hl_id}")
async def fetch_cover_by_hl(hl_id: int, db: AsyncSession = Depends(get_db)):
    hl = await db.get(Highlight, hl_id)
    if not hl:
        return {"ok": False, "error": "Highlight not found"}
    return await fetch_cover(title=hl.book_title, author=hl.book_author or "", source="auto", db=db)


@router.post("/api/books/cover/upload/{hl_id}")
async def upload_cover_by_hl(hl_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    hl = await db.get(Highlight, hl_id)
    if not hl:
        return JSONResponse({"ok": False, "error": "Highlight not found"}, status_code=404)
    return await upload_cover(title=hl.book_title, author=hl.book_author or "", file=file, db=db)
