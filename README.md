# commonplace-multi

A multi-user fork of [Commonplace](https://github.com/cansas/commonplace) — the self-hosted Readwise alternative. Same app, now with isolated accounts for family or small teams.

- **Multi-user**: Admin invites users. No public signup. All data (highlights, reviews, tags, streaks, achievements, push subscriptions) partitioned by `user_id`.
- **All the same features**: Capture from KOReader/Kindle/Obsidian/Readwise, full-text search, daily review, achievements, themes, BookOrbit sync, push notifications, Obsidian sync plugin.
- **Self-hosted**: Single Docker container, SQLite database, no external services.

## Upgrading from Single-User Commonplace

If you already run the original Commonplace (single-user), switching to this fork is a one-time migration:

1. **Backup your data** — copy your volume's `data/` directory.
2. **Swap the image** — deploy `ghcr.io/cansas/commonplace-multi:latest` with the same mounted volume.
3. **Restart** — migration runs automatically on startup:
   - Adds `user_id` to all tables, sets existing data to `user_id=1`
   - Migrates per-user settings (theme, review count, hardcover key, push prefs) from `.settings.json` to the DB
   - Rebuilds FTS5 search index
4. **Your existing admin account** (user_id=1) keeps all data. Start inviting users at `/admin/users`.

No manual SQL, no config changes, no downtime beyond the container restart.

## Quick Start (Fresh Install)

```bash
docker run -d --name commonplace-multi -p 8765:8765 \
  -v ./data:/app/data \
  ghcr.io/cansas/commonplace-multi:latest
```

Open `http://localhost:8765` and the setup wizard creates the admin account. Then visit `/admin/users` to invite others.

## Documentation

| Document | Description |
|----------|-------------|
| [API.md](API.md) | Full API reference — all endpoints with auth, params, and examples |
| [ENV.md](ENV.md) | Environment variables reference |
| [INSTALL.md](INSTALL.md) | Server, KOReader plugin, and Obsidian plugin setup |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Bug reports, PR workflow, AI code policy |

## Features

- **Multi-user** — invite-only registration, admin user management, data fully isolated
- **Highlights** — add, edit, delete, search, filter by source/favorites/book
- **Books view** — browse by book with covers (HardCover.app + Open Library), rename/merge/delete
- **Book metadata** — set HardCover ID or ISBN for reliable cover lookups
- **Tag management** — create, rename, merge, delete tags with optional color coding
- **Import** — Readwise Obsidian .md, KOReader JSON, Kindle My Clippings, Readwise-compatible API
- **Export** — batch export all highlights as JSON
- **Backup & Restore** — ZIP download with database + covers, restore from ZIP
- **Share cards** — PNG/SVG share cards per highlight with OpenGraph meta tags
- **Themes** — Modern, Reader, Dark, plus custom themes — drop a `.css` file into `data/themes/` or upload via Settings
- **Streaks** — track daily review streaks with current and best counters
- **BookOrbit Sync** — auto-import annotations from BookOrbit (kobo, koreader, web) with SHA256 fingerprint dedup
- **Push notifications** — review reminders and streak-at-risk alerts via Web Push (VAPID)
- **First-run wizard** — web-based admin creation, no env vars required

## License

MIT No Attribution
