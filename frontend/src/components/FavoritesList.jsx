import { useEffect, useState } from "react";
import { lookupWord } from "../api.js";
import WordCard from "./WordCard.jsx";

// Re-enriches each saved word for display. Favorites live in localStorage in
// Phase 2; the list of words is passed in from App.
export default function FavoritesList({ favorites, onToggleFavorite }) {
  const [cards, setCards] = useState([]);

  useEffect(() => {
    Promise.all(favorites.map((w) => lookupWord(w).catch(() => ({ word: w, enriched: false }))))
      .then(setCards)
      .catch(() => setCards([]));
  }, [favorites]);

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
