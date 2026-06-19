# Book Metadata (HardCover ID + ISBN) Implementation Plan

> **For Hermes:** Use the task list below. Each task is independent enough to delegate or work through sequentially.

**Goal:** Add `hardcover_id` and `isbn` columns to the `BookCover` model so users can manually set or auto-capture a HardCover book ID and ISBN. This lets cover resolution skip the brittle fuzzy search and go direct to `books_by_pk(id)` — faster, deterministic, and correctable by the user.

**Why this works:**
- Highlights carry `book_title` + `book_author` as plain strings — no FK to a book ID
- Adding metadata to `BookCover` is purely additive; sync/import matching is unaffected
- Book rename already updates `BookCover.book_title` — IDs follow naturally
- Book merge already deletes the source BookCover — target's IDs survive

**Design decisions:**
- Add columns only to `BookCover` (not a new Book model) — YAGNI
- `_hardcover_search()` returns IDs alongside the cover URL so callers can save them
- Manual override endpoint lets the user correct auto-assigned IDs
- Cover resolution checks `hardcover_id` first before doing a fuzzy search

---

## Task 1: Model + Migration

**Objective:** Add `hardcover_id` (Integer, nullable) and `isbn` (String(20), nullable) to BookCover model with a safe migration.

**Files:**
- Modify: `app/models.py` — add columns to BookCover
- Modify: `app/database.py` — add ALTER TABLE migration

**Model change** (`app/models.py:BookCover`):
```python
class BookCover(Base):
    __tablename__ = "book_covers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_title = Column(String(511), nullable=False)
    book_author = Column(String(511), nullable=False, default="")
    cover_source = Column(String(16), nullable=False, default="none")
    cover_url = Column(String(1024), nullable=True)
    hardcover_id = Column(Integer, nullable=True)    # NEW
    isbn = Column(String(20), nullable=True)          # NEW
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("book_title", "book_author", name="uq_book_cover"),
    )
```

**Migration** (`app/database.py`, in the `init_db()` function, after the share_token migration block):
```python
# ── BookCover metadata columns ──────────────────────────────────────────
async with engine.begin() as conn:
    pragma2 = await conn.execute(sqltext("PRAGMA table_info('book_covers')"))
    bc_cols = {row[1] for row in pragma2.fetchall()}
    if "hardcover_id" not in bc_cols:
        await conn.execute(sqltext("ALTER TABLE book_covers ADD COLUMN hardcover_id INTEGER"))
        print("  Migration: added hardcover_id to book_covers")
    if "isbn" not in bc_cols:
        await conn.execute(sqltext("ALTER TABLE book_covers ADD COLUMN isbn VARCHAR(20)"))
        print("  Migration: added isbn to book_covers")
```

**Validation:**
- Start the app and check logs for `Migration: added hardcover_id to book_covers`
- Run `sqlite3 data/commonplace.db ".schema book_covers"` to confirm columns exist

---

## Task 2: Cover Enrichment — Save IDs During Cover Lookup

**Objective:** Change `_hardcover_search()` to return the HardCover ID and ISBN alongside the cover URL, and have callers save them to the BookCover record.

**Files:**
- Modify: `app/services/book_covers.py` — return tuple from `_hardcover_search()`
- Modify: `app/services/book_covers.py` — update `search_cover()` to propagate the tuple
- Modify: `app/routes/books.py` — save IDs in `fetch_cover()` and `backfill_covers()`

### 2a: Change `_hardcover_search()` return type

Current signature:
```python
async def _hardcover_search(title, author, client, api_key="") -> Optional[str]:
```

New signature:
```python
async def _hardcover_search(title, author, client, api_key="") -> Optional[tuple[str, Optional[int], Optional[str]]]:
    # Returns (cover_url, hardcover_id, isbn) or None
```

Within the function:
- When HardCover returns search results, extract the ID from the search data (it's in `ids_list[0]`) and any ISBN if available
- When doing the `books_by_pk` fallback, also extract ID and ISBN from the book data
- Return `(cover_url, hardcover_id, isbn)` if a cover URL was found

Look for the `ids_list[0]` usage at line ~118-135 and capture the ID there:

```python
# In the books_by_pk fallback block (~line 118-135):
if ids_list:
    bid = ids_list[0]
    book_query = "{ book: books_by_pk(id: " + str(bid) + ") { id title slug isbn image { url } } }"
    book_resp = await client.post(...)
    if book_resp.status_code == 200:
        book_data = book_resp.json().get("data", {}).get("book", {})
        if book_data:
            img = book_data.get("image")
            if img and isinstance(img, dict) and img.get("url"):
                return (img["url"], book_data.get("id"), book_data.get("isbn"))
            slug = book_data.get("slug")
            if slug:
                return (f"https://hardcovercdn.com/books/{slug}.jpg", book_data.get("id"), book_data.get("isbn"))
```

Also try to extract ID + ISBN from the initial results before the fallback (at ~line 106-115, where direct cover URL is found). If we have a cover but no ID yet, use `ids_list[0]` if available.

### 2b: Update `search_cover()` signature

```python
async def search_cover(title, author="", client=None, hardcover_key="") -> tuple[Optional[str], str]:
```
becomes:
```python
async def search_cover(title, author="", client=None, hardcover_key="") -> tuple[Optional[str], str, Optional[int], Optional[str]]:
    # Returns (cover_url, source_name, hardcover_id, isbn)
```

Update the HardCover branch:
```python
result = await _hardcover_search(title, author, client, api_key=hardcover_key)
if result:
    url, hc_id, isbn = result
    return url, "hardcover", hc_id, isbn
```

### 2c: Update callers in `app/routes/books.py`

In `fetch_cover()` (line 132-155), update to save IDs:

```python
@router.post("/api/books/cover/fetch")
async def fetch_cover(title: str = Form(...), author: str = Form(default=""), source: str = Form(default="auto"), db: AsyncSession = Depends(get_db)):
    try:
        hc_key = get_hardcover_api_key()
        url, cover_source, hc_id, isbn = await search_cover(title, author, hardcover_key=hc_key)
        if not url:
            return {"ok": False, "error": "No cover found"}

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
            if hc_id is not None:
                cover.hardcover_id = hc_id
            if isbn is not None:
                cover.isbn = isbn
        else:
            db.add(BookCover(
                book_title=title, book_author=author,
                cover_url=url, cover_source=cover_source,
                hardcover_id=hc_id, isbn=isbn,
            ))
        await db.commit()
        return {"ok": True, "cover_url": url, "source": cover_source}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
```

In `backfill_covers()` (line 441-464), same treatment — save IDs when they come back.

**Validation:**
- Visit /books, click 🔍 on a book that has a HardCover match
- Check `sqlite3 data/commonplace.db "SELECT hardcover_id, isbn FROM book_covers WHERE hardcover_id IS NOT NULL LIMIT 5"`
- Should show populated IDs

---

## Task 3: Use `hardcover_id` to Skip Fuzzy Search

**Objective:** When a BookCover record already has `hardcover_id` set, skip the fuzzy `search()` GraphQL query entirely and go straight to `books_by_pk(id)`.

**Files:**
- Modify: `app/services/book_covers.py` — add shortcut at the start of `_hardcover_search()`

**Change** (at the top of `_hardcover_search()`, before any API call):

```python
async def _hardcover_search(title, author, client, api_key="", known_id=None) -> Optional[tuple[str, Optional[int], Optional[str]]]:
    key = api_key or HARDCOVER_API_KEY
    if not key:
        return None

    # If we already have a known HardCover ID, skip the fuzzy search entirely
    if known_id is not None:
        book_query = """
        query BookById($id: Int!) {
          book: books_by_pk(id: $id) {
            id title slug isbn image { url }
          }
        }
        """
        payload = {"query": book_query, "variables": {"id": known_id}}
        try:
            resp = await client.post(
                "https://api.hardcover.app/v1/graphql",
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                book_data = resp.json().get("data", {}).get("book", {})
                if book_data:
                    img = book_data.get("image")
                    if img and isinstance(img, dict) and img.get("url"):
                        return (img["url"], book_data.get("id"), book_data.get("isbn"))
                    slug = book_data.get("slug")
                    if slug:
                        return (f"https://hardcovercdn.com/books/{slug}.jpg", book_data.get("id"), book_data.get("isbn"))
        except Exception as e:
            print(f"  [covers] HardCover books_by_pk({known_id}) error: {e}")
        return None

    # ... rest of existing function (fuzzy search logic) ...
```

Then update `search_cover()` to look up the known_id from the caller:

```python
async def search_cover(title, author="", client=None, hardcover_key="", known_id=None) -> tuple[Optional[str], str, Optional[int], Optional[str]]:
    _owns_client = client is None
    if _owns_client:
        client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    try:
        # 1. Hardcover.app (with optional known ID shortcut)
        result = await _hardcover_search(title, author, client, api_key=hardcover_key, known_id=known_id)
        if result:
            url, hc_id, isbn = result
            return url, "hardcover", hc_id, isbn

        # 2. Open Library (unchanged)
        url = await _open_library_search(title, author, client)
        if url:
            return url, "openlibrary", None, None
    finally:
        if _owns_client:
            await client.aclose()
    return None, "", None, None
```

And in `fetch_cover()` in `books.py`, look up the existing BookCover first to pass `known_id`:

```python
@router.post("/api/books/cover/fetch")
async def fetch_cover(title: str = Form(...), author: str = Form(default=""), ...):
    # Look up existing record first
    existing = await db.execute(
        select(BookCover).where(
            BookCover.book_title == title,
            BookCover.book_author == author,
        )
    )
    existing_cover = existing.scalar_one_or_none()
    known_id = existing_cover.hardcover_id if existing_cover else None

    hc_key = get_hardcover_api_key()
    url, cover_source, hc_id, isbn = await search_cover(title, author, hardcover_key=hc_key, known_id=known_id)
    # ...
```

**Validation:**
- Set a hardcover_id manually on a book, then click 🔍 — should see `[covers] HardCover books_by_pk(X)` log instead of `[covers] HardCover search: N results`
- No fuzzy search log lines should appear for that book

---

## Task 4: Manual Edit API Endpoint

**Objective:** Create an API endpoint so the user (or a future backfill script) can manually set a book's HardCover ID and ISBN.

**Files:**
- Create: none (add to existing `books.py`)
- Modify: `app/routes/books.py` — add `/api/books/metadata` endpoint

**New endpoint:**

```python
@router.post("/api/books/metadata")
async def set_book_metadata(
    title: str = Form(...),
    author: str = Form(default=""),
    hardcover_id: str = Form(default=""),
    isbn: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Manually set or update HardCover ID and ISBN for a book.
    
    Saves metadata to the BookCover record. If no BookCover exists yet,
    creates one. Then optionally triggers a cover fetch using the new ID.
    Returns the current cover URL if one was found.
    """
    author = author or ""
    hc_id = None
    if hardcover_id.strip():
        try:
            hc_id = int(hardcover_id.strip())
        except ValueError:
            return {"ok": False, "error": "HardCover ID must be a number"}

    isbn_val = isbn.strip() or None

    # Find or create BookCover record
    result = await db.execute(
        select(BookCover).where(
            BookCover.book_title == title,
            BookCover.book_author == author,
        )
    )
    cover = result.scalar_one_or_none()
    if cover:
        cover.hardcover_id = hc_id
        cover.isbn = isbn_val
    else:
        cover = BookCover(
            book_title=title, book_author=author,
            hardcover_id=hc_id, isbn=isbn_val,
        )
        db.add(cover)
    await db.commit()

    # If a HardCover ID was provided, do an immediate look-up
    url = cover.cover_url
    source = cover.cover_source
    if hc_id is not None:
        hc_key = get_hardcover_api_key()
        result = await search_cover(title, author, hardcover_key=hc_key, known_id=hc_id)
        new_url, new_source, _, _ = result
        if new_url:
            cover.cover_url = new_url
            cover.cover_source = new_source
            url = new_url
            source = new_source
            await db.commit()

    return {
        "ok": True,
        "hardcover_id": hc_id,
        "isbn": isbn_val,
        "cover_url": url,
        "cover_source": source,
    }
```

**Validation:**
```bash
curl -X POST http://localhost:8765/api/books/metadata \
  -d "title=The+Brothers+Karamazov" \
  -d "author=Fyodor+Dostoevsky" \
  -d "hardcover_id=12345"
```
Expected: `{"ok": true, "hardcover_id": 12345, ...}`

---

## Task 5: UI — Edit Metadata from the Books Page

**Objective:** Add UI for the user to view and edit a book's HardCover ID and ISBN. Keep it simple — reuse the existing rename modal pattern.

**Files:**
- Modify: `app/templates/books.html` — add metadata modal + trigger icon

**Approach:**
Add a new "🏷️" icon in the book card action row (next to ✏️🔍📤). Clicking it opens a small modal with two text fields: HardCover ID and ISBN. On save, it calls the `/api/books/metadata` endpoint, then refreshes the cover.

Add after the rename modal block:

```html
<!-- Metadata Modal -->
<div id="metadata-modal" class="fixed inset-0 z-50 hidden bg-black/40 flex items-center justify-center">
  <div class="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 overflow-hidden" onclick="event.stopPropagation()">
    <div class="px-6 py-4 border-b border-slate-100">
      <h3 class="text-lg font-semibold text-slate-900">🏷️ Book Metadata</h3>
    </div>
    <form id="metadata-form" class="p-6 space-y-4" onsubmit="return submitMetadata(event)">
      <input type="hidden" id="meta-title" name="title" />
      <input type="hidden" id="meta-author" name="author" />
      <div>
        <label for="meta-hardcover-id" class="block text-sm font-medium text-slate-700 mb-1">HardCover ID</label>
        <input type="number" id="meta-hardcover-id" name="hardcover_id"
               class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
               placeholder="e.g. 12345" />
        <p class="text-xs text-slate-400 mt-1">Found in the URL: hardcover.app/books/<strong>12345</strong>/title</p>
      </div>
      <div>
        <label for="meta-isbn" class="block text-sm font-medium text-slate-700 mb-1">ISBN</label>
        <input type="text" id="meta-isbn" name="isbn"
               class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
               placeholder="e.g. 9780140449242" />
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick="closeMetadataModal()" class="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50">Cancel</button>
        <button type="submit" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700">Save</button>
      </div>
    </form>
  </div>
</div>
```

Add metadata trigger icon to the book card action row (in the books grid loop, after the 🔍 icon):
```html
<span onclick="event.preventDefault(); event.stopPropagation(); openMetadata(this)" class="text-xs text-slate-400 hover:text-purple-500 cursor-pointer" title="Edit HardCover ID / ISBN">🏷️</span>
```

Add JavaScript functions (in the scripts block):

```javascript
var metaCard = null;

function openMetadata(el) {
  metaCard = el.closest('[data-hl-id]');
  if (!metaCard) { showToast('Could not find book data', 'error'); return; }
  var title = metaCard.dataset.title;
  var author = metaCard.dataset.author;

  document.getElementById('meta-title').value = title || '';
  document.getElementById('meta-author').value = (author === 'Unknown' ? '' : (author || ''));
  document.getElementById('meta-hardcover-id').value = '';
  document.getElementById('meta-isbn').value = '';
  document.getElementById('metadata-modal').classList.remove('hidden');
}

function closeMetadataModal() {
  document.getElementById('metadata-modal').classList.add('hidden');
  metaCard = null;
}

function submitMetadata(event) {
  event.preventDefault();
  var btn = event.target.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  var fd = new FormData(document.getElementById('metadata-form'));
  fetch('/api/books/metadata', { method: 'POST', body: fd })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        if (d.cover_url && metaCard) updateCoverImage(metaCard, d.cover_url);
        showToast('Metadata saved', 'success');
        closeMetadataModal();
      } else {
        showToast('Error: ' + (d.error || 'unknown'), 'error');
      }
    })
    .catch(function(e) {
      showToast('Network error: ' + e.message, 'error');
    })
    .finally(function() {
      btn.disabled = false;
      btn.textContent = 'Save';
    });
}

document.getElementById('metadata-modal')?.addEventListener('click', closeMetadataModal);
```

**Validation:**
- Open /books, click 🏷️ on a book
- Enter HardCover ID "12345" (or any real ID for a book you own)
- Click save — cover should update with the correct book's cover
- Refresh the page — cover should still be correct (was persisted)

---

## Task 6: Backfill Existing Books

**Objective:** For books that already have a HardCover-sourced cover but no saved `hardcover_id`, search HardCover and save the ID. This is a one-time pass that runs during backfill.

**Files:**
- Modify: `app/routes/books.py` — extend `backfill_covers()` to store IDs

In `backfill_covers()` (line 441), after fetching a cover, if the source was "hardcover", try to get the hardcover_id:

```python
@router.post("/api/books/cover/backfill")
async def backfill_covers(db: AsyncSession = Depends(get_db)):
    hc_key = get_hardcover_api_key()
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
        cover_row = existing.scalar_one_or_none()
        if cover_row and cover_row.hardcover_id is not None:
            continue  # Already has an ID

        url, cover_source, hc_id, isbn = await search_cover(
            row.book_title, row.book_author or "",
            hardcover_key=hc_key,
            known_id=cover_row.hardcover_id if cover_row else None,
        )
        if url:
            if cover_row:
                cover_row.cover_url = url
                cover_row.cover_source = cover_source
                if hc_id is not None:
                    cover_row.hardcover_id = hc_id
                if isbn is not None:
                    cover_row.isbn = isbn
            else:
                db.add(BookCover(
                    book_title=row.book_title,
                    book_author=row.book_author or "",
                    cover_url=url, cover_source=cover_source,
                    hardcover_id=hc_id, isbn=isbn,
                ))
            fetched += 1
            await db.commit()
    return {"ok": True, "fetched": fetched}
```

**Validation:**
- Click "🔄 Fetch Covers" on /books
- Check DB: `SELECT book_title, hardcover_id, isbn FROM book_covers WHERE hardcover_id IS NOT NULL`

---

## Task 7: Version Bump + Commit

**Objective:** Bump the version string and git tag, then commit all changes.

**Files:**
- Modify: `app/main.py` — bump `version="0.6.7"`
- git commit + tag

```bash
git add -A
git commit -m "v0.6.7 — Book metadata: HardCover ID + ISBN on BookCover model"
git tag v0.6.7
git push origin main --tags
```

---

## Files Changed (Summary)

| File | Change |
|------|--------|
| `app/models.py` | Add `hardcover_id` (Integer) + `isbn` (String(20)) to BookCover |
| `app/database.py` | Migration: ALTER TABLE book_covers ADD COLUMN for both |
| `app/services/book_covers.py` | `_hardcover_search()` returns tuple; `search_cover()` propagates; `known_id` shortcut |
| `app/routes/books.py` | `fetch_cover()` and `backfill_covers()` save IDs; new `POST /api/books/metadata` |
| `app/templates/books.html` | Metadata modal + 🏷️ trigger icon + JS |
| `app/main.py` | Version bump to 0.6.7 |

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|-----------|
| Invalid HardCover ID entered manually | Endpoint validates it's an integer; `books_by_pk` returns null gracefully if ID doesn't exist |
| ISBN format inconsistency (with/without hyphens) | Store as plain string, no validation beyond length; search uses stripped value |
| HardCover API key not configured | The `known_id` shortcut checks for the key first — if no key, falls through to Open Library |
| Book rename with IDs | The rename endpoint already updates `BookCover.book_title` — IDs follow the record naturally |
| Merge keeps wrong ID | Current merge deletes source BookCover; target's IDs survive — correct behavior |

## Open Questions

1. **String representation of ISBN in the UI?** — Should we auto-format ISBN-10 vs ISBN-13 with hyphens, or just store as-is?
2. **Batch backfill on startup?** — The existing `backfill_covers()` is manual (button click). Should we add an auto-backfill on app startup for books that lack IDs but already have HardCover covers? Probably defer — manual is fine for now.
3. **Should setting a HardCover ID auto-fetch the cover?** — Yes, done in the metadata endpoint (Task 4). Saves an extra click.
