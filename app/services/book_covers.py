"""Book cover lookup via Open Library API."""

import httpx
import asyncio
from typing import Optional

OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"
COVERS_BASE = "https://covers.openlibrary.org/b/id"


async def search_cover(title: str, author: str = "") -> Optional[str]:
    """Search Open Library for a book cover by title and optional author.
    Returns the cover URL (large) or None if not found.
    """
    query = title.strip()
    if author:
        query += f" {author.strip()}"

    params = {"q": query, "limit": 5, "fields": "key,cover_i,title,author_name"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_LIBRARY_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()

            docs = data.get("docs", [])
            for doc in docs:
                cover_i = doc.get("cover_i")
                if cover_i:
                    return f"{COVERS_BASE}/{cover_i}-L.jpg"
    except Exception as e:
        print(f"  [covers] Open Library search error for '{title}': {e}")

    return None


async def batch_search(books: list[tuple[str, str]], rate_limit: float = 1.0) -> dict:
    """Search covers for multiple books with rate limiting.
    Returns dict of (title, author) -> cover_url or None.
    """
    results = {}
    for title, author in books:
        url = await search_cover(title, author)
        results[(title, author)] = url
        await asyncio.sleep(rate_limit)  # Be nice to Open Library
    return results
