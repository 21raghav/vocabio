// Thin wrapper around the backend API. All paths are relative so the Vite proxy
// (dev) or nginx (prod) routes them to FastAPI.

// Anonymous per-device identity: generate a random id once, persist it, and send
// it on every request so the backend can scope favorites/known words to this
// browser. No login required.
function userId() {
  let id = localStorage.getItem("vocabio:user-id");
  if (!id) {
    id = (crypto.randomUUID?.() || String(Date.now() + Math.random()));
    localStorage.setItem("vocabio:user-id", id);
  }
  return id;
}

// Raised on HTTP 429 so the UI can show a friendly "slow down" message.
export class RateLimitError extends Error {}

async function request(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { "X-User-Id": userId(), ...(options.headers || {}) },
  });
  if (res.status === 429) {
    throw new RateLimitError("Too many requests — please slow down a moment.");
  }
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const postJson = (url, body) =>
  request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export function getWordOfDay(isoDate) {
  const q = isoDate ? `?on=${isoDate}` : "";
  return request(`/api/word-of-the-day${q}`);
}

export function getNextWord(exclude = []) {
  const q = exclude.length ? `?exclude=${encodeURIComponent(exclude.join(","))}` : "";
  return request(`/api/words/next${q}`);
}

export function lookupWord(word) {
  return request(`/api/words/${encodeURIComponent(word.trim().toLowerCase())}`);
}

export function getHistory(days = 7) {
  return request(`/api/history?days=${days}`); // [{ date, word }]
}

// --- Favorites + known words (persisted per-user in the backend DB). ---
// Each endpoint returns { words, total }; callers use both for paging.

export const getFavorites = (limit = 100, offset = 0) =>
  request(`/api/favorites?limit=${limit}&offset=${offset}`);
export const addFavorite = (word) => postJson("/api/favorites", { word });
export const removeFavorite = (word) =>
  request(`/api/favorites/${encodeURIComponent(word)}`, { method: "DELETE" });

export const getKnown = (limit = 100, offset = 0) =>
  request(`/api/known?limit=${limit}&offset=${offset}`);
export const addKnown = (word) => postJson("/api/known", { word });
