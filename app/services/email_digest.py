"""Mailjet email digest service.

Sends daily review emails via Mailjet's REST API (free tier: 6k/mo, 200/day).
All configuration is read/written through ``app.services.settings_service``.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

MAILJET_API = "https://api.mailjet.com/v3.1/send"


# ── Public helpers (delegate to settings_service) ─────────────────────────

def get_email_config() -> dict:
    """Return all email/digest settings from the shared settings store."""
    from app.services.settings_service import get_email_config as _cfg
    return _cfg()


def save_email_config(config: dict) -> None:
    """Merge *config* into the shared settings store."""
    from app.services.settings_service import save_email_config as _save
    _save(config)


# ── Low-level Mailjet API ──────────────────────────────────────────────────


async def send_email_via_mailjet(
    api_key: str,
    secret_key: str,
    from_name: str,
    from_email: str,
    to_email: str,
    subject: str,
    html_content: str,
) -> dict:
    """Send a single email via Mailjet REST API. Returns response JSON."""
    payload = {
        "Messages": [
            {
                "From": {"Name": from_name, "Email": from_email},
                "To": [{"Email": to_email}],
                "Subject": subject,
                "HTMLPart": html_content,
            }
        ]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            MAILJET_API,
            auth=(api_key, secret_key),
            json=payload,
        )
    result = resp.json()
    if resp.status_code != 200:
        error_detail = result.get("ErrorMessage", result.get("error", str(result)))
        raise RuntimeError(f"Mailjet error ({resp.status_code}): {error_detail}")
    return result


# ── Digest builder ─────────────────────────────────────────────────────────


async def build_digest_html(db) -> str:
    """Query the daily review queue and build an HTML email body.

    Uses the same queue as the review page so the email matches
    what the user will see when they open /review.
    """
    from app.services.review_queue import get_or_create_queue
    from app.services.settings_service import get_review_count

    queue = await get_or_create_queue(get_review_count())
    # Show up to 3 un-reviewed entries from the queue
    highlights = [h for h in queue if not h["reviewed"]][:3]

    if not highlights:
        return "<p>No highlights to review today. Import some highlights to get started!</p>"

    items_html = ""
    for hl in highlights[:3]:
        text = hl.get("text") or ""
        note = hl.get("note") or ""
        book_title = hl.get("book_title") or ""
        book_author = hl.get("book_author") or ""
        items_html += f"""
        <div style="margin-bottom:24px;padding:16px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">
            <p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#1e293b;font-style:italic;">{_escape_html(text)}</p>
            <div style="margin-top:8px;font-size:12px;color:#64748b;">
                <span>📖 {_escape_html(book_title)}</span>
                {f'<span style="margin:0 4px;">·</span><span>✍️ {_escape_html(book_author)}</span>' if book_author else ''}
            </div>
        </div>
        """

    return f"""
    <div style="max-width:560px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="text-align:center;padding:24px 0 16px;">
            <h1 style="font-size:20px;font-weight:700;color:#1e293b;margin:0;">📖 Your Daily Review</h1>
            <p style="font-size:14px;color:#64748b;margin:6px 0 0;">Highlights to reinforce today</p>
        </div>
        {items_html}
        <div style="text-align:center;padding:16px 0 24px;">
            <a href="{_get_base_url()}/review"
               style="display:inline-block;padding:12px 28px;background:#6366f1;color:#fff;font-size:14px;font-weight:600;border-radius:8px;text-decoration:none;">
                📝 Start Review Session
            </a>
        </div>
        <div style="text-align:center;padding:12px 0;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;">
            <p style="margin:0 0 4px;">Commonplace — self-hosted highlights</p>
            <p style="margin:0;">
                <a href="{_get_base_url()}/settings?tab=email" style="color:#94a3b8;text-decoration:underline;">Unsubscribe</a>
                · or disable in Settings
            </p>
        </div>
    </div>
    """


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _get_base_url() -> str:
    """Return the base URL from settings, or a sensible default."""
    from app.services.settings_service import get as _get
    return _get("base_url", "http://localhost:8765")


# ── Send test email ────────────────────────────────────────────────────────


async def send_test_email(api_key: str, secret_key: str, from_name: str, from_email: str, to_email: str) -> dict:
    """Send a simple test email to verify Mailjet config."""
    html = """
    <div style="max-width:560px;margin:0 auto;font-family:sans-serif;padding:32px 0;text-align:center;">
        <h1 style="font-size:24px;color:#1e293b;">✅ Test Email</h1>
        <p style="font-size:14px;color:#64748b;">Your Mailjet configuration is working!</p>
        <p style="font-size:12px;color:#94a3b8;">Sent from Commonplace</p>
    </div>
    """
    return await send_email_via_mailjet(
        api_key, secret_key, from_name, from_email, to_email,
        "Commonplace — Test Email", html,
    )
