"""Book cover lookup — Hardcover primary, Open Library fallback."""

import os
import asyncio
from typing import Optional

import httpx

HARDCOVER_API = "https://api.hardcover.app/v1/graphql"
HARDCOVER_KEY = os.environ.get("HARDCOVER_API_KEY", "")

OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"
COVERS_BASE = "https://covers.openlibrary.org/b/id"


async def _ol_search(title: str, author: str = "") -> Optional[str]:
    """Fallback: search Open Library for a cover."""
    query = title.strip()
    if author:
        query += f" {author.strip()}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                OPEN_LIBRARY_SEARCH,
                params={"q": query, "limit": 5, "fields": "key,cover_i,title,author_name"},
            )
            resp.raise_for_status()
            data = resp.json()
            for doc in data.get("docs", []):
                cover_i = doc.get("cover_i")
                if cover_i:
                    return f"{COVERS_BASE}/{cover_i}-L.jpg"
    except Exception:
        pass
    return None


async def _hc_search(title: str, author: str = "") -> Optional[str]:
    """Primary: search Hardcover by title/author for a cover."""
    if not HARDCOVER_KEY:
        return None  # No key configured, skip

    # Build search query — include author if we have it
    search_query = title.strip()
    if author:
        search_query = f"{author.strip()} {title.strip()}"

    query = """
    query SearchBook($query: String!) {
        search(query: $query, query_type: "Book", per_page: 5, page: 1) {
            results
        }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                HARDCOVER_API,
                json={"query": query, "variables": {"query": search_query}},
                headers={
                    "Authorization": HARDCOVER_KEY,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # The search returns Typesense results as a JSON string in `results`
            # Try to parse the first result's cover
            search_data = data.get("data", {}).get("search", {})
            results_raw = search_data.get("results")
            if results_raw:
                # results can be a JSON string or already parsed
                import json as _json
                if isinstance(results_raw, str):
                    docs = _json.loads(results_raw)
                else:
                    docs = results_raw

                if isinstance(docs, dict) and "hits" in docs:
                    for hit in docs.get("hits", []):
                        doc = hit.get("document", {})
                        # Try various cover fields Typesense may include
                        for key in ("cover_url", "image_url", "image", "cover"):
                            val = doc.get(key)
                            if val:
                                if isinstance(val, str):
                                    return val
                                if isinstance(val, dict):
                                    return val.get("url") or val.get("secure_url")
    except Exception as e:
        import traceback
        print(f"  [covers] Hardcover error for '{title}': {e}")
        traceback.print_exc()

    return None


async def search_cover(title: str, author: str = "") -> Optional[str]:
    """Try Hardcover first, then Open Library fallback."""
    url = await _hc_search(title, author)
    if url:
        return url
    return await _ol_search(title, author)


async def batch_search(books: list[tuple[str, str]], rate_limit: float = 1.0) -> dict:
    """Search covers for multiple books with rate limiting."""
    results = {}
    for title, author in books:
        url = await search_cover(title, author)
        results[(title, author)] = url
        await asyncio.sleep(rate_limit)
    return results
