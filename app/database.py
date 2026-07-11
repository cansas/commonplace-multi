from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import sqlalchemy
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:////app/data/commonplace.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    from sqlalchemy import text as sqltext

    async with engine.begin() as conn:
        from app.models import Base  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    # ═══════════════════════════════════════════════════════════════════
    # MULTI-USER MIGRATION — single-user DB → multi-user (user_id cols)
    # ═══════════════════════════════════════════════════════════════════
    # Detects an existing single-user DB (no user_id column on highlights)
    # and recreates each content table with user_id. All existing data
    # is assigned to user_id=1 (the admin user).
    async with engine.begin() as conn:
        pragma = await conn.execute(sqltext("PRAGMA table_info('highlights')"))
        hl_cols = {row[1] for row in pragma.fetchall()}

        if "user_id" not in hl_cols:
            print("  === Multi-user fork migration ===")
            print("  Detected single-user DB — adding user_id to all content tables...")

            # Drop FTS triggers + table (will be rebuilt later in init_db)
            await conn.execute(sqltext("DROP TRIGGER IF EXISTS highlights_ai"))
            await conn.execute(sqltext("DROP TRIGGER IF EXISTS highlights_ad"))
            await conn.execute(sqltext("DROP TRIGGER IF EXISTS highlights_au"))
            await conn.execute(sqltext("DROP TABLE IF EXISTS highlights_fts"))

            # ── highlights ──────────────────────────────────────────────
            print("  Migrating: highlights")
            await conn.execute(sqltext(
                "ALTER TABLE highlights ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            await conn.execute(sqltext(
                "UPDATE highlights SET user_id = 1 WHERE user_id IS NULL"
            ))

        # ── tags ────────────────────────────────────────────────────
        pragma = await conn.execute(sqltext("PRAGMA table_info('tags')"))
        tag_cols = {row[1] for row in pragma.fetchall()}
        if "user_id" not in tag_cols:
            print("  Migrating: tags")
            old_tags = (await conn.execute(sqltext(
                "SELECT id, name, color FROM tags"
            ))).fetchall()
            await conn.execute(sqltext("DROP TABLE IF EXISTS tags_v2"))
            await conn.execute(sqltext(
                "CREATE TABLE tags_v2 ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  user_id INTEGER NOT NULL REFERENCES users(id),"
                "  name VARCHAR(128) NOT NULL,"
                "  color VARCHAR(7),"
                "  UNIQUE(user_id, name)"
                ")"
            ))
            for row in old_tags:
                await conn.execute(
                    sqltext(
                        "INSERT INTO tags_v2 (id, user_id, name, color) VALUES (:id, 1, :name, :color)"
                    ),
                    {"id": row[0], "name": row[1], "color": row[2]},
                )
            await conn.execute(sqltext("DROP TABLE tags"))
            await conn.execute(sqltext("ALTER TABLE tags_v2 RENAME TO tags"))

        # ── sources ─────────────────────────────────────────────────
        pragma = await conn.execute(sqltext("PRAGMA table_info('sources')"))
        src_cols = {row[1] for row in pragma.fetchall()}
        if "user_id" not in src_cols:
            print("  Migrating: sources")
            old_srcs = (await conn.execute(sqltext(
                "SELECT id, name, source_type, last_import_at, last_hash, highlights_imported FROM sources"
            ))).fetchall()
            await conn.execute(sqltext("DROP TABLE IF EXISTS sources_v2"))
            await conn.execute(sqltext(
                "CREATE TABLE sources_v2 ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  user_id INTEGER NOT NULL REFERENCES users(id),"
                "  name VARCHAR(255) NOT NULL,"
                "  source_type VARCHAR(64) NOT NULL,"
                "  last_import_at TIMESTAMP,"
                "  last_hash VARCHAR(128),"
                "  highlights_imported INTEGER DEFAULT 0"
                ")"
            ))
            for row in old_srcs:
                await conn.execute(
                    sqltext(
                        "INSERT INTO sources_v2 (id, user_id, name, source_type, last_import_at, last_hash, highlights_imported) "
                        "VALUES (:id, 1, :name, :st, :lia, :lh, :hi)"
                    ),
                    {"id": row[0], "name": row[1], "st": row[2], "lia": row[3], "lh": row[4], "hi": row[5]},
                )
            await conn.execute(sqltext("DROP TABLE sources"))
            await conn.execute(sqltext("ALTER TABLE sources_v2 RENAME TO sources"))

        # ── review_log ──────────────────────────────────────────────
        pragma = await conn.execute(sqltext("PRAGMA table_info('review_log')"))
        rl_cols = {row[1] for row in pragma.fetchall()}
        if "user_id" not in rl_cols:
            print("  Migrating: review_log")
            old_rls = (await conn.execute(sqltext(
                "SELECT id, highlight_id, reviewed_at, rating, ease_factor, interval, repetitions, next_review_at "
                "FROM review_log"
            ))).fetchall()
            await conn.execute(sqltext("DROP TABLE IF EXISTS review_log_v2"))
            await conn.execute(sqltext(
                "CREATE TABLE review_log_v2 ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  user_id INTEGER NOT NULL REFERENCES users(id),"
                "  highlight_id INTEGER NOT NULL REFERENCES highlights(id),"
                "  reviewed_at TIMESTAMP,"
                "  rating INTEGER,"
                "  ease_factor FLOAT DEFAULT 2.5,"
                "  interval INTEGER DEFAULT 0,"
                "  repetitions INTEGER DEFAULT 0,"
                "  next_review_at TIMESTAMP"
                ")"
            ))
            for row in old_rls:
                await conn.execute(
                    sqltext(
                        "INSERT INTO review_log_v2 (id, user_id, highlight_id, reviewed_at, rating, ease_factor, interval, repetitions, next_review_at) "
                        "VALUES (:id, 1, :hl_id, :ra, :rating, :ef, :intv, :rep, :nra)"
                    ),
                    {"id": row[0], "hl_id": row[1], "ra": row[2], "rating": row[3],
                     "ef": row[4], "intv": row[5], "rep": row[6], "nra": row[7]},
                )
            await conn.execute(sqltext("DROP TABLE review_log"))
            await conn.execute(sqltext("ALTER TABLE review_log_v2 RENAME TO review_log"))

        # ── daily_review_queue ──────────────────────────────────────
        pragma = await conn.execute(sqltext("PRAGMA table_info('daily_review_queue')"))
        drq_cols = {row[1] for row in pragma.fetchall()}
        if "user_id" not in drq_cols:
                old_drqs = (await conn.execute(sqltext(
                    "SELECT id, highlight_id, queue_date, position, reviewed FROM daily_review_queue"
                ))).fetchall()

                await conn.execute(sqltext("DROP TABLE IF EXISTS daily_review_queue_v2"))
                await conn.execute(sqltext(
                    "CREATE TABLE daily_review_queue_v2 ("
                    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "  user_id INTEGER NOT NULL REFERENCES users(id),"
                    "  highlight_id INTEGER NOT NULL REFERENCES highlights(id),"
                    "  queue_date DATE NOT NULL,"
                    "  position INTEGER NOT NULL,"
                    "  reviewed INTEGER DEFAULT 0,"
                    "  UNIQUE(user_id, queue_date, position)"
                    ")"
                ))
                for row in old_drqs:
                    await conn.execute(
                        sqltext(
                            "INSERT INTO daily_review_queue_v2 (id, user_id, highlight_id, queue_date, position, reviewed) "
                            "VALUES (:id, 1, :hl_id, :qd, :pos, :rev)"
                        ),
                        {"id": row[0], "hl_id": row[1], "qd": row[2], "pos": row[3], "rev": row[4]},
                    )
                await conn.execute(sqltext("DROP TABLE daily_review_queue"))
                await conn.execute(sqltext("ALTER TABLE daily_review_queue_v2 RENAME TO daily_review_queue"))

        # ── book_covers ─────────────────────────────────────────────
        print("  Migrating: book_covers")
        pragma = await conn.execute(sqltext("PRAGMA table_info('book_covers')"))
        bc_cols = {row[1] for row in pragma.fetchall()}
        if "user_id" not in bc_cols:
            old_bcs = (await conn.execute(sqltext(
                "SELECT id, book_title, book_author, cover_source, cover_url, hardcover_id, isbn, updated_at "
                "FROM book_covers"
            ))).fetchall()

            await conn.execute(sqltext("DROP TABLE IF EXISTS book_covers_v2"))
            await conn.execute(sqltext(
                "CREATE TABLE book_covers_v2 ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  user_id INTEGER NOT NULL REFERENCES users(id),"
                "  book_title VARCHAR(511) NOT NULL,"
                "  book_author VARCHAR(511) NOT NULL DEFAULT '',"
                "  cover_source VARCHAR(16) NOT NULL DEFAULT 'none',"
                "  cover_url VARCHAR(1024),"
                "  hardcover_id INTEGER,"
                "  isbn VARCHAR(20),"
                "  updated_at TIMESTAMP,"
                "  UNIQUE(user_id, book_title, book_author)"
                ")"
            ))
            for row in old_bcs:
                await conn.execute(
                    sqltext(
                        "INSERT INTO book_covers_v2 (id, user_id, book_title, book_author, cover_source, cover_url, hardcover_id, isbn, updated_at) "
                        "VALUES (:id, 1, :bt, :ba, :cs, :cu, :hcid, :isbn, :ua)"
                    ),
                    {"id": row[0], "bt": row[1], "ba": row[2], "cs": row[3], "cu": row[4],
                     "hcid": row[5], "isbn": row[6], "ua": row[7]},
                )
            await conn.execute(sqltext("DROP TABLE book_covers"))
            await conn.execute(sqltext("ALTER TABLE book_covers_v2 RENAME TO book_covers"))

        # ── user_achievements — update NULL user_id to 1 ────────────
        await conn.execute(sqltext(
            "UPDATE user_achievements SET user_id = 1 WHERE user_id IS NULL"
        ))

        # ── push_subscriptions — update NULL user_id to 1 ────────────
        await conn.execute(sqltext(
            "UPDATE push_subscriptions SET user_id = 1 WHERE user_id IS NULL"
        ))

        print("  Multi-user migration complete — all existing data assigned to user_id=1")

    # ═══════════════════════════════════════════════════════════════════
    # LEGACY MIGRATIONS (shared with upstream)
    # ═══════════════════════════════════════════════════════════════════
    # Migrations for existing databases — use PRAGMA to check column existence
    async with engine.begin() as conn:
        # Check which columns actually exist in highlights
        pragma = await conn.execute(sqltext("PRAGMA table_info('highlights')"))
        existing = {row[1] for row in pragma.fetchall()}  # row[1] = column name

        pending = []
        if "favorite" not in existing:
            pending.append("ALTER TABLE highlights ADD COLUMN favorite INTEGER DEFAULT 0")
        if "share_token" not in existing:
            pending.append("ALTER TABLE highlights ADD COLUMN share_token VARCHAR(64)")

        for stmt in pending:
            print(f"  Running migration: {stmt}")
            await conn.execute(sqltext(stmt))

        # Fingerprint column for import dedup
        if "fingerprint" not in existing:
            await conn.execute(sqltext(
                "ALTER TABLE highlights ADD COLUMN fingerprint VARCHAR(64)"
            ))
            print("  Migration: added fingerprint to highlights")

    # Backfill share_token for highlights that don't have one
    async with async_session() as session:
        from app.models import Highlight
        from app.routes.share import get_share_token
        from sqlalchemy import select
        result = await session.execute(
            select(Highlight).where(Highlight.share_token.is_(None))
        )
        missing = result.scalars().all()
        for hl in missing:
            hl.share_token = get_share_token()
        if missing:
            await session.commit()
            print(f"  Backfilled share_token for {len(missing)} highlights")

    # Backfill fingerprints for existing rows (one-time)
    async with async_session() as session:
        from app.services.import_service import highlight_fingerprint
        from sqlalchemy import select
        result = await session.execute(
            select(Highlight).where(Highlight.fingerprint.is_(None))
        )
        missing = result.scalars().all()
        if missing:
            print(f"  Backfilling fingerprints for {len(missing)} highlights...")
            for hl in missing:
                hl.fingerprint = highlight_fingerprint(hl.text, hl.book_title or "")
            await session.commit()

    # Create fingerprint index
    async with engine.begin() as conn:
        try:
            await conn.execute(sqltext(
                "CREATE INDEX IF NOT EXISTS ix_highlights_fingerprint "
                "ON highlights(fingerprint)"
            ))
        except sqlalchemy.exc.OperationalError:
            pass  # SQLite version or feature not supported
        except Exception as e:
            print(f"  WARNING: Could not create fingerprint index: {e}")

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

    # ── UserAchievements table ─────────────────────────────────────────────
    async with engine.begin() as conn:
        pragma3 = await conn.execute(sqltext("SELECT name FROM sqlite_master WHERE type='table' AND name='user_achievements'"))
        if not pragma3.fetchone():
            await conn.execute(sqltext(
                "CREATE TABLE user_achievements ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),"
                "  achievement_key VARCHAR(64) NOT NULL,"
                "  message VARCHAR(255),"
                "  unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
                "  UNIQUE(user_id, achievement_key)"
                ")"
            ))
            print("  Migration: created user_achievements table")

    # ── UserSettings table (multi-user fork) ──────────────────────────────
    async with engine.begin() as conn:
        pragma_usr = await conn.execute(sqltext(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'"
        ))
        if not pragma_usr.fetchone():
            await conn.execute(sqltext(
                "CREATE TABLE user_settings ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  user_id INTEGER NOT NULL REFERENCES users(id),"
                "  key VARCHAR(64) NOT NULL,"
                "  value TEXT NOT NULL,"
                "  UNIQUE(user_id, key)"
                ")"
            ))
            print("  Migration: created user_settings table")

    # ── Invites table (multi-user fork) ──────────────────────────────────
    async with engine.begin() as conn:
        pragma_inv = await conn.execute(sqltext(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='invites'"
        ))
        if not pragma_inv.fetchone():
            await conn.execute(sqltext(
                "CREATE TABLE invites ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  username VARCHAR(128) NOT NULL,"
                "  token VARCHAR(64) NOT NULL UNIQUE,"
                "  created_by INTEGER NOT NULL REFERENCES users(id),"
                "  expires_at TIMESTAMP NOT NULL,"
                "  used_at TIMESTAMP,"
                "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            print("  Migration: created invites table")

    # Seed user_settings from file for existing single-user DBs
    async with async_session() as session:
        from app.models import UserSetting
        from sqlalchemy import select, func
        usr_count = await session.execute(
            select(func.count(UserSetting.id)).where(UserSetting.user_id == 1)
        )
        if usr_count.scalar() == 0:
            from app.services.user_settings import migrate_from_file
            n = await migrate_from_file(session, 1)
            if n:
                print(f"  Seeded {n} user_settings from .settings.json for user_id=1")

    # ── Tags color column ───────────────────────────────────────────────────
    async with engine.begin() as conn:
        pragma4 = await conn.execute(sqltext("PRAGMA table_info('tags')"))
        tag_cols = {row[1] for row in pragma4.fetchall()}
        if "color" not in tag_cols:
            await conn.execute(sqltext("ALTER TABLE tags ADD COLUMN color VARCHAR(7)"))
            print("  Migration: added color to tags")

    # Create dedup index (text + book_title + highlighted_at)
    async with engine.begin() as conn:
        try:
            await conn.execute(sqltext(
                "CREATE INDEX IF NOT EXISTS ix_highlights_dedup "
                "ON highlights(text, book_title, highlighted_at)"
            ))
        except sqlalchemy.exc.OperationalError:
            pass  # SQLite version or feature not supported
        except Exception as e:
            print(f"  WARNING: Could not create dedup index: {e}")

    # ── FTS5 Full-Text Search ─────────────────────────────────────────────
    async with engine.begin() as conn:
        # Drop old external-content FTS table if upgrading
        await conn.execute(sqltext("DROP TABLE IF EXISTS highlights_fts"))
        # Create FTS5 virtual table (standalone — stores its own content)
        await conn.execute(sqltext(
            "CREATE VIRTUAL TABLE IF NOT EXISTS highlights_fts USING fts5("
            "  text, note, book_title, book_author,"
            "  tokenize='porter unicode61'"
            ")"
        ))
        # Sync triggers — AU fires only when FTS-relevant columns change
        # (not on favorite/share_token updates)
        await conn.execute(sqltext(
            "CREATE TRIGGER IF NOT EXISTS highlights_ai AFTER INSERT ON highlights BEGIN "
            "  INSERT INTO highlights_fts(rowid, text, note, book_title, book_author) "
            "  VALUES (new.id, new.text, new.note, new.book_title, new.book_author); "
            "END"
        ))
        await conn.execute(sqltext(
            "CREATE TRIGGER IF NOT EXISTS highlights_ad AFTER DELETE ON highlights BEGIN "
            "  DELETE FROM highlights_fts WHERE rowid = old.id; "
            "END"
        ))
        await conn.execute(sqltext(
            "CREATE TRIGGER IF NOT EXISTS highlights_au AFTER UPDATE OF text, note, book_title, book_author ON highlights BEGIN "
            "  DELETE FROM highlights_fts WHERE rowid = old.id; "
            "  INSERT INTO highlights_fts(rowid, text, note, book_title, book_author) "
            "  VALUES (new.id, new.text, new.note, new.book_title, new.book_author); "
            "END"
        ))

    # ── Database indexes ───────────────────────────────────────────────────
    # Add indexes on common filter columns used in WHERE/ORDER BY clauses
    async with engine.begin() as conn:
        for idx_stmt in [
            "CREATE INDEX IF NOT EXISTS ix_highlights_highlighted_at ON highlights(highlighted_at)",
            "CREATE INDEX IF NOT EXISTS ix_highlights_book_title ON highlights(book_title)",
            "CREATE INDEX IF NOT EXISTS ix_highlights_source_type ON highlights(source_type)",
            "CREATE INDEX IF NOT EXISTS ix_highlights_favorite ON highlights(favorite)",
            "CREATE INDEX IF NOT EXISTS ix_highlights_user_id ON highlights(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_review_log_highlight_id ON review_log(highlight_id)",
            "CREATE INDEX IF NOT EXISTS ix_review_log_reviewed_at ON review_log(reviewed_at)",
            "CREATE INDEX IF NOT EXISTS ix_review_log_user_id ON review_log(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_tags_user_id ON tags(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_daily_review_queue_user_id ON daily_review_queue(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_book_covers_user_id ON book_covers(user_id)",
        ]:
            try:
                await conn.execute(sqltext(idx_stmt))
            except Exception:
                pass  # Index may already exist or engine doesn't support

    # Backfill FTS index for existing highlights
    async with async_session() as session:
        from app.models import Highlight
        from sqlalchemy import select, func
        hl_count = await session.execute(select(func.count(Highlight.id)))
        total = hl_count.scalar() or 0

        # Check if FTS index needs backfilling
        try:
            fts_ok = await session.execute(
                sqltext("SELECT COUNT(*) FROM highlights_fts")
            )
            needs_backfill = (fts_ok.scalar() or 0) == 0
        except Exception:
            needs_backfill = True

        if needs_backfill and total > 0:
            print(f"  Backfilling FTS index for {total} highlights...")
            await session.execute(sqltext(
                "INSERT INTO highlights_fts(rowid, text, note, book_title, book_author) "
                "SELECT id, text, note, book_title, book_author FROM highlights"
            ))
            await session.commit()
            print("  FTS backfill complete")
