# Commonplace — Environment Variables

Below are all environment variables supported by the Commonplace application, their default values, and what they control.

| Variable | Default | Description |
|---|---|---|
| **COMMONPLACE_USERNAME** | _(none — optional)_ | Admin username for initial user creation. **Optional** — on first run the setup wizard prompts for credentials in the browser. Only set this if you want to skip the wizard and auto-create the admin account. Used in `app/auth.py`. |
| **COMMONPLACE_PASSWORD** | _(none — optional)_ | Admin password for initial user creation. **Optional** — must be set together with `COMMONPLACE_USERNAME` if that is set. Used in `app/auth.py`. |
| **SESSION_SECRET** | _(auto-generated — persisted to `data/.session_secret`)_ | Secret key for signing session cookies and CSRF tokens. If not set, a random 64-character hex string is generated on first start and written to `data/.session_secret`. **For production deployments, set this explicitly** — changing it invalidates all existing sessions. Used in `app/main.py` and `app/csrf.py`. |
| **SESSION_HTTPS_ONLY** | `"false"` | Controls the `https_only` flag on the session cookie. Set to `"true"` in production with TLS to prevent the session cookie from being sent over unencrypted HTTP. Leave as `"false"` for local dev without TLS. Used in `app/main.py`. |
| **DATABASE_URL** | `"sqlite+aiosqlite:////app/data/commonplace.db"` | Database connection URL. Defaults to SQLite at `/app/data/commonplace.db`. Set to any SQLAlchemy async-compatible URL (e.g., `postgresql+asyncpg://...`) to use a different backend. Used in `app/database.py`. |
| **COVERS_DIR** | `./data/covers/` | Directory for book cover images. Mounted as static files at `/static/covers/`. Created automatically on startup. Used in `app/main.py`, `app/services/highlight_card.py`, `app/routes/books.py`, `app/routes/backup.py`. |
| **HARDCOVER_API_KEY** | `""` (empty — disabled) | API key for [Hardcover.app](https://hardcover.app/account/api) GraphQL API. Primary cover source (fallback: Hardcover → Open Library). When empty, only Open Library (free, no key) is used. Can also be set from the Settings page in the UI. Used in `app/services/book_covers.py`. |

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
| `env.example` | All seven variables documented |

## docker-compose.yml defaults

The `docker-compose.yml` sets `COMMONPLACE_USERNAME` with a shell-variable default of `admin` (`${COMMONPLACE_USERNAME:-admin}`). `COMMONPLACE_PASSWORD` and `SESSION_SECRET` have no defaults and are pulled from the `.env` file. Since the setup wizard handles first-run creation, none of these are strictly required.
