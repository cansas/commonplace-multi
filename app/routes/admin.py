"""Admin routes — user management, invite flow, registration, dedup.

Supports multi-user fork: admin invites users, users accept via
one-time token, no public signup.
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import User, Invite
from app.auth import get_current_user_id, hash_password, verify_password
from app.csrf import template_context, csrf_guard
from app.template import render

router = APIRouter(tags=["admin"])

_INVITE_TTL_DAYS = 7


async def _require_admin(request: Request, db: AsyncSession) -> User:
    """Return the current user if they are the admin (user_id=1)."""
    uid = await get_current_user_id(request)
    if uid != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Admin user list ─────────────────────────────────────────────────────


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin: list all users and show invite controls."""
    await _require_admin(request, db)

    result = await db.execute(
        select(User).order_by(User.created_at.asc())
    )
    users = result.scalars().all()

    # Each user's basic info
    user_stats = []
    for u in users:
        user_stats.append({
            "id": u.id,
            "username": u.username,
            "created_at": u.created_at,
            "is_admin": u.id == 1,
        })

    return render(
        request,
        "admin_users.html",
        template_context(
            request,
            active_page="admin",
            users=user_stats,
        ),
    )


# ── Create invite ──────────────────────────────────────────────────────


@router.post("/admin/invite")
async def create_invite(
    request: Request,
    csrf_token: str = Form(default=""),
    username: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Admin: create an invite for a new user."""
    await _require_admin(request, db)
    csrf_guard(request, csrf_token)

    username = username.strip()
    if not username or len(username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")

    # Check not taken
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        return RedirectResponse(url="/admin/users?error=Username+taken", status_code=303)

    # Generate invite
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=_INVITE_TTL_DAYS)
    inv = Invite(
        username=username,
        token=token,
        created_by=1,  # only admin can create invites
        expires_at=expires_at,
    )
    db.add(inv)
    await db.commit()

    base_url = str(request.base_url).rstrip("/")
    invite_url = f"{base_url}/setup/invite?token={token}"

    # Store in session for display
    request.session["last_invite_url"] = invite_url
    request.session["last_invite_username"] = username

    return RedirectResponse(url="/admin/users?invited=1", status_code=303)


# ── Accept invite ──────────────────────────────────────────────────────


@router.get("/setup/invite", response_class=HTMLResponse)
async def accept_invite_page(
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Show invite acceptance form."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)

    result = await db.execute(
        select(Invite).where(
            Invite.token == token,
            Invite.used_at.is_(None),
            Invite.expires_at > datetime.utcnow(),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        return render(
            request,
            "invite_expired.html",
            template_context(request),
        )

    return render(
        request,
        "accept_invite.html",
        template_context(
            request,
            token=token,
            username=inv.username,
        ),
    )


@router.post("/setup/invite")
async def accept_invite(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Accept an invite and create the user account."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)

    result = await db.execute(
        select(Invite).where(
            Invite.token == token,
            Invite.used_at.is_(None),
            Invite.expires_at > datetime.utcnow(),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        return render(
            request, "invite_expired.html",
            template_context(request),
        )

    # Validate
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if password != confirm_password:
        errors.append("Passwords do not match")
    if errors:
        return render(
            request, "accept_invite.html",
            template_context(request, token=token, username=inv.username, error=" | ".join(errors)),
        )

    # Create user
    pwhash = hash_password(password)
    user = User(username=inv.username, password_hash=pwhash)
    db.add(user)
    await db.flush()

    # Mark invite used
    inv.used_at = datetime.utcnow()
    await db.commit()

    # Log them in
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["theme"] = "modern"

    return RedirectResponse(url="/", status_code=303)


# ── Rescind invite ─────────────────────────────────────────────────────


@router.post("/admin/invite/{invite_id}/rescind")
async def rescind_invite(
    request: Request,
    invite_id: int,
    csrf_token: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Admin: cancel a pending invite."""
    await _require_admin(request, db)
    csrf_guard(request, csrf_token)

    result = await db.execute(
        select(Invite).where(
            Invite.id == invite_id,
            Invite.used_at.is_(None),
        )
    )
    inv = result.scalar_one_or_none()
    if inv:
        # Mark expired immediately instead of deleting (keep audit trail)
        inv.expires_at = datetime.utcnow()
        await db.commit()

    return RedirectResponse(url="/admin/users", status_code=303)


# ── Dedup ────────────────────────────────────────────────────────────────


@router.post("/admin/dedup")
async def dedup_highlights(
    request: Request,
    csrf_token: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Admin: find and merge duplicate highlights by (text, book_title, book_author)."""
    await _require_admin(request, db)
    csrf_guard(request, csrf_token)

    from app.models import Highlight, ReviewLog, highlight_tags
    from sqlalchemy import text as sqltext

    # Find all duplicates — same text + book_title + book_author, grouped
    rows = await db.execute(sqltext(
        "SELECT text, book_title, book_author, COUNT(*) as cnt "
        "FROM highlights "
        "GROUP BY text, book_title, book_author "
        "HAVING COUNT(*) > 1 "
        "ORDER BY cnt DESC"
    ))
    dup_groups = rows.mappings().all()

    merged = 0
    removed = 0
    for group in dup_groups:
        dup_rows = await db.execute(
            sqltext(
                "SELECT id FROM highlights "
                "WHERE text = :text AND book_title = :bt "
                "AND (book_author = :ba OR (book_author IS NULL AND :ba = '')) "
                "ORDER BY id ASC"
            ),
            {"text": group["text"], "bt": group["book_title"], "ba": group["book_author"] or ""},
        )
        ids = [r[0] for r in dup_rows.fetchall()]
        keep_id = ids[0]
        del_ids = ids[1:]

        # Merge tags from duplicates into the kept one
        for did in del_ids:
            await db.execute(
                sqltext(
                    "INSERT OR IGNORE INTO highlight_tags (highlight_id, tag_id) "
                    "SELECT :keep, tag_id FROM highlight_tags WHERE highlight_id = :del"
                ),
                {"keep": keep_id, "del": did},
            )

        # Reassign review_logs one at a time
        for did in del_ids:
            await db.execute(
                sqltext("UPDATE review_log SET highlight_id = :keep WHERE highlight_id = :del"),
                {"keep": keep_id, "del": did},
            )

        # Delete duplicate highlights
        for did in del_ids:
            await db.execute(
                sqltext("DELETE FROM highlight_tags WHERE highlight_id = :id"),
                {"id": did},
            )
            await db.execute(
                sqltext("DELETE FROM highlights WHERE id = :id"),
                {"id": did},
            )

        merged += 1
        removed += len(del_ids)

    await db.commit()

    # Rebuild FTS index
    await db.execute(sqltext("DELETE FROM highlights_fts"))
    await db.execute(sqltext(
        "INSERT INTO highlights_fts(rowid, text, note, book_title, book_author) "
        "SELECT id, text, note, book_title, book_author FROM highlights"
    ))
    await db.commit()

    return {"ok": True, "groups_merged": merged, "duplicates_removed": removed}
