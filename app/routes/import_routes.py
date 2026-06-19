"""Import routes — Readwise Obsidian files, KOReader JSON, Readwise API format."""

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Highlight, Source
from app.services.obsidian import parse_readwise_md
from app.services.koreader_json import parse_koreader_json
from app.schemas import ReadwiseBatchImport
from app.routes.share import get_share_token
from app.csrf import template_context, csrf_guard
from datetime import datetime
import json

router = APIRouter(tags=["import"])

_jinja = None


def init(templates):
    global _jinja
    _jinja = templates


async def _render_import(request, db, import_result=None):
    """Render the import page with recent imports and optional import result."""
    result = await db.execute(
        select(Source).order_by(Source.last_import_at.desc().nullslast()).limit(10)
    )
    sources = result.scalars().all()

    return _jinja.TemplateResponse(
        request,
        "import.html",
        template_context(
            request,
            active_page="import",
            import_result=import_result,
            recent_imports=[
                {
                    "name": s.name,
                    "source_type": s.source_type,
                    "last_import_at": s.last_import_at.strftime("%Y-%m-%d %H:%M") if s.last_import_at else "",
                    "count": s.highlights_imported or 0,
                }
                for s in sources
            ],
        ),
    )


@router.get("/import", response_class=HTMLResponse)
async def import_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await _render_import(request, db)


async def _save_highlights(db, highlights_list, source_name, source_type, dry_run=False):
    """Bulk-save highlights and record source. Skips duplicates.

    In dry_run mode, counts what would be imported/skipped without writing.
    Returns (count, skipped).
    """
    # Pre-fetch existing highlights to avoid N+1 queries
    existing_set = set()
    if highlights_list:
        result = await db.execute(
            select(Highlight.text, Highlight.book_title, Highlight.highlighted_at)
        )
        for row in result.all():
            existing_set.add((row.text, row.book_title, row.highlighted_at))

    count = 0
    skipped = 0
    for item in highlights_list:
        text = item["text"]
        book_title = item.get("book_title", "Untitled")
        highlighted_at = item.get("highlighted_at")

        if (text, book_title, highlighted_at) in existing_set:
            skipped += 1
            continue

        if dry_run:
            count += 1
            continue

        hl = Highlight(
            text=text,
            note=item.get("note"),
            page=item.get("page"),
            chapter=item.get("chapter"),
            source_type=source_type,
            book_title=book_title,
            book_author=item.get("book_author"),
            category=item.get("category", "books"),
            color=item.get("color"),
            highlighted_at=highlighted_at or datetime.utcnow(),
            share_token=get_share_token(),
        )
        db.add(hl)
        existing_set.add((text, book_title, highlighted_at))
        count += 1

    if not dry_run and count > 0:
        # Record the import source
        src = Source(
            name=source_name,
            source_type=source_type,
            last_import_at=datetime.utcnow(),
            highlights_imported=count,
        )
        db.add(src)

    if not dry_run:
        await db.commit()

    return count, skipped


@router.post("/import/readwise")
async def import_readwise(
    request: Request,
    csrf_token: str = Form(default=""),
    file: UploadFile = File(...),
    content: str = Form(default=""),
    dry_run: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    csrf_guard(request, csrf_token)
    all_highlights = []
    errors = []
    is_dry_run = dry_run == "true"

    if content.strip():
        # Pasted content mode
        try:
            parsed = parse_readwise_md(content, "pasted-content")
            all_highlights.extend(parsed)
        except Exception as e:
            errors.append(f"Failed to parse pasted content: {e}")
        source_name = "Pasted Readwise content"
    else:
        # File upload mode
        try:
            raw = (await file.read()).decode("utf-8", errors="replace")
        except Exception as e:
            errors.append(f"Failed to read file {file.filename}: {e}")
            raw = ""

        if raw and not errors:
            try:
                parsed = parse_readwise_md(raw, file.filename or "")
                all_highlights.extend(parsed)
            except Exception as e:
                errors.append(f"Failed to parse {file.filename}: {e}")

        source_name = file.filename or "unknown"

    count, skipped = await _save_highlights(
        db, all_highlights,
        source_name=source_name,
        source_type="readwise",
        dry_run=is_dry_run,
    )

    result = {
        "success": len(errors) == 0,
        "imported": count,
        "skipped": skipped,
        "errors": errors,
        "dry_run": is_dry_run,
        "source_name": source_name,
        "source_type": "readwise",
        "action": "/import/readwise",
    }

    if is_dry_run and content.strip():
        result["pasted_content"] = content

    return await _render_import(request, db, result)


@router.post("/import/koreader-json")
async def import_koreader_json(
    request: Request,
    csrf_token: str = Form(default=""),
    file: UploadFile = File(...),
    dry_run: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    csrf_guard(request, csrf_token)
    is_dry_run = dry_run == "true"

    try:
        content = json.loads(await file.read())
    except json.JSONDecodeError as e:
        result = {
            "success": False,
            "imported": 0,
            "skipped": 0,
            "errors": [f"Invalid JSON: {e}"],
            "dry_run": False,
            "source_name": file.filename or "unknown",
            "source_type": "koreader",
            "action": "/import/koreader-json",
        }
        return await _render_import(request, db, result)

    parsed = parse_koreader_json(content)

    count, skipped = await _save_highlights(
        db, parsed,
        source_name=file.filename or "koreader-export.json",
        source_type="koreader",
        dry_run=is_dry_run,
    )

    result = {
        "success": True,
        "imported": count,
        "skipped": skipped,
        "errors": [],
        "dry_run": is_dry_run,
        "source_name": file.filename or "koreader-export.json",
        "source_type": "koreader",
        "action": "/import/koreader-json",
    }

    return await _render_import(request, db, result)


# Readwise-compatible API endpoint (what KOReader Readwise plugin sends)
@router.post("/api/v2/highlights")
async def readwise_api_import(
    data: ReadwiseBatchImport,
    db: AsyncSession = Depends(get_db),
):
    # Pre-fetch existing highlights to avoid N+1 queries
    existing_set = set()
    result = await db.execute(
        select(Highlight.text, Highlight.book_title, Highlight.highlighted_at)
    )
    for row in result.all():
        existing_set.add((row.text, row.book_title, row.highlighted_at))

    count = 0
    skipped = 0
    for item in data.highlights:
        text = item.text
        book_title = item.book_title or "Untitled"
        highlighted_at = item.highlighted_at

        if (text, book_title, highlighted_at) in existing_set:
            skipped += 1
            continue

        hl = Highlight(
            text=text,
            note=item.note,
            page=item.page,
            chapter=item.chapter,
            source_type=item.source_type or "koreader",
            source_id=item.source_id,
            book_title=book_title,
            book_author=item.book_author,
            book_url=item.book_url,
            category=item.category or "books",
            color=item.color,
            highlighted_at=highlighted_at or datetime.utcnow(),
            share_token=get_share_token(),
        )
        db.add(hl)
        existing_set.add((text, book_title, highlighted_at))
        count += 1

    src = Source(
        name=f"KOReader API ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')})",
        source_type="koreader",
        last_import_at=datetime.utcnow(),
        highlights_imported=count,
    )
    db.add(src)
    await db.commit()

    return {"imported": count, "skipped": skipped}
