"""Parse KOReader JSON export files."""

import json
from typing import List, Dict
from datetime import datetime


def parse_koreader_json(data: dict) -> List[Dict]:
    """
    Parse KOReader JSON export format (single or multi-book).

    Single book format:
      { "title": "...", "author": "...", "entries": [{"text": "...", "page": 42, ...}] }

    Multi-book format:
      { "documents": [{ "title": "...", "entries": [...] }, ...] }
    """
    highlights = []

    # Handle multi-book export
    documents = data.get("documents", [])
    if documents:
        for doc in documents:
            highlights.extend(_parse_book(doc))
        return highlights

    # Handle single-book export
    if "entries" in data:
        highlights.extend(_parse_book(data))

    return highlights


def _parse_book(data: dict) -> List[Dict]:
    book_title = data.get("title", "Untitled")
    book_author = data.get("author", "")
    entries = data.get("entries", [])
    results = []

    for entry in entries:
        highlighted_at = None
        if entry.get("time"):
            try:
                highlighted_at = datetime.fromtimestamp(entry["time"])
            except (OSError, ValueError):
                pass
        if entry.get("datetime"):
            try:
                highlighted_at = datetime.fromisoformat(str(entry["datetime"]).replace("T", " "))
            except (ValueError, TypeError):
                pass

        results.append({
            "text": entry.get("text", ""),
            "note": entry.get("note"),
            "page": entry.get("page"),
            "chapter": entry.get("chapter"),
            "book_title": book_title,
            "book_author": book_author,
            "source_type": "koreader",
            "color": entry.get("color"),
            "highlighted_at": highlighted_at,
            "tags": [],
        })

    return results
