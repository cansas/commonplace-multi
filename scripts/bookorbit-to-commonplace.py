#!/usr/bin/env python3
"""
bookorbit-to-commonplace.py
Bridges Kobo annotations from BookOrbit into Commonplace.

Keychain entries needed (set once):
  security add-generic-password -s bookorbit-api -a "username" -w "your-bookorbit-username"
  security add-generic-password -s bookorbit-api -a "password" -w "your-bookorbit-password"
  security add-generic-password -s commonplace-api -a "token" -w "your-commonplace-api-token"
"""

import urllib.request
import urllib.error
import json
import os
import subprocess
import sys
import http.cookiejar
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────
BOOKORBIT_BASE = "http://192.168.1.130:3000"
COMMONPLACE_BASE = "https://commonplace.bcbrown.us"
STATE_FILE = os.path.expanduser("~/.hermes/bookorbit-sync-state.json")

BO_SERVICE = "bookorbit-api"
CP_SERVICE = "commonplace-api"


# ── Helpers ─────────────────────────────────────────────────────────────

def keychain_get(service, account):
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Exception(f"Keychain lookup failed: {service}/{account}")
    return result.stdout.strip()


def json_request(opener, url, method="GET", data=None, headers=None):
    """JSON HTTP helper. Returns (status_code, parsed_body)."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if data is not None:
        req.data = json.dumps(data).encode()
    try:
        resp = opener.open(req)
        body = json.loads(resp.read().decode())
        return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"error": body}


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_synced_id": 0, "last_synced_at": None}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── BookOrbit ───────────────────────────────────────────────────────────

def bo_login(opener, username, password):
    """Login to BookOrbit. CookieJar captures the JWT cookie."""
    status, body = json_request(
        opener,
        f"{BOOKORBIT_BASE}/api/v1/auth/login",
        method="POST",
        data={"username": username, "password": password},
    )
    if status != 200:
        raise Exception(f"BookOrbit login failed ({status}): {body}")


def bo_fetch_annotations(opener, since_id=0):
    """Fetch Kobo-origin annotations paginated, newest-first ID sort."""
    all_items = []
    page = 1
    page_size = 100

    while True:
        url = (
            f"{BOOKORBIT_BASE}/api/v1/annotations"
            f"?origins=kobo&status=active&sortBy=createdAt&sortDir=asc"
            f"&page={page}&pageSize={page_size}"
        )
        status, body = json_request(opener, url)
        if status != 200:
            raise Exception(f"BookOrbit annotations fetch failed ({status}): {body}")

        items = body.get("items", [])
        # Only take items we haven't seen
        for item in items:
            if int(item["id"]) > since_id:
                all_items.append(item)

        total = body.get("total", 0)
        if page * page_size >= total:
            break
        page += 1

    return all_items


# ── Commonplace ─────────────────────────────────────────────────────────

def cp_post_highlight(token, annotation):
    """POST one highlight to Commonplace. Readwise v2 field aliases work."""
    payload = {
        "text": annotation["text"],
        "book_title": annotation.get("bookTitle") or "Untitled",
        "book_author": annotation.get("author") or "",
        "highlighted_at": annotation.get("createdAt"),
        "color": annotation.get("color"),
        "chapter": annotation.get("chapterTitle"),
        "source_type": "kobo",
        "category": "books",
    }
    if annotation.get("note"):
        payload["note"] = annotation["note"]

    # Strip nulls
    payload = {k: v for k, v in payload.items() if v is not None}

    # Use a fresh opener (no BookOrbit cookies needed)
    opener = urllib.request.build_opener()
    status, body = json_request(
        opener,
        f"{COMMONPLACE_BASE}/api/highlights",
        method="POST",
        data=payload,
        headers={"Authorization": f"Token {token}"},
    )
    if status not in (200, 201):
        raise Exception(f"Commonplace POST failed ({status}): {body}")
    return body


# ── Main ────────────────────────────────────────────────────────────────

def main():
    log = lambda msg: print(msg, file=sys.stderr)

    # ── Read credentials ───────────────────────────────────────────────
    try:
        bo_username = keychain_get(BO_SERVICE, "username")
        bo_password = keychain_get(BO_SERVICE, "password")
        cp_token = keychain_get(CP_SERVICE, "token")
    except Exception as e:
        log(f"Keychain error: {e}")
        log("Set up credentials with:")
        log('  security add-generic-password -s bookorbit-api -a "username" -w "..."')
        log('  security add-generic-password -s bookorbit-api -a "password" -w "..."')
        log('  security add-generic-password -s commonplace-api -a "token" -w "..."')
        sys.exit(1)

    # ── Load state ─────────────────────────────────────────────────────
    state = load_state()
    last_id = state.get("last_synced_id", 0)
    log(f"State loaded: last_synced_id={last_id}")

    # ── Login to BookOrbit ─────────────────────────────────────────────
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    log(f"Logging into BookOrbit at {BOOKORBIT_BASE}...")
    try:
        bo_login(opener, bo_username, bo_password)
    except Exception as e:
        log(f"BookOrbit login failed: {e}")
        sys.exit(2)

    # ── Fetch annotations ──────────────────────────────────────────────
    log(f"Fetching Kobo annotations since id={last_id}...")
    annotations = bo_fetch_annotations(opener, last_id)
    log(f"Found {len(annotations)} new annotation(s)")

    if not annotations:
        # Silent exit — no delivery to user
        print(json.dumps({"posted": 0, "errors": 0, "last_id": last_id}))
        return

    # ── Post to Commonplace ────────────────────────────────────────────
    posted = 0
    errors = 0
    max_id = last_id

    for ann in annotations:
        try:
            cp_post_highlight(cp_token, ann)
            posted += 1
            if int(ann["id"]) > max_id:
                max_id = int(ann["id"])
            preview = ann["text"][:70].replace("\n", " ")
            log(f"  [+] [{ann['id']}] \"{preview}\"")
        except Exception as e:
            errors += 1
            log(f"  [x] [{ann['id']}] {e}")

    # ── Save state ─────────────────────────────────────────────────────
    state["last_synced_id"] = max_id
    state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    log(f"State saved: last_synced_id={max_id}")

    # ── Report ─────────────────────────────────────────────────────────
    result = {"posted": posted, "errors": errors, "last_id": max_id}
    print(json.dumps(result))

    if errors > 0:
        sys.exit(3)


if __name__ == "__main__":
    main()
