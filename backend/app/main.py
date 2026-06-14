"""FastAPI application — routes for the word-of-the-day API."""

from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from . import words
from .config import settings
from .db import (
    Favorite,
    KnownWord,
    add_word,
    all_words,
    count_words,
    get_db,
    init_db,
    list_words,
    remove_word,
)
from .schemas import HistoryItem, NextWordResponse, Word, WordList, WordRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables on startup
    yield


app = FastAPI(title="Vocabio API", lifespan=lifespan)

def client_ip(request: Request) -> str:
    """Real client IP for rate limiting.

    The app sits behind Caddy → nginx, so request.client.host is an internal proxy
    address. The proxies set X-Forwarded-For with the original client first, so we
    key on that to rate-limit per visitor rather than globally. (XFF is spoofable in
    principle, but the proxies overwrite it for direct clients — fine for this demo.)
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Light per-IP rate limit — caps abuse (e.g. flooding /api/words/{word}, which each
# insert a cache row).
limiter = Limiter(key_func=client_ip, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user(x_user_id: str = Header(default="anonymous")) -> str:
    """Anonymous per-device identity from the X-User-Id header.

    The frontend generates a random id once and stores it locally, so each browser
    gets its own favorites/known set. Missing header falls back to a shared
    'anonymous' bucket (e.g. for curl/health checks).
    """
    return (x_user_id or "anonymous").strip()[:64]


def _page(db: Session, model, user_id: str, limit: int, offset: int) -> WordList:
    return WordList(
        words=list_words(db, model, user_id, limit, offset),
        total=count_words(db, model, user_id),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/word-of-the-day", response_model=Word)
async def word_of_the_day(
    on: Optional[date] = Query(default=None), db: Session = Depends(get_db)
) -> Word:
    """Today's word (or the word for a given date via ?on=YYYY-MM-DD)."""
    target = on or date.today()
    return await words.enrich(words.word_for_date(target), db)


@app.get("/api/history", response_model=list[HistoryItem])
async def history(
    days: int = Query(default=7, ge=1, le=30), db: Session = Depends(get_db)
) -> list[HistoryItem]:
    """The daily words for the last `days` days (most recent first)."""
    today = date.today()
    items = []
    for i in range(days):
        d = today - timedelta(days=i)
        enriched = await words.enrich(words.word_for_date(d), db)
        items.append(HistoryItem(date=d.isoformat(), word=enriched))
    return items


@app.get("/api/words/next", response_model=NextWordResponse)
async def next_word(
    exclude: str = Query(default=""),
    db: Session = Depends(get_db),
    user_id: str = Depends(current_user),
) -> NextWordResponse:
    """A fresh word, skipping today's word, the `exclude` list, and the user's known words."""
    seen = {w.strip().lower() for w in exclude.split(",") if w.strip()}
    seen.add(words.word_for_date(date.today()))
    seen.update(all_words(db, KnownWord, user_id))  # never resurface mastered words

    chosen = words.pick_next_word(seen)
    if chosen is None:
        return NextWordResponse(exhausted=True)
    return NextWordResponse(word=await words.enrich(chosen, db))


@app.get("/api/words/{word}", response_model=Word)
async def lookup(word: str, db: Session = Depends(get_db)) -> Word:
    """Look up any word's definition on demand (search)."""
    result = await words.enrich(word.lower(), db)
    if not result.enriched:
        raise HTTPException(status_code=404, detail=f"No definition found for '{word}'.")
    return result


# --- Favorites (scoped per user, paginated) ---

@app.get("/api/favorites", response_model=WordList)
def get_favorites(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: str = Depends(current_user),
) -> WordList:
    return _page(db, Favorite, user_id, limit, offset)


@app.post("/api/favorites", response_model=WordList, status_code=201)
def add_favorite(
    req: WordRequest, db: Session = Depends(get_db), user_id: str = Depends(current_user)
) -> WordList:
    add_word(db, Favorite, user_id, req.word.lower())
    return _page(db, Favorite, user_id, 100, 0)


@app.delete("/api/favorites/{word}", response_model=WordList)
def delete_favorite(
    word: str, db: Session = Depends(get_db), user_id: str = Depends(current_user)
) -> WordList:
    remove_word(db, Favorite, user_id, word.lower())
    return _page(db, Favorite, user_id, 100, 0)


# --- Known words ("I know this") (scoped per user, paginated) ---

@app.get("/api/known", response_model=WordList)
def get_known(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: str = Depends(current_user),
) -> WordList:
    return _page(db, KnownWord, user_id, limit, offset)


@app.post("/api/known", response_model=WordList, status_code=201)
def add_known(
    req: WordRequest, db: Session = Depends(get_db), user_id: str = Depends(current_user)
) -> WordList:
    add_word(db, KnownWord, user_id, req.word.lower())
    return _page(db, KnownWord, user_id, 100, 0)


@app.delete("/api/known/{word}", response_model=WordList)
def delete_known(
    word: str, db: Session = Depends(get_db), user_id: str = Depends(current_user)
) -> WordList:
    remove_word(db, KnownWord, user_id, word.lower())
    return _page(db, KnownWord, user_id, 100, 0)
