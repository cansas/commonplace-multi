from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class HighlightCreate(BaseModel):
    text: str
    note: Optional[str] = None
    page: Optional[int] = None
    chapter: Optional[str] = None
    source_type: str = "manual"
    source_id: Optional[str] = None
    book_title: str = "Untitled"
    book_author: Optional[str] = None
    book_url: Optional[str] = None
    category: Optional[str] = "books"
    color: Optional[str] = None
    highlighted_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


class HighlightOut(BaseModel):
    id: int
    text: str
    note: Optional[str] = None
    page: Optional[int] = None
    chapter: Optional[str] = None
    source_type: str
    book_title: str
    book_author: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    highlighted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    tags: List[str] = []
    favorite: int = 0

    class Config:
        from_attributes = True


class HighlightUpdate(BaseModel):
    text: Optional[str] = None
    note: Optional[str] = None
    page: Optional[int] = None
    chapter: Optional[str] = None
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    tags: Optional[List[str]] = None


class ReadwiseBatchImport(BaseModel):
    """Matches the Readwise API v2 format that KOReader uses."""
    highlights: List[HighlightCreate]


class ReviewRating(BaseModel):
    rating: int  # 0=forgot, 1=hard, 2=good, 3=easy


class DashboardStats(BaseModel):
    total_highlights: int
    total_books: int
    today_review_count: int
    total_sources: int
