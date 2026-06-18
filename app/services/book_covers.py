"""Book cover lookup — bookcover-api (Goodreads source)."""

import os
import asyncio
from typing import Optional

import httpx

COVER_API = os.environ.get("BOOKCOVER_API_URL", "https://bookcover.longitood.com")


async def search_cover(title: str, author: str = "", client: httpx.AsyncClient = None) -> Optional[str]:
    """Search for a cover via bookcover-api (Goodreads scraped)."""
    params = {"book_title": title.strip()}
    if author:
        params["author_name"] = author.strip()

    _owns_client = client is None
    if _owns_client:
        client = httpx.AsyncClient(timeout=10.0)
    try:
        resp = await client.get(f"{COVER_API}/bookcover", params=params)
        if resp.status_code == 200:
            return resp.json().get("url")
        if resp.status_code in (400, 404):
            return None
        print(f"  [covers] bookcover-api returned {resp.status_code} for '{title}'")
        return None
    except Exception as e:
        print(f"  [covers] bookcover-api error for '{title}': {e}")
    finally:
        if _owns_client:
            await client.aclose()
    return None


async def batch_search(books: list[tuple[str, str]], rate_limit: float = 1.0, concurrency: int = 3) -> dict:
    results = {}
    sem = asyncio.Semaphore(concurrency)

    async def _fetch(client, title, author):
        async with sem:
            url = await search_cover(title, author, client=client)
            results[(title, author)] = url
            await asyncio.sleep(rate_limit)

    async with httpx.AsyncClient(timeout=10.0) as client:
        await asyncio.gather(*[_fetch(client, t, a) for t, a in books])
    return results
