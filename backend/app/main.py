"""FastAPI application — routes for the word-of-the-day API."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import words
from .config import settings
from .db import Favorite, KnownWord, add_word, get_db, init_db, list_words, remove_word
from .schemas import NextWordResponse, Word, WordList, WordRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables on startup
    yield


app = FastAPI(title="Vocabio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/words/next", response_model=NextWordResponse)
async def next_word(
    exclude: str = Query(default=""), db: Session = Depends(get_db)
) -> NextWordResponse:
    """A fresh word, skipping today's word, the `exclude` list, and known words."""
    seen = {w.strip().lower() for w in exclude.split(",") if w.strip()}
    seen.add(words.word_for_date(date.today()))
    seen.update(list_words(db, KnownWord))  # never resurface mastered words

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


# --- Favorites ---

@app.get("/api/favorites", response_model=WordList)
def get_favorites(db: Session = Depends(get_db)) -> WordList:
    return WordList(words=list_words(db, Favorite))


@app.post("/api/favorites", response_model=WordList, status_code=201)
def add_favorite(req: WordRequest, db: Session = Depends(get_db)) -> WordList:
    add_word(db, Favorite, req.word.lower())
    return WordList(words=list_words(db, Favorite))


@app.delete("/api/favorites/{word}", response_model=WordList)
def delete_favorite(word: str, db: Session = Depends(get_db)) -> WordList:
    remove_word(db, Favorite, word.lower())
    return WordList(words=list_words(db, Favorite))


# --- Known words ("I know this") ---

@app.get("/api/known", response_model=WordList)
def get_known(db: Session = Depends(get_db)) -> WordList:
    return WordList(words=list_words(db, KnownWord))


@app.post("/api/known", response_model=WordList, status_code=201)
def add_known(req: WordRequest, db: Session = Depends(get_db)) -> WordList:
    add_word(db, KnownWord, req.word.lower())
    return WordList(words=list_words(db, KnownWord))


@app.delete("/api/known/{word}", response_model=WordList)
def delete_known(word: str, db: Session = Depends(get_db)) -> WordList:
    remove_word(db, KnownWord, word.lower())
    return WordList(words=list_words(db, KnownWord))
