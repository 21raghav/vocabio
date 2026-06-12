# Vocabio — Build Progress Report

## Phase 0 — Project Setup ✅
- Created the repo skeleton and `.gitignore` (ignores `.venv`, `__pycache__`,
  `.env`, `node_modules`, build output, OS/editor files).

## Phase 1 — Backend Core ✅
A working FastAPI backend that serves an enriched word of the day, a "next word"
for the keep-going flow, and on-demand word lookup. **No database yet** (Phase 3) —
the curated list is a JSON file and definitions are cached in memory.

### Files created
| File | Purpose |
|---|---|
| `backend/requirements.txt` | Dependencies: FastAPI, uvicorn, httpx, pydantic. |
| `backend/words.json` | Curated list of ~64 interesting words. |
| `backend/.env.example` | Configurable CORS origins + cache TTL. |
| `backend/app/config.py` | Loads settings from env / `.env`. |
| `backend/app/schemas.py` | Pydantic response shapes (`Word`, `NextWordResponse`). |
| `backend/app/words.py` | The core logic: word selection + dictionary enrichment. |
| `backend/app/main.py` | FastAPI app + the four routes. |

### Endpoints (all verified working)
| Endpoint | What it returns |
|---|---|
| `GET /health` | `{"status":"ok"}` — for Docker healthchecks later. |
| `GET /api/word-of-the-day` | Today's enriched word. `?on=YYYY-MM-DD` for any date. |
| `GET /api/words/next?exclude=a,b` | A fresh random word, skipping today's + the exclude list. |
| `GET /api/words/{word}` | On-demand lookup (search); 404 if no definition. |

---

## The Logic — Explained

### 1. Deterministic "word of the day"
The same date must give the same word for everyone, with **no database and no
scheduler**. The trick:

```
digest = sha256("2026-06-11")        # hash the ISO date string
index  = int(digest, 16) % len(WORDS)  # map the huge number into list range
word   = WORDS[index]
```

- **Why hash instead of, say, day-of-year?** A hash scatters consecutive dates all
  over the list, so yesterday and today aren't neighbours in `words.json`. It also
  means reordering the list doesn't shift every future word predictably.
- **Stateless:** any server, any time, computes the same answer — no storage needed.

### 2. "Next word" / "I know this" selection
`pick_next_word(exclude)` filters the list down to words **not** in an exclude set,
then picks one at random.

- The route always adds **today's word** to the exclude set (so "Show me another"
  never just repeats the daily word).
- The client sends words it has **already seen this session** via `?exclude=`.
- If everything is excluded, the API returns `{"exhausted": true}` instead of erroring
  — the UI can then show a "you've seen them all" message.
- In **Phase 3**, the user's *known* words (from the DB) get added to the exclude set
  too, so mastered words stop reappearing.

### 3. Dictionary enrichment with a cache
A raw word like `"reverie"` isn't useful on its own — we need its definition,
phonetic spelling, and part of speech. `enrich(word)` does this:

```
if word is in cache and not stale  ->  return cached result
otherwise                          ->  call Free Dictionary API,
                                        parse it, cache it, return it
```

- **Why cache?** The dictionary is an external HTTP call (slow, rate-limited). The
  same word of the day is requested by every visitor all day, so we fetch once and
  reuse. TTL is configurable (default 24h).
- **Graceful failure:** if the API is down or has no entry, we return the bare word
  with `enriched: false` rather than crashing — the site still shows *something*.
- **Phase 1 cache is in-memory** (a dict). Phase 3 swaps it for the `word_cache`
  table so it survives restarts and is shared across instances.

### 4. Why the code is split this way
- `config.py` — all tunables in one place, env-driven (12-factor friendly).
- `schemas.py` — the API's public contract, separate from logic.
- `words.py` — pure domain logic (selection + enrichment); easy to unit-test.
- `main.py` — thin HTTP layer that just wires routes to `words.py`.

This keeps the HTTP layer dumb and the logic testable — and matches the "flat over
nested" principle in the plan (no `services/` or `routers/` folders yet; we add them
only when a file actually outgrows itself).

---

## How to run it
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
# then visit http://localhost:8000/docs for the interactive API explorer
```

## A note from the build
- The dev machine runs **Python 3.9**, which doesn't support the newer `str | None`
  union syntax at runtime (pydantic/FastAPI evaluate annotations). Switched those to
  `Optional[str]` from `typing`. Worth knowing if we set a different Python in Docker
  later (3.11+ would allow the `|` syntax).

## Phase 2 — Frontend ✅
A React + Vite single-page app, wired to the backend through a dev proxy. Builds
clean and the proxy was verified serving real data from FastAPI.

### Files created
| File | Purpose |
|---|---|
| `frontend/package.json` | React 18 + Vite 6 deps and scripts. |
| `frontend/vite.config.js` | Dev server + proxy: `/api` and `/health` → `localhost:8000`. |
| `frontend/index.html` | App shell with the `#root` mount point. |
| `frontend/src/main.jsx` | React entry — mounts `<App/>`. |
| `frontend/src/api.js` | Fetch wrapper + localStorage helpers. |
| `frontend/src/App.jsx` | Top-level state, tabs, and the keep-going logic. |
| `frontend/src/components/WordCard.jsx` | One reusable word card (definition + actions). |
| `frontend/src/components/SearchBar.jsx` | On-demand word lookup. |
| `frontend/src/components/HistoryList.jsx` | Last 7 days of words. |
| `frontend/src/components/FavoritesList.jsx` | Saved words, re-enriched for display. |
| `frontend/src/styles.css` | One stylesheet (dark theme). |

### Four tabs
**Today** (word of the day + "Show me another" / "I know this"), **History**,
**Favorites**, **Search**.

---

## Phase 2 Logic — Explained

### 1. The Vite proxy (why there's no CORS pain in dev)
The frontend runs on `:5173`, the backend on `:8000` — different origins. Rather
than fight CORS in the browser, `vite.config.js` proxies any `/api/*` request from
`:5173` to the backend. So `api.js` only ever uses **relative paths** (`/api/...`).
In Phase 4 nginx will do the same job in production — same relative paths, no code
change.

### 2. The "keep going" state machine (`App.jsx`)
The core of the "I know this" feature lives in three pieces of state:
- `current` — the word on the card right now.
- `seen` — every word shown **this session**, seeded with today's word.
- `exhausted` — true once the backend runs out of unseen words.

Flow:
```
Show me another  ->  getNextWord(seen)  ->  set current, append to seen
I know this      ->  save word to KNOWN (localStorage)  ->  then "another"
```
We pass `seen` to the backend as the `exclude` list, so the same word never repeats
within a session. When the backend replies `exhausted: true`, the Today tab swaps to
a "come back tomorrow" message. **In Phase 3**, "I know this" will POST to the
backend instead of localStorage, and known words will be excluded server-side too.

### 3. Favorites: localStorage now, DB later
`api.js` has a tiny `store` helper (`add/remove/has/list`) over `localStorage`.
Favorites are mirrored into React state so the ★ updates instantly. Keeping the read
path in one place means Phase 3 only has to swap `store.*` calls for API calls — the
components don't change.

### 4. History without a history endpoint (yet)
The backend's daily word is **deterministic by date**, so the frontend can
reconstruct history by simply asking `word-of-the-day?on=<past date>` for the last 7
days. No backend work needed for a usable history view now; Phase 3 can add a real
`/api/history` endpoint if we want server-side records.

### 5. One reusable `WordCard`
The action buttons (`onAnother`, `onKnowThis`, `onToggleFavorite`) are **optional
props**. The Today tab passes all of them; History/Favorites/Search pass only the
favorite toggle. One component, four contexts — no duplication.

---

## How to run the full app (dev)
```bash
# terminal 1 — backend
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd frontend && npm install && npm run dev
# open http://localhost:5173
```

## Phase 3 — Persistence (Database) ✅
Added a database layer with SQLAlchemy. Dictionary cache, favorites, and known
words now live in the DB. Verified end-to-end through the Vite proxy, and that data
survives a backend restart.

### Key decision: SQLite local, Postgres in Docker
`database_url` is configurable (`config.py`). It defaults to **SQLite**
(`sqlite:///./vocabio.db`) so the app runs locally with zero setup, and Phase 4's
Docker compose will point it at **Postgres** via an env var. SQLAlchemy abstracts
the difference, so **no code changes** are needed to switch — only configuration.

### Files created / changed
| File | Change |
|---|---|
| `backend/app/db.py` | **New** — engine, session, ORM models, CRUD helpers. |
| `backend/app/words.py` | `enrich()` now reads/writes the `word_cache` table instead of an in-memory dict. |
| `backend/app/main.py` | DB dependency + favorites/known routes; `next` excludes known words. |
| `backend/app/schemas.py` | Added `WordRequest` and `WordList`. |
| `backend/app/config.py` | Added `database_url`. |
| `backend/requirements.txt` | Added `sqlalchemy`, `psycopg2-binary`. |
| `frontend/src/api.js` | Swapped the localStorage `store` for favorites/known API calls. |
| `frontend/src/App.jsx` | Loads favorites from the backend; "I know this" POSTs to `/api/known`. |

### New endpoints (all verified)
| Endpoint | Behaviour |
|---|---|
| `GET/POST /api/favorites`, `DELETE /api/favorites/{word}` | Manage favorites; each returns the full updated list. |
| `GET/POST /api/known`, `DELETE /api/known/{word}` | Manage known words. |
| `GET /api/words/next` | Now also excludes words in the `known_word` table. |

---

## Phase 3 Logic — Explained

### 1. Three tables, one module (`db.py`)
- `word_cache` — cached dictionary results (`fetched_at` drives the TTL).
- `favorite` — saved words.
- `known_word` — words the user marked "I know this".

Everything persistence-related — engine, session, models, and tiny CRUD helpers
(`list_words` / `add_word` / `remove_word`) — lives in one file, per the "flat over
nested" rule. The CRUD helpers take a `model` argument so favorites and known words
share the **same three functions** instead of duplicating six.

### 2. The cache moved from RAM to the DB
Phase 1 cached definitions in a Python dict (lost on restart, not shared between
processes). Now `enrich(word, db)`:
```
look up word_cache row
  fresh?  -> return it (no external call)
  stale/missing -> fetch from Free Dictionary API, upsert the row, return it
```
This survives restarts and, once there are multiple backend containers (Phase 4+),
is shared across them.

### 3. "I know this" is now server-side
Before, known words sat in the browser's localStorage — so the backend's "next
word" couldn't honour them. Now `POST /api/known` records the word, and
`/api/words/next` adds all known words to its exclude set. The exclusion is enforced
where the selection actually happens, so it's consistent no matter which client asks.

### 4. Why endpoints return the whole list
`POST /api/favorites` returns the **full updated favorites list**, not just an OK.
The frontend then does `setFavorites(updated)` with no second request and no guessing
about local state — the server is always the single source of truth.

### 5. Request flow, end to end
```
Browser  ──► Vite proxy (dev) / nginx (prod)  ──►  FastAPI route
                                                     │ Depends(get_db) → Session
                                                     ▼
                                                 words.py / db.py  ──►  DB
                                                     │
                                          (cache miss) ──► Free Dictionary API
```

---

## Dev convenience — `dev.sh`
A root script that starts both servers together (backend with `--reload` on :8000,
frontend on :5173) and stops both on Ctrl-C. Run `./dev.sh` from the project root —
no need to activate the venv or juggle two terminals.

---

## Security Review (pre-commit) ✅
Ran before the first commit. Codebase is safe to commit to a **private** repo.

### Fixed
- **Unencoded user input in an outbound URL** — `/api/words/{word}` passed the raw
  word into the dictionary API URL. Now URL-encoded with `quote(...)`
  (`words.py`), so special characters can't alter the request.
- **`IndexError` → 500 on empty API response** — `_parse_definition` now guards an
  empty payload and returns `enriched=False` instead of crashing.

### Verified clean
- No secrets / API keys in source; `.env` and `*.db` are gitignored.
- SQLAlchemy ORM with parameterized queries — no SQL injection.
- CORS restricted to configured origins (not `*`).

### Deferred — MUST address before the public AWS deploy (Phase 5)
- **No auth + global data**: favorites/known words are shared and writable by
  anyone. Fine for single-user local use; needs auth or per-user scoping before
  going public.
- **No rate limiting**: each `/api/words/{x}` lookup inserts a `word_cache` row, so
  arbitrary lookups allow unbounded DB growth (mild DoS). Add a rate limit or only
  cache curated words before exposing publicly.

---

## Next up — Phase 4 (Dockerize)
Write a Dockerfile for the backend and a multi-stage one for the frontend (build →
nginx), plus `docker-compose.yml` wiring **frontend + backend + Postgres** so the
whole app runs with one `docker-compose up`. This is where `database_url` flips from
SQLite to Postgres.
