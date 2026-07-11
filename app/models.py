from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Table, Boolean, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

# Many-to-many: highlight <-> tag
highlight_tags = Table(
    "highlight_tags",
    Base.metadata,
    Column("highlight_id", Integer, ForeignKey("highlights.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    page = Column(Integer, nullable=True)
    chapter = Column(String(255), nullable=True)
    source_type = Column(String(64), nullable=False, default="manual")  # koreader, readwise, manual, kindle
    source_id = Column(String(255), nullable=True)
    book_title = Column(String(511), nullable=False, default="Untitled")
    book_author = Column(String(511), nullable=True)
    book_url = Column(String(2047), nullable=True)
    category = Column(String(64), nullable=True, default="books")
    color = Column(String(32), nullable=True)
    highlighted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    favorite = Column(Integer, default=0)  # 0=no, 1=favorite
    share_token = Column(String(64), unique=True, nullable=True)
    fingerprint = Column(String(64), nullable=True, index=True)  # SHA256 dedup hash

    user = relationship("User", foreign_keys=[user_id])
    tags = relationship("Tag", secondary=highlight_tags, lazy="subquery")
    reviews = relationship("ReviewLog", back_populates="highlight", lazy="subquery")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(128), nullable=False)
    color = Column(String(7), nullable=True)  # hex color like #3b82f6

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tag_per_user"),
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(64), nullable=False)
    last_import_at = Column(DateTime, nullable=True)
    last_hash = Column(String(128), nullable=True)
    highlights_imported = Column(Integer, default=0)

    user = relationship("User", foreign_keys=[user_id])


class ReviewLog(Base):
    __tablename__ = "review_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    highlight_id = Column(Integer, ForeignKey("highlights.id"), nullable=False)
    reviewed_at = Column(DateTime, default=datetime.utcnow)
    rating = Column(Integer, nullable=True)  # deprecated — always None after SM-2 removal
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=0)  # days
    repetitions = Column(Integer, default=0)
    next_review_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    highlight = relationship("Highlight", back_populates="reviews")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")


class Invite(Base):
    """One-time invite token for new user registration."""
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_key = Column(String(64), nullable=False)
    message = Column(String(255), nullable=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_key", name="uq_user_achievement"),
    )


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(128), nullable=False)  # e.g. "koreader", "obsidian-plugin"
    token_hash = Column(String(255), nullable=False)  # SHA256 of the token secret
    token_prefix = Column(String(16), nullable=False)  # first chars for display
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tokens")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(512), nullable=False, unique=True)
    p256dh_key = Column(String(256), nullable=False)
    auth_key = Column(String(256), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class DailyReviewQueue(Base):
    __tablename__ = "daily_review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    highlight_id = Column(Integer, ForeignKey("highlights.id"), nullable=False)
    queue_date = Column(Date, nullable=False)
    position = Column(Integer, nullable=False)
    reviewed = Column(Boolean, default=False)

    user = relationship("User", foreign_keys=[user_id])
    highlight = relationship("Highlight")

    __table_args__ = (
        UniqueConstraint("user_id", "queue_date", "position", name="uq_queue_user_date_position"),
    )


class UserSetting(Base):
    """Per-user key-value settings store — replaces file-backed .settings.json for user-scoped settings."""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_setting"),
    )


class BookCover(Base):
    __tablename__ = "book_covers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_title = Column(String(511), nullable=False)
    book_author = Column(String(511), nullable=False, default="")
    cover_source = Column(String(16), nullable=False, default="none")
    cover_url = Column(String(1024), nullable=True)
    hardcover_id = Column(Integer, nullable=True)
    isbn = Column(String(20), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "book_title", "book_author", name="uq_cover_per_user"),
    )
