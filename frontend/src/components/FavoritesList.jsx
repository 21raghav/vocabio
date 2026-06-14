import { useEffect, useState } from "react";
import { lookupWord, RateLimitError } from "../api.js";
import WordCard from "./WordCard.jsx";

// Re-enriches each saved word for display. The `favorites` word list is passed in
// from App (the backend is the source of truth, scoped to this device).
export default function FavoritesList({ favorites, onToggleFavorite }) {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    Promise.all(
      favorites.map((w) =>
        lookupWord(w).catch(() => ({ word: w, enriched: false }))
      )
    )
      .then(setCards)
      .catch((e) =>
        setError(e instanceof RateLimitError ? e.message : "Couldn’t load favorites.")
      )
      .finally(() => setLoading(false));
  }, [favorites]);

  if (loading && favorites.length) return <p className="muted view">Loading favorites…</p>;
  if (error) return <p className="muted view">{error}</p>;
  if (favorites.length === 0) {
    return <p className="muted view">No favorites yet — tap ☆ on a word to save it.</p>;
  }

  return (
    <div className="view">
      {cards.map((data) => (
        <WordCard
          key={data.word}
          data={data}
          isFavorite={true}
          onToggleFavorite={onToggleFavorite}
        />
      ))}
    </div>
  );
}
