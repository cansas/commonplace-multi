# Commonkore — KOReader → Commonplace Exporter

A KOReader plugin that sends your book highlights to your **Commonplace** server.

## Installation

1. Connect your KOReader device via USB
2. Copy the `commonkore.koplugin/` directory into KOReader's plugins folder:

   ```
   koreader/plugins/commonkore.koplugin/main.lua
   ```

3. Eject your device and open any book
4. Open the **Tools** menu (wrench icon) → **Export** → **Commonplace**
5. Set your **server URL** (e.g., `http://192.168.1.130:8765` or `https://commonplace.yourdomain.com`)
6. Set your **API token** (from Commonplace's Settings page)
7. Toggle **Export to Commonplace** on
8. Use the standard **Export** submenu to send highlights

> **Note:** The old installation method (dropping `commonkore.lua` into `exporter.koplugin/target/`) no longer works. KOReader's exporter plugin uses a hardcoded target list, not dynamic file scanning. The plugin registers itself via KOReader's Provider system instead.

## Usage

Same as the built-in Readwise exporter — export highlights for the current book or all books from the Export menu.

## Cloudflare Tunnel

If Commonplace is behind Cloudflare Access, add a **Bypass** policy for paths starting with `/api/` so KOReader can reach the API without browser authentication.

## How it works

Sends highlights to `{server_url}/api/v2/highlights` with `Authorization: Token {token}`, matching the Readwise API v2 format. Registers with KOReader's `Provider:register("exporter", ...)` system as a standalone plugin (no modification to the exporter plugin needed).
