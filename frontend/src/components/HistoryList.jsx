import { useEffect, useState } from "react";
import { getWordOfDay } from "../api.js";
import WordCard from "./WordCard.jsx";

// Browse the last N days of words. Until the backend has a history endpoint
// (Phase 3) we simply ask for word-of-the-day on each past date.
const DAYS = 7;

export default function HistoryList({ favorites, onToggleFavorite }) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const dates = Array.from({ length: DAYS }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - i);
      return d.toISOString().slice(0, 10);
    });
    Promise.all(dates.map((iso) => getWordOfDay(iso).then((w) => ({ iso, w }))))
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  return (
    <div className="view">
      {items.map(({ iso, w }) => (
        <div key={iso}>
          <p className="date-label">{iso}</p>
          <WordCard
            data={w}
            isFavorite={favorites.includes(w.word)}
            onToggleFavorite={onToggleFavorite}
          />
        </div>
      ))}
    </div>
  );
}
