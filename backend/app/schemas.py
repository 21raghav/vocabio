"""Pydantic response models — the shape of what the API returns."""

from typing import Optional

from pydantic import BaseModel


class Word(BaseModel):
    """An enriched word: the term plus dictionary details."""

    word: str
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    definition: Optional[str] = None
    example: Optional[str] = None
    # True when we couldn't find the word in the dictionary API; the client can
    # still display the word itself but knows enrichment failed.
    enriched: bool = True


class NextWordResponse(BaseModel):
    """Result of asking for another word — may be empty if the list is exhausted."""

    word: Optional[Word] = None
    exhausted: bool = False


class WordRequest(BaseModel):
    """Body for adding a favorite / known word."""

    word: str


class WordList(BaseModel):
    """A page of words (favorites or known) plus the total count for paging."""

    words: list[str]
    total: int = 0


class HistoryItem(BaseModel):
    """The daily word for a given date."""

    date: str
    word: Word
