"""Database layer: engine, session, ORM models, and small CRUD helpers.

One module for all persistence (the "flat over nested" rule). Split models/CRUD
into their own files only if this grows unwieldy.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, sessionmaker

from .config import settings

# SQLite needs check_same_thread off for FastAPI's threaded request handling;
# the flag is harmless/ignored for Postgres.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class WordCache(Base):
    """Cached dictionary enrichment so we don't re-hit the external API."""

    __tablename__ = "word_cache"
    word = mapped_column(String, primary_key=True)
    phonetic = mapped_column(String, nullable=True)
    part_of_speech = mapped_column(String, nullable=True)
    definition = mapped_column(Text, nullable=True)
    example = mapped_column(Text, nullable=True)
    enriched = mapped_column(String, default="1")  # "1"/"0" — sqlite-friendly bool
    fetched_at = mapped_column(DateTime, default=datetime.utcnow)


# Favorites/known are scoped per anonymous user: the client sends a stable random
# user id (X-User-Id header), so each browser sees only its own words. The composite
# primary key (user_id, word) keeps each user's set independent.
class Favorite(Base):
    __tablename__ = "favorite"
    user_id = mapped_column(String, primary_key=True)
    word = mapped_column(String, primary_key=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class KnownWord(Base):
    __tablename__ = "known_word"
    user_id = mapped_column(String, primary_key=True)
    word = mapped_column(String, primary_key=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- CRUD helpers (kept tiny; the routes stay thin). All scoped by user_id. ---

def list_words(db: Session, model, user_id: str, limit: int, offset: int) -> list[str]:
    """A page of the user's words, newest first."""
    rows = db.scalars(
        select(model)
        .where(model.user_id == user_id)
        .order_by(model.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [r.word for r in rows]


def count_words(db: Session, model, user_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    )


def all_words(db: Session, model, user_id: str) -> set[str]:
    """Every word for a user (used to exclude known words when picking next)."""
    return set(
        db.scalars(select(model.word).where(model.user_id == user_id)).all()
    )


def add_word(db: Session, model, user_id: str, word: str) -> None:
    if db.get(model, (user_id, word)) is None:
        db.add(model(user_id=user_id, word=word))
        db.commit()


def remove_word(db: Session, model, user_id: str, word: str) -> None:
    row = db.get(model, (user_id, word))
    if row is not None:
        db.delete(row)
        db.commit()
