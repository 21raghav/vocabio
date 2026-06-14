import { useEffect, useState } from "react";
import { getHistory, RateLimitError } from "../api.js";
import WordCard from "./WordCard.jsx";

// Browse the last N days of words via the backend's /api/history endpoint.
const DAYS = 7;

export default function HistoryList({ favorites, onToggleFavorite }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getHistory(DAYS)
      .then(setItems)
      .catch((e) =>
        setError(e instanceof RateLimitError ? e.message : "Couldn’t load history.")
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted view">Loading history…</p>;
  if (error) return <p className="muted view">{error}</p>;

  return (
    <div className="view">
      {items.map(({ date, word }) => (
        <div key={date}>
          <p className="date-label">{date}</p>
          <WordCard
            data={word}
            isFavorite={favorites.includes(word.word)}
            onToggleFavorite={onToggleFavorite}
          />
        </div>
      ))}
    </div>
  );
}
