# Commonplace Sync — Obsidian Plugin

Sync highlights from your Commonplace server into your Obsidian vault.

## Installation

### From GitHub Release (recommended)

1. Download `commonplace-sync.zip` from the [latest release](https://github.com/cansas/commonplace/releases/latest)
2. Extract the zip into `<vault>/.obsidian/plugins/commonplace-sync/`
3. In Obsidian: **Settings → Community Plugins** → toggle on **Commonplace Sync**

### From Source

```bash
cd obsidian-plugin
npm install
npm run build
```
Then copy `main.js`, `manifest.json`, and `styles.css` to `<vault>/.obsidian/plugins/commonplace-sync/`.

## Configuration

1. Open Obsidian **Settings → Community Plugins → Commonplace Sync**
2. Set your **Server URL** (e.g. `https://commonplace.yourdomain.com` or `http://192.168.1.130:8765`)
3. Set your **API Token** (from Commonplace Settings page)
4. Choose an **Output Folder** (default: `Commonplace/`)

## Usage

- **Ribbon icon** (download arrow) — click to sync
- **Command palette** — "Sync highlights from Commonplace"
- **Settings page** — "Sync Now" button

## Output

Highlights are written as markdown files matching the Readwise format:

```markdown
# Book Title

## Metadata
- Author: [[Author Name]]
- Full Title: Book Title
- Category: #books

## Highlights
- Highlight text (p. 42)
    - Tags: [[tag1]] [[tag2]]
```

Incremental sync: only new highlights since your last sync are pulled. Use "Reset and Sync All" in settings to re-pull everything.
