import { useEffect, useState } from "react";
import {
  getWordOfDay,
  getNextWord,
  getFavorites,
  addFavorite,
  removeFavorite,
  addKnown,
  RateLimitError,
} from "./api.js";
import WordCard from "./components/WordCard.jsx";
import SearchBar from "./components/SearchBar.jsx";
import HistoryList from "./components/HistoryList.jsx";
import FavoritesList from "./components/FavoritesList.jsx";

const TABS = ["Today", "History", "Favorites", "Search"];

// Turn any thrown error into a user-facing message (429 gets its own).
const message = (err) =>
  err instanceof RateLimitError ? err.message : "Something went wrong. Please try again.";

export default function App() {
  const [tab, setTab] = useState("Today");
  const [current, setCurrent] = useState(null); // word currently on the card
  const [seen, setSeen] = useState([]); // words shown this session (for exclude)
  const [exhausted, setExhausted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true); // initial word-of-day load
  const [error, setError] = useState(null);

  // favorites (just the word list) kept in React state; the backend is the source.
  const [favorites, setFavorites] = useState([]);

  // Load today's word + the saved favorites on first render.
  useEffect(() => {
    getWordOfDay()
      .then((w) => {
        setCurrent(w);
        setSeen([w.word]);
      })
      .catch((e) => setError(message(e)))
      .finally(() => setLoading(false));
    getFavorites()
      .then((r) => setFavorites(r.words))
      .catch(() => setFavorites([]));
  }, []);

  async function toggleFavorite(word) {
    try {
      const res = favorites.includes(word)
        ? await removeFavorite(word)
        : await addFavorite(word);
      setFavorites(res.words);
    } catch (e) {
      setError(message(e));
    }
  }

  // Fetch a different word, excluding everything seen this session.
  async function another() {
    setBusy(true);
    setError(null);
    try {
      const res = await getNextWord(seen);
      if (res.exhausted) {
        setExhausted(true);
      } else {
        setCurrent(res.word);
        setSeen((s) => [...s, res.word.word]);
      }
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  // "I know this": record it in the backend (so it never resurfaces), then advance.
  async function knowThis(word) {
    try {
      await addKnown(word);
    } catch (e) {
      setError(message(e));
      return;
    }
    await another();
  }

  function renderToday() {
    if (loading) return <p className="muted view">Loading today’s word…</p>;
    if (error && !current)
      return <p className="muted view">{error}</p>;
    if (exhausted)
      return <p className="muted view">You’ve seen every word — come back tomorrow! 🎉</p>;
    return (
      <div className="view">
        <WordCard
          data={current}
          isFavorite={current && favorites.includes(current.word)}
          onToggleFavorite={toggleFavorite}
          onAnother={another}
          onKnowThis={knowThis}
          busy={busy}
        />
        {error && <p className="muted">{error}</p>}
      </div>
    );
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
        {tab === "Today" && renderToday()}
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
