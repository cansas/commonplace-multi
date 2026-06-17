"""Book cover lookup — bookcover-api (Goodreads source)."""

import os
import asyncio
from typing import Optional

import httpx

COVER_API = os.environ.get("BOOKCOVER_API_URL", "https://bookcover.longitood.com")


async def search_cover(title: str, author: str = "") -> Optional[str]:
    """Search for a cover via bookcover-api (Goodreads scraped)."""
    params = {"book_title": title.strip()}
    if author:
        params["author_name"] = author.strip()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{COVER_API}/bookcover", params=params)
            if resp.status_code == 200:
                return resp.json().get("url")
            if resp.status_code in (400, 404):
                return None
            print(f"  [covers] bookcover-api returned {resp.status_code} for '{title}'")
            return None
    except Exception as e:
        print(f"  [covers] bookcover-api error for '{title}': {e}")
    return None


async def batch_search(books: list[tuple[str, str]], rate_limit: float = 1.0) -> dict:
    results = {}
    for title, author in books:
        url = await search_cover(title, author)
        results[(title, author)] = url
        await asyncio.sleep(rate_limit)
    return results
