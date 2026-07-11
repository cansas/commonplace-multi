"""
BookOrbit to Commonplace sync engine.

Imports annotations (kobo, koreader, web) from a BookOrbit server
into Commonplace's local database using SHA256 fingerprint dedup
and watermark tracking.

Now supports per-user sync for the multi-user fork.
"""

import logging
import secrets
from datetime import datetime
from typing import Any

import httpx

from app.services.import_service import highlight_fingerprint

logger = logging.getLogger(__name__)

ORIGIN_SOURCE_TYPE = {
    "kobo": "kobo",
    "koreader": "koreader",
    "web": "web",
}

_PAGE_SIZE = 100
_LOGIN_TIMEOUT = 15
_ANNOTATION_TIMEOUT = 30


async def _get_config(db, user_id: int) -> dict:
    from app.services.user_settings import get as _ug
    return {
        "url": await _ug(db, user_id, "bookorbit_url", ""),
        "username": await _ug(db, user_id, "bookorbit_username", ""),
        "password": await _ug(db, user_id, "bookorbit_password", ""),
        "enabled": await _ug(db, user_id, "bookorbit_sync_enabled", False),
        "last_synced_id": await _ug(db, user_id, "bookorbit_last_synced_id", 0),
        "last_synced_at": await _ug(db, user_id, "bookorbit_last_synced_at", ""),
        "disabled_reason": await _ug(db, user_id, "bookorbit_disabled_reason", ""),
    }


async def _save_config(db, user_id: int, config: dict) -> None:
    from app.services.user_settings import set_ as _us
    allowed = {
        "bookorbit_url", "bookorbit_username", "bookorbit_password",
        "bookorbit_sync_enabled", "bookorbit_disabled_reason",
    }
    for k in allowed:
        if k in config:
            await _us(db, user_id, k, config[k])


async def _json_request(
    client: httpx.AsyncClient,
    url: str,
    method: str = "GET",
    json_data: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, Any]:
    try:
        resp = await client.request(method, url, json=json_data, headers=headers)
        body = resp.json() if resp.text else {}
        return resp.status_code, body
    except httpx.TimeoutException:
        return 0, {"error": "Request timed out"}
    except httpx.RequestError as e:
        return 0, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


async def test_connection(url: str, username: str, password: str) -> dict:
    if not url or not username or not password:
        return {"ok": False, "error": "URL, username, and password are required"}
    clean_url = url.rstrip("/")
    async with httpx.AsyncClient(timeout=_LOGIN_TIMEOUT) as client:
        status, body = await _json_request(
            client, f"{clean_url}/api/v1/auth/login",
            method="POST",
            json_data={"username": username, "password": password},
        )
    if status == 200:
        return {"ok": True}
    msg = body.get("message") or body.get("error") or f"HTTP {status}"
    return {"ok": False, "error": msg}


async def sync_from_bookorbit(db, user_id: int = 1) -> dict:
    """Run a sync pass for a given user. Returns stats dict."""
    config = await _get_config(db, user_id)
    if not config["enabled"]:
        return {"posted": 0, "skipped": 0, "errors": 0, "last_id": config["last_synced_id"]}
    if not config["url"] or not config["username"] or not config["password"]:
        return {"posted": 0, "skipped": 0, "errors": 0, "last_id": config["last_synced_id"]}

    clean_url = config["url"].rstrip("/")
    watermark = config["last_synced_id"]

    from sqlalchemy import text as sqltext

    async with httpx.AsyncClient(timeout=_ANNOTATION_TIMEOUT) as client:
        status, body = await _json_request(
            client, f"{clean_url}/api/v1/auth/login",
            method="POST",
            json_data={"username": config["username"], "password": config["password"]},
        )
        if status != 200:
            msg = body.get("message") or body.get("error") or f"HTTP {status}"
            logger.warning("BookOrbit login failed (user %d): %s", user_id, msg)
            await _save_config(db, user_id, {"bookorbit_disabled_reason": f"login_failed: {msg}"})
            await db.commit()
            return {"posted": 0, "skipped": 0, "errors": 0, "last_id": watermark}

        await _save_config(db, user_id, {"bookorbit_disabled_reason": ""})

        all_annotations = []
        page = 1
        while True:
            url = (
                f"{clean_url}/api/v1/annotations"
                f"?status=active&sortBy=createdAt&sortDir=asc"
                f"&page={page}&pageSize={_PAGE_SIZE}"
            )
            status, body = await _json_request(client, url)
            if status != 200:
                logger.warning("BookOrbit annotations fetch failed (user %d, page %d): %s", user_id, page, body)
                break
            items = body.get("items", [])
            if not items:
                break
            all_annotations.extend(items)
            total = body.get("total", 0)
            if page * _PAGE_SIZE >= total:
                break
            page += 1

    posted = 0
    skipped = 0
    errors = 0
    max_id = watermark

    result = await db.execute(
        sqltext("SELECT fingerprint FROM highlights WHERE fingerprint IS NOT NULL AND user_id = :uid"),
        {"uid": user_id},
    )
    existing_fingerprints = {row[0] for row in result.fetchall()}

    result = await db.execute(
        sqltext("SELECT source_id FROM highlights WHERE source_id LIKE 'bookorbit:%' AND user_id = :uid"),
        {"uid": user_id},
    )
    existing_source_ids = {row[0] for row in result.fetchall()}

    for ann in all_annotations:
        ann_id = int(ann["id"])
        if ann_id <= watermark:
            continue

        source_id = f"bookorbit:{ann_id}"
        if source_id in existing_source_ids:
            if ann_id > max_id:
                max_id = ann_id
            skipped += 1
            continue

        text = (ann.get("text") or "").strip()
        if not text:
            skipped += 1
            continue

        book_title = ann.get("bookTitle") or "Untitled"
        book_author = ann.get("author") or ""
        fp = highlight_fingerprint(text, book_title, book_author)

        if fp in existing_fingerprints:
            if ann_id > max_id:
                max_id = ann_id
            skipped += 1
            continue

        origin = ann.get("origin", "kobo")
        source_type = ORIGIN_SOURCE_TYPE.get(origin, origin)

        try:
            highlighted_at = None
            if ann.get("createdAt"):
                try:
                    highlighted_at = datetime.fromisoformat(ann["createdAt"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            stmt = sqltext("""
                INSERT INTO highlights
                    (user_id, text, note, page, chapter, source_type, source_id,
                     book_title, book_author, color, category, favorite,
                     highlighted_at, created_at, share_token, fingerprint)
                VALUES
                    (:user_id, :text, :note, :page, :chapter, :source_type, :source_id,
                     :book_title, :book_author, :color, :category, 0,
                     :highlighted_at, :created_at, :share_token, :fingerprint)
            """)

            await db.execute(stmt, {
                "user_id": user_id,
                "text": text,
                "note": ann.get("note") or None,
                "page": None,
                "chapter": ann.get("chapterTitle") or None,
                "source_type": source_type,
                "source_id": source_id,
                "book_title": book_title,
                "book_author": book_author,
                "color": ann.get("color") or None,
                "category": "books",
                "highlighted_at": highlighted_at,
                "created_at": datetime.utcnow(),
                "share_token": secrets.token_urlsafe(16),
                "fingerprint": fp,
            })

            await db.commit()
            posted += 1
            existing_fingerprints.add(fp)
            existing_source_ids.add(source_id)
            if ann_id > max_id:
                max_id = ann_id

        except Exception as e:
            await db.rollback()
            errors += 1
            logger.warning("Failed to import BookOrbit annotation %d (user %d): %s", ann_id, user_id, e)

    if posted > 0 or max_id > watermark:
        await _save_config(db, user_id, {
            "bookorbit_last_synced_id": max_id,
            "bookorbit_last_synced_at": datetime.utcnow().isoformat(),
        })
        await db.commit()

    logger.info(
        "BookOrbit sync (user %d): posted=%d skipped=%d errors=%d last_id=%d",
        user_id, posted, skipped, errors, max_id,
    )
    return {"posted": posted, "skipped": skipped, "errors": errors, "last_id": max_id}
