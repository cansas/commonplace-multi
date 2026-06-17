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
        return None

    search_query = title.strip()
    if author:
        search_query = f"{author.strip()} {title.strip()}"

    search_gql = """
    query SearchBook($query: String!) {
        search(query: $query, query_type: "Book", per_page: 3, page: 1) {
            results
        }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                HARDCOVER_API,
                json={"query": search_gql, "variables": {"query": search_query}},
                headers={"Authorization": HARDCOVER_KEY, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            search_data = data.get("data", {}).get("search", {})
            results_raw = search_data.get("results")
            if not results_raw:
                return None

            # Parse Typesense results
            import json as _json
            docs = _json.loads(results_raw) if isinstance(results_raw, str) else results_raw
            hits = docs.get("hits", []) if isinstance(docs, dict) else []
            if not hits:
                return None

            # Try to find a matching book and get its ID
            book_id = None
            for hit in hits:
                doc = hit.get("document", {})
                bid = doc.get("id")
                if bid:
                    book_id = bid
                    break

            if not book_id:
                return None

            # Second query: get the book with image URL
            book_gql = """
            query GetCover($id: Int!) {
                books(where: {id: {_eq: $id}}) {
                    id
                    title
                    image {
                        url
                    }
                }
            }
            """
            resp2 = await client.post(
                HARDCOVER_API,
                json={"query": book_gql, "variables": {"id": book_id}},
                headers={"Authorization": HARDCOVER_KEY, "Content-Type": "application/json"},
            )
            resp2.raise_for_status()
            data2 = resp2.json()
            books = data2.get("data", {}).get("books", [])
            if books:
                img = books[0].get("image")
                if img:
                    url = img.get("url") or img.get("secure_url")
                    if url:
                        return url
    except Exception as e:
        print(f"  [covers] Hardcover error for '{title}': {e}")
        import traceback
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
