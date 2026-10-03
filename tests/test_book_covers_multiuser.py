"""Regression tests: book covers are per-user in the multi-user fork.

book_covers.user_id is NOT NULL in this fork. Every cover write must set it
and every cover read must be scoped to the requesting user — otherwise inserts
crash with `NOT NULL constraint failed: book_covers.user_id` and one user's
cover lookup can return (or overwrite) another user's row.
"""

import io

import pytest
import pytest_asyncio
from fastapi import UploadFile
from sqlalchemy import select, text as sqltext

from app.models import BookCover, Highlight, User
from app.routes import books as books_routes
from tests.conftest import test_engine

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 256

# The FTS index is created by init_db()'s raw DDL, which the test fixture
# (Base.metadata.create_all) doesn't run. rename/delete rebuild it.
_FTS_DDL = [
    "DROP TABLE IF EXISTS highlights_fts",
    "DROP TRIGGER IF EXISTS highlights_ai",
    "DROP TRIGGER IF EXISTS highlights_ad",
    "DROP TRIGGER IF EXISTS highlights_au",
    "CREATE VIRTUAL TABLE IF NOT EXISTS highlights_fts USING fts5("
    "  text, note, book_title, book_author,"
    "  tokenize='porter unicode61'"
    ")",
    "CREATE TRIGGER IF NOT EXISTS highlights_ai AFTER INSERT ON highlights BEGIN "
    "  INSERT INTO highlights_fts(rowid, text, note, book_title, book_author) "
    "  VALUES (new.id, new.text, new.note, new.book_title, new.book_author); "
    "END",
    "CREATE TRIGGER IF NOT EXISTS highlights_ad AFTER DELETE ON highlights BEGIN "
    "  DELETE FROM highlights_fts WHERE rowid = old.id; "
    "END",
]


async def _ensure_fts(session):
    """Build a clean FTS index + triggers (matching init_db's raw DDL)."""
    for stmt in _FTS_DDL:
        await session.execute(sqltext(stmt))
    await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def _fts_isolation():
    """Drop the raw-SQL FTS objects after each test.

    The shared in-memory engine survives between tests, and
    Base.metadata.drop_all() can't remove FTS virtual tables or triggers —
    leaving them behind makes later inserts collide on FTS rowids.
    """
    yield
    async with test_engine.begin() as conn:
        for stmt in (
            "DROP TABLE IF EXISTS highlights_fts",
            "DROP TRIGGER IF EXISTS highlights_ai",
            "DROP TRIGGER IF EXISTS highlights_ad",
            "DROP TRIGGER IF EXISTS highlights_au",
        ):
            await conn.execute(sqltext(stmt))


async def _make_user(session, username: str) -> int:
    user = User(username=username, password_hash="x")
    session.add(user)
    await session.commit()
    return user.id


async def _add_highlight(session, user_id: int, title="Dune", author="Frank Herbert"):
    hl = Highlight(
        user_id=user_id, text="A beginning is a very delicate time.",
        book_title=title, book_author=author, source_type="manual",
    )
    session.add(hl)
    await session.commit()
    return hl.id


@pytest.mark.asyncio
async def test_save_cover_sets_user_id(db_session):
    """The crash from the bug report: insert without user_id."""
    uid = await _make_user(db_session, "cover-saver")
    result = await books_routes.save_cover_selection(
        title="Dune", author="Frank Herbert",
        cover_url="https://example.test/dune.jpg", source="openlibrary",
        hardcover_id="", isbn="", user_id=uid, db=db_session,
    )
    assert result["ok"] is True

    rows = (await db_session.execute(select(BookCover))).scalars().all()
    assert len(rows) == 1
    assert rows[0].user_id == uid


@pytest.mark.asyncio
async def test_two_users_can_hold_different_covers_for_same_book(db_session):
    """Same title/author must not collide, error, or leak between users."""
    u1 = await _make_user(db_session, "reader-one")
    u2 = await _make_user(db_session, "reader-two")

    for uid, url in ((u1, "https://example.test/one.jpg"), (u2, "https://example.test/two.jpg")):
        result = await books_routes.save_cover_selection(
            title="Dune", author="Frank Herbert",
            cover_url=url, source="openlibrary",
            hardcover_id="", isbn="", user_id=uid, db=db_session,
        )
        assert result["ok"] is True

    rows = (await db_session.execute(select(BookCover))).scalars().all()
    assert len(rows) == 2
    assert {r.user_id: r.cover_url for r in rows} == {
        u1: "https://example.test/one.jpg",
        u2: "https://example.test/two.jpg",
    }

    # _get_cover never returns the other user's row
    mine = await books_routes._get_cover(db_session, u1, "Dune", "Frank Herbert")
    assert mine.cover_url == "https://example.test/one.jpg"

    # Updating one user's cover leaves the other's alone
    await books_routes.save_cover_selection(
        title="Dune", author="Frank Herbert",
        cover_url="https://example.test/one-v2.jpg", source="hardcover",
        hardcover_id="", isbn="", user_id=u1, db=db_session,
    )
    other = await books_routes._get_cover(db_session, u2, "Dune", "Frank Herbert")
    assert other.cover_url == "https://example.test/two.jpg"


@pytest.mark.asyncio
async def test_uploaded_cover_files_are_per_user(db_session, tmp_path, monkeypatch):
    """Two users uploading a cover for the same book must not share a file."""
    monkeypatch.setattr(books_routes, "COVERS_DIR", str(tmp_path))
    u1 = await _make_user(db_session, "uploader-one")
    u2 = await _make_user(db_session, "uploader-two")

    urls = {}
    for uid in (u1, u2):
        upload = UploadFile(file=io.BytesIO(PNG), filename="cover.png")
        result = await books_routes.upload_cover(
            title="Dune", author="Frank Herbert", file=upload,
            user_id=uid, db=db_session,
        )
        assert result["ok"] is True
        urls[uid] = result["cover_url"]
        assert (tmp_path / result["cover_url"].split("/")[-1]).is_file()

    assert urls[u1] != urls[u2]

    rows = (await db_session.execute(select(BookCover))).scalars().all()
    assert {r.user_id for r in rows} == {u1, u2}

    # Re-uploading for u1 must not delete u2's file
    upload = UploadFile(file=io.BytesIO(PNG), filename="cover.png")
    again = await books_routes.upload_cover(
        title="Dune", author="Frank Herbert", file=upload, user_id=u1, db=db_session,
    )
    assert again["ok"] is True
    assert (tmp_path / urls[u2].split("/")[-1]).is_file()


@pytest.mark.asyncio
async def test_rename_book_is_scoped_to_user(db_session):
    await _ensure_fts(db_session)
    u1 = await _make_user(db_session, "renamer")
    u2 = await _make_user(db_session, "bystander")
    await _add_highlight(db_session, u1)
    await _add_highlight(db_session, u2)
    await books_routes.save_cover_selection(
        title="Dune", author="Frank Herbert",
        cover_url="https://example.test/dune.jpg", source="openlibrary",
        hardcover_id="", isbn="", user_id=u1, db=db_session,
    )

    result = await books_routes.rename_book(
        old_title="Dune", old_author="Frank Herbert",
        new_title="Dune Messiah", new_author="Frank Herbert",
        merge="", user_id=u1, db=db_session,
    )
    assert result["ok"] is True

    titles_u1 = (await db_session.execute(
        select(Highlight.book_title).where(Highlight.user_id == u1)
    )).scalars().all()
    titles_u2 = (await db_session.execute(
        select(Highlight.book_title).where(Highlight.user_id == u2)
    )).scalars().all()
    assert titles_u1 == ["Dune Messiah"]
    assert titles_u2 == ["Dune"]

    covers = (await db_session.execute(select(BookCover))).scalars().all()
    assert len(covers) == 1
    assert (covers[0].user_id, covers[0].book_title) == (u1, "Dune Messiah")


@pytest.mark.asyncio
async def test_delete_book_is_scoped_to_user(db_session):
    await _ensure_fts(db_session)
    u1 = await _make_user(db_session, "deleter")
    u2 = await _make_user(db_session, "keeper")
    await _add_highlight(db_session, u1)
    await _add_highlight(db_session, u2)

    result = await books_routes.delete_book(
        title="Dune", author="Frank Herbert", user_id=u1, db=db_session,
    )
    assert result["ok"] is True

    assert (await db_session.execute(
        select(Highlight).where(Highlight.user_id == u1)
    )).scalars().all() == []
    assert len((await db_session.execute(
        select(Highlight).where(Highlight.user_id == u2)
    )).scalars().all()) == 1


@pytest.mark.asyncio
async def test_cover_by_highlight_rejects_other_users_highlight(db_session):
    u1 = await _make_user(db_session, "owner")
    u2 = await _make_user(db_session, "intruder")
    hl_id = await _add_highlight(db_session, u2)

    result = await books_routes.fetch_cover_by_hl(hl_id=hl_id, user_id=u1, db=db_session)
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_backfill_covers_writes_user_scoped_rows(db_session, monkeypatch):
    u1 = await _make_user(db_session, "backfill-one")
    u2 = await _make_user(db_session, "backfill-two")
    await _add_highlight(db_session, u1, title="Dune")
    await _add_highlight(db_session, u2, title="Neuromancer")

    async def fake_search(title, author, **kwargs):
        return (f"https://example.test/{title}.jpg", "openlibrary", None, None)

    monkeypatch.setattr(books_routes, "search_cover", fake_search)
    monkeypatch.setattr(books_routes, "get_hardcover_api_key", lambda: "")

    result = await books_routes.backfill_covers(user_id=u1, db=db_session)
    assert result["ok"] is True and result["fetched"] == 1

    rows = (await db_session.execute(select(BookCover))).scalars().all()
    assert [(r.user_id, r.book_title) for r in rows] == [(u1, "Dune")]


@pytest.mark.asyncio
async def test_api_books_only_returns_requesting_users_books(db_session):
    u1 = await _make_user(db_session, "api-one")
    u2 = await _make_user(db_session, "api-two")
    await _add_highlight(db_session, u1, title="Dune")
    await _add_highlight(db_session, u1, title="Dune")  # same book, count 2
    await _add_highlight(db_session, u2, title="Neuromancer")

    payload = await books_routes.api_books(
        request=None, search="", sort="highlights", user_id=u1, db=db_session,
    )
    assert [b["title"] for b in payload["books"]] == ["Dune"]
    assert payload["books"][0]["highlight_count"] == 2
