// Thin wrapper around the backend API. All paths are relative so the Vite proxy
// (dev) or nginx (prod, Phase 4) routes them to FastAPI.

async function getJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const postJson = (url, body) =>
  getJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export function getWordOfDay(isoDate) {
  const q = isoDate ? `?on=${isoDate}` : "";
  return getJson(`/api/word-of-the-day${q}`);
}

export function getNextWord(exclude = []) {
  const q = exclude.length ? `?exclude=${encodeURIComponent(exclude.join(","))}` : "";
  return getJson(`/api/words/next${q}`);
}

export function lookupWord(word) {
  return getJson(`/api/words/${encodeURIComponent(word.trim().toLowerCase())}`);
}

// --- Favorites + known words (Phase 3: persisted in the backend DB). ---
// Each endpoint returns the full updated list, so callers just store the result.

export const getFavorites = () => getJson("/api/favorites").then((r) => r.words);
export const addFavorite = (word) => postJson("/api/favorites", { word }).then((r) => r.words);
export const removeFavorite = (word) =>
  getJson(`/api/favorites/${encodeURIComponent(word)}`, { method: "DELETE" }).then((r) => r.words);

export const getKnown = () => getJson("/api/known").then((r) => r.words);
export const addKnown = (word) => postJson("/api/known", { word }).then((r) => r.words);
