import { useEffect, useState } from "react";
import {
  getWordOfDay,
  getNextWord,
  getFavorites,
  addFavorite,
  removeFavorite,
  addKnown,
} from "./api.js";
import WordCard from "./components/WordCard.jsx";
import SearchBar from "./components/SearchBar.jsx";
import HistoryList from "./components/HistoryList.jsx";
import FavoritesList from "./components/FavoritesList.jsx";

const TABS = ["Today", "History", "Favorites", "Search"];

export default function App() {
  const [tab, setTab] = useState("Today");
  const [current, setCurrent] = useState(null); // word currently on the card
  const [seen, setSeen] = useState([]); // words shown this session (for exclude)
  const [exhausted, setExhausted] = useState(false);
  const [busy, setBusy] = useState(false);

  // favorites kept in React state so the UI re-renders; the backend is the source.
  const [favorites, setFavorites] = useState([]);

  // Load today's word + the saved favorites on first render.
  useEffect(() => {
    getWordOfDay()
      .then((w) => {
        setCurrent(w);
        setSeen([w.word]);
      })
      .catch(() => setCurrent(null));
    getFavorites().then(setFavorites).catch(() => setFavorites([]));
  }, []);

  async function toggleFavorite(word) {
    const updated = favorites.includes(word)
      ? await removeFavorite(word)
      : await addFavorite(word);
    setFavorites(updated);
  }

  // Fetch a different word, excluding everything seen this session.
  async function another() {
    setBusy(true);
    try {
      const res = await getNextWord(seen);
      if (res.exhausted) {
        setExhausted(true);
      } else {
        setCurrent(res.word);
        setSeen((s) => [...s, res.word.word]);
      }
    } finally {
      setBusy(false);
    }
  }

  // "I know this": record it in the backend (so it never resurfaces), then advance.
  async function knowThis(word) {
    await addKnown(word);
    await another();
  }

  return (
    <div className="app">
      <header className="masthead">
        <h1>Vocabio</h1>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {tab === "Today" &&
          (exhausted ? (
            <p className="muted view">You’ve seen every word — come back tomorrow! 🎉</p>
          ) : (
            <div className="view">
              <WordCard
                data={current}
                isFavorite={current && favorites.includes(current.word)}
                onToggleFavorite={toggleFavorite}
                onAnother={another}
                onKnowThis={knowThis}
                busy={busy}
              />
            </div>
          ))}

        {tab === "History" && (
          <HistoryList favorites={favorites} onToggleFavorite={toggleFavorite} />
        )}
        {tab === "Favorites" && (
          <FavoritesList favorites={favorites} onToggleFavorite={toggleFavorite} />
        )}
        {tab === "Search" && (
          <SearchBar favorites={favorites} onToggleFavorite={toggleFavorite} />
        )}
      </main>
    </div>
  );
}
