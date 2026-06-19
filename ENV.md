# Commonplace — Environment Variables

Below are all environment variables supported by the Commonplace application, their default values, and what they control.

| Variable | Default | Description |
|---|---|---|
| **COMMONPLACE_USERNAME** | _(none — required for first run)_ | Admin username for initial user creation. On first run, if this variable is set (along with `COMMONPLACE_PASSWORD`), an admin user is created automatically. Otherwise the setup wizard prompts for credentials. In `docker-compose.yml` the default is `admin` via `${COMMONPLACE_USERNAME:-admin}`. Used in `app/auth.py`. |
| **COMMONPLACE_PASSWORD** | _(none — required for first run)_ | Admin password for initial user creation. Must be set together with `COMMONPLACE_USERNAME` for automatic first-run setup. Used in `app/auth.py`. |
| **SESSION_SECRET** | _(auto-generated — persisted to `data/.session_secret`)_ | Secret key used for signing session cookies and CSRF tokens. If not set, a random 64-character hex string is generated on first start and written to `data/.session_secret`. **For production deployments, set this explicitly** — changing it invalidates all existing sessions. Used in `app/main.py` and `app/csrf.py`. |
| **SESSION_HTTPS_ONLY** | `"false"` | Controls the `https_only` flag on the session cookie. Set to `"true"` in production environments with TLS to prevent the session cookie from being sent over unencrypted HTTP connections. In local development without TLS, leave as `"false"`. Used in `app/main.py`. |
| **DATABASE_URL** | `"sqlite+aiosqlite:////app/data/commonplace.db"` | Database connection URL for SQLAlchemy's async engine. Defaults to a SQLite database at `/app/data/commonplace.db`. Set to any SQLAlchemy async-compatible URL (e.g., `postgresql+asyncpg://...`) to use a different database backend. Used in `app/database.py` (referenced in `app/routes/backup.py`). |
| **COVERS_DIR** | `./data/covers/` (relative to project root) | Directory path for storing downloaded book cover images. Mounted as static files at `/static/covers/`. Created automatically on startup with `chmod 755`. Used in `app/main.py`, `app/services/highlight_card.py`, `app/routes/books.py`, and `app/routes/backup.py`. |
| **HARDCOVER_API_KEY** | `""` (empty — disabled) | API key for [Hardcover.app](https://hardcover.app/account/api) GraphQL API. Used as the primary book cover lookup source (fallback chain: Hardcover → Open Library). When empty, the Hardcover search is skipped and only Open Library (free, no key) is used. Used in `app/services/book_covers.py`. |

## Files that reference these variables

| File | Variables |
|---|---|
| `app/main.py` | `COVERS_DIR`, `SESSION_SECRET`, `SESSION_HTTPS_ONLY` |
| `app/database.py` | `DATABASE_URL` |
| `app/auth.py` | `COMMONPLACE_USERNAME`, `COMMONPLACE_PASSWORD` |
| `app/csrf.py` | `SESSION_SECRET` |
| `app/services/book_covers.py` | `HARDCOVER_API_KEY` |
| `app/services/highlight_card.py` | `COVERS_DIR` |
| `app/routes/books.py` | `COVERS_DIR` |
| `app/routes/backup.py` | `COVERS_DIR` |
| `docker-compose.yml` | `COMMONPLACE_USERNAME`, `COMMONPLACE_PASSWORD`, `SESSION_SECRET` |
| `env.example` | All seven variables documented with descriptions |

## docker-compose.yml defaults

The `docker-compose.yml` file sets `COMMONPLACE_USERNAME` with a shell-variable default of `admin` (`${COMMONPLACE_USERNAME:-admin}`). `COMMONPLACE_PASSWORD` and `SESSION_SECRET` have no defaults and are pulled directly from the `.env` file.
