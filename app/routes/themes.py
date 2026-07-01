"""Theme management API — upload, delete, list custom themes.

All endpoints are CSRF-exempt (under /api/) and require an active session.
"""

import os
import re
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse

import tinycss2

from app.services.theme_service import CUSTOM_THEMES_DIR, discover_custom_themes

MAX_THEME_SIZE = 50 * 1024  # 50 KB

router = APIRouter(tags=["themes"])


def _validate_theme_css(content: str) -> tuple[bool, str, str | None]:
    """Validate a CSS file as a theme.

    Returns (is_valid, error_message, theme_name).
    Validates:
      - Must be parseable CSS
      - No @import rules (prevents external stylesheet loading)
      - No url() references (prevents tracking/phishing callouts)
      - Must define exactly one ``.theme-{name}`` class
    """
    try:
        rules = tinycss2.parse_stylesheet(content)
    except Exception as e:
        return False, f"Failed to parse CSS: {e}", None

    if not rules:
        return False, "File contains no CSS rules", None

    name = None

    for rule in rules:
        # Block @import
        if rule.type == "at-rule":
            keyword = getattr(rule, "lower_at_keyword", "") or getattr(rule, "at_keyword", "")
            if keyword == "import":
                return False, "@import rules are not allowed in themes", None
            continue

        if rule.type != "qualified-rule":
            continue

        # Extract .theme-{name} from the selector
        prelude = tinycss2.serializer.serialize(rule.prelude).strip()
        m = re.match(r"\.theme-([a-z][a-z0-9_-]*)\b", prelude)
        if m:
            if name and m.group(1) != name:
                return False, "Theme file must define a single .theme-{name} class", None
            name = m.group(1)

        # Check for url() inside the rule content
        try:
            content_text = tinycss2.serializer.serialize(rule.content)
            if re.search(r"url\s*\(", content_text, re.IGNORECASE):
                return False, "External URLs are not allowed in themes (url() is blocked for privacy)", None
            if re.search(r'https?://', content_text):
                return False, "External URLs are not allowed in themes", None
        except Exception:
            pass

    if not name:
        return False, "Theme must define a .theme-{name} CSS class (e.g. .theme-ocean)", None

    return True, "", name


@router.post("/api/themes/upload")
async def upload_theme(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload a new custom theme CSS file.

    Validates the file and writes it to ``data/themes/{name}.css``.
    """
    # Auth check — must have session
    if not request.session.get("user_id"):
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    # Validate extension
    if not file.filename or not file.filename.lower().endswith(".css"):
        return JSONResponse(
            {"ok": False, "error": "Only .css files are accepted"},
            status_code=400,
        )

    # Read content
    try:
        content = await file.read()
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Failed to read file: {e}"}, status_code=400)

    content_str = content.decode("utf-8", errors="replace")

    # Size check
    if len(content_str) > MAX_THEME_SIZE:
        return JSONResponse(
            {"ok": False, "error": f"File too large ({len(content_str) // 1024}KB). Max is 50KB."},
            status_code=400,
        )

    # Validate CSS
    ok, error, theme_name = _validate_theme_css(content_str)
    if not ok:
        return JSONResponse({"ok": False, "error": error}, status_code=400)

    if not theme_name:
        return JSONResponse({"ok": False, "error": "Could not determine theme name from CSS"}, status_code=400)

    # Ensure themes directory exists
    os.makedirs(CUSTOM_THEMES_DIR, exist_ok=True)

    # Write the file (name from CSS class, not the uploaded filename)
    dest = os.path.join(CUSTOM_THEMES_DIR, f"{theme_name}.css")
    try:
        with open(dest, "w") as f:
            f.write(content_str)
    except OSError as e:
        return JSONResponse({"ok": False, "error": f"Failed to write theme file: {e}"}, status_code=500)

    return {
        "ok": True,
        "theme_name": theme_name,
        "message": f"Theme '{theme_name}' uploaded",
    }


@router.post("/api/themes/delete")
async def delete_theme(
    request: Request,
    name: str = Form(...),
):
    """Delete a custom theme CSS file.

    Only custom themes (in ``data/themes/``) can be deleted.
    Built-in themes are not touchable.
    """
    if not request.session.get("user_id"):
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    # Validate name
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        return JSONResponse({"ok": False, "error": "Invalid theme name"}, status_code=400)

    filepath = os.path.join(CUSTOM_THEMES_DIR, f"{name}.css")

    # Safety: ensure it's actually inside the custom themes dir (no path traversal)
    real_dest = os.path.realpath(filepath)
    real_base = os.path.realpath(CUSTOM_THEMES_DIR)
    if not real_dest.startswith(real_base + os.sep) and real_dest != real_base:
        return JSONResponse({"ok": False, "error": "Invalid theme path"}, status_code=400)

    if not os.path.isfile(real_dest):
        return JSONResponse({"ok": False, "error": f"Theme '{name}' not found"}, status_code=404)

    try:
        os.remove(real_dest)
    except OSError as e:
        return JSONResponse({"ok": False, "error": f"Failed to delete theme: {e}"}, status_code=500)

    return {"ok": True, "theme_name": name, "message": f"Theme '{name}' deleted"}
