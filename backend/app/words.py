"""Word selection + dictionary enrichment.

The curated list is loaded from words.json; fetched definitions are cached in the
`word_cache` table (see db.py) so we don't repeatedly hit the external API.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from .config import settings
from .db import WordCache
from .schemas import Word

# Load the curated word list once at import time.
_WORDS_FILE = Path(__file__).resolve().parent.parent / "words.json"
WORDS: list[str] = json.loads(_WORDS_FILE.read_text())

DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


def word_for_date(day: date) -> str:
    """Deterministically map a date to a word.

    The same date always yields the same word for everyone, with no database and
    no scheduler. We hash the ISO date string to an integer and take it modulo the
    list length. Hashing (rather than day-of-year) spreads consecutive days across
    the list so neighbouring days don't sit next to each other.
    """
    digest = hashlib.sha256(day.isoformat().encode()).hexdigest()
    index = int(digest, 16) % len(WORDS)
    return WORDS[index]


def pick_next_word(exclude: set[str]) -> str | None:
    """Pick a random word not in `exclude`. Returns None if all are excluded."""
    candidates = [w for w in WORDS if w not in exclude]
    if not candidates:
        return None
    return random.choice(candidates)


async def enrich(word: str, db: Session) -> Word:
    """Return an enriched Word, using the DB cache when it's still fresh.

    On a cache miss (or stale entry) we call the Free Dictionary API, parse out the
    first useful definition/example/phonetic, store it in `word_cache`, and return
    it. If the API has no entry, we return the bare word with enriched=False.
    """
    row = db.get(WordCache, word)
    if row is not None:
        age = (datetime.utcnow() - row.fetched_at).total_seconds()
        if age < settings.cache_ttl_seconds:
            return _row_to_word(row)

    result = await _fetch_definition(word)
    _save_cache(db, result)
    return result


def _row_to_word(row: WordCache) -> Word:
    return Word(
        word=row.word,
        phonetic=row.phonetic,
        part_of_speech=row.part_of_speech,
        definition=row.definition,
        example=row.example,
        enriched=row.enriched == "1",
    )


def _save_cache(db: Session, w: Word) -> None:
    row = db.get(WordCache, w.word)
    if row is None:
        row = WordCache(word=w.word)
        db.add(row)
    row.phonetic = w.phonetic
    row.part_of_speech = w.part_of_speech
    row.definition = w.definition
    row.example = w.example
    row.enriched = "1" if w.enriched else "0"
    row.fetched_at = datetime.utcnow()
    db.commit()


async def _fetch_definition(word: str) -> Word:
    # Encode the word so user-supplied characters can't alter the request URL.
    url = DICTIONARY_API.format(word=quote(word, safe=""))
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return Word(word=word, enriched=False)
        return _parse_definition(word, resp.json())
    except (httpx.HTTPError, ValueError):
        # Network error or bad JSON — degrade gracefully.
        return Word(word=word, enriched=False)


def _parse_definition(word: str, payload: list) -> Word:
    """Pull the first phonetic / part-of-speech / definition / example we find."""
    if not payload:
        return Word(word=word, enriched=False)
    entry = payload[0]
    phonetic = entry.get("phonetic") or _first_phonetic(entry)

    for meaning in entry.get("meanings", []):
        for definition in meaning.get("definitions", []):
            if definition.get("definition"):
                return Word(
                    word=word,
                    phonetic=phonetic,
                    part_of_speech=meaning.get("partOfSpeech"),
                    definition=definition.get("definition"),
                    example=definition.get("example"),
                )
    return Word(word=word, phonetic=phonetic, enriched=False)


def _first_phonetic(entry: dict) -> str | None:
    for p in entry.get("phonetics", []):
        if p.get("text"):
            return p["text"]
    return None
