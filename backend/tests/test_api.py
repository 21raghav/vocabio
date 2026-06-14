import os
import tempfile
from datetime import date

os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{tempfile.mkdtemp(prefix='vocabio-test-')}/test.db"
)

import pytest
from fastapi.testclient import TestClient

from app import words
from app.db import Favorite, KnownWord, SessionLocal, WordCache, init_db
from app.main import app
from app.schemas import Word


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    with SessionLocal() as db:
        for model in (Favorite, KnownWord, WordCache):
            db.query(model).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        for model in (Favorite, KnownWord, WordCache):
            db.query(model).delete()
        db.commit()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_word_for_date_is_stable_and_curated():
    target = date(2026, 6, 13)

    first = words.word_for_date(target)
    second = words.word_for_date(target)

    assert first == second
    assert first in words.WORDS


def test_pick_next_word_respects_exclusions():
    excluded = set(words.WORDS[:-1])

    assert words.pick_next_word(excluded) == words.WORDS[-1]
    assert words.pick_next_word(set(words.WORDS)) is None


def test_favorites_crud(client):
    assert client.get("/api/favorites").json() == {"words": []}

    created = client.post("/api/favorites", json={"word": "Reverie"})
    assert created.status_code == 201
    assert created.json() == {"words": ["reverie"]}

    duplicate = client.post("/api/favorites", json={"word": "reverie"})
    assert duplicate.status_code == 201
    assert duplicate.json() == {"words": ["reverie"]}

    deleted = client.delete("/api/favorites/reverie")
    assert deleted.status_code == 200
    assert deleted.json() == {"words": []}


def test_next_word_excludes_known_session_seen_and_today(client, monkeypatch):
    client.post("/api/known", json={"word": "abstruse"})
    captured = {}

    def fake_pick_next_word(exclude):
        captured["exclude"] = exclude
        return None

    monkeypatch.setattr(words, "pick_next_word", fake_pick_next_word)

    response = client.get("/api/words/next?exclude=reverie")

    assert response.status_code == 200
    assert response.json() == {"word": None, "exhausted": True}
    assert "reverie" in captured["exclude"]
    assert "abstruse" in captured["exclude"]
    assert words.word_for_date(date.today()) in captured["exclude"]


def test_lookup_returns_404_when_dictionary_cannot_enrich(client, monkeypatch):
    async def fake_enrich(word, db):
        return Word(word=word, enriched=False)

    monkeypatch.setattr(words, "enrich", fake_enrich)

    response = client.get("/api/words/not-a-real-entry")

    assert response.status_code == 404
