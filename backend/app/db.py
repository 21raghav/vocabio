"""Database layer: engine, session, ORM models, and small CRUD helpers.

One module for all persistence (the "flat over nested" rule). Split models/CRUD
into their own files only if this grows unwieldy.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, create_engine, select
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


class Favorite(Base):
    __tablename__ = "favorite"
    word = mapped_column(String, primary_key=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class KnownWord(Base):
    __tablename__ = "known_word"
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


# --- CRUD helpers (kept tiny; the routes stay thin) ---

def list_words(db: Session, model) -> list[str]:
    """Words from a Favorite/KnownWord table, newest first."""
    rows = db.scalars(select(model).order_by(model.created_at.desc())).all()
    return [r.word for r in rows]


def add_word(db: Session, model, word: str) -> None:
    if db.get(model, word) is None:
        db.add(model(word=word))
        db.commit()


def remove_word(db: Session, model, word: str) -> None:
    row = db.get(model, word)
    if row is not None:
        db.delete(row)
        db.commit()
