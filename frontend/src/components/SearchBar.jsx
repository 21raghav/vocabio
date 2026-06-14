import { useState } from "react";
import { lookupWord, RateLimitError } from "../api.js";
import WordCard from "./WordCard.jsx";

export default function SearchBar({ favorites, onToggleFavorite }) {
  const [term, setTerm] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function search(e) {
    e.preventDefault();
    if (!term.trim()) return;
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      setResult(await lookupWord(term));
    } catch (err) {
      setError(
        err instanceof RateLimitError ? err.message : `No definition found for “${term}”.`
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="view">
      <form className="search" onSubmit={search}>
        <input
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Look up any word…"
          aria-label="Search for a word"
        />
        <button type="submit" disabled={loading}>
          {loading ? "…" : "Search"}
        </button>
      </form>

      {error && <p className="muted">{error}</p>}
      <WordCard
        data={result}
        isFavorite={result && favorites.includes(result.word)}
        onToggleFavorite={onToggleFavorite}
      />
    </div>
  );
}
