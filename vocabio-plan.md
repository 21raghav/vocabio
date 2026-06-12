# Vocabio — Word of the Day Website

A full-stack "Word of the Day" web application, built as a portfolio project to
demonstrate full-stack development plus Docker and AWS deployment skills.

---

## 1. Goals

- Ship a real, useful Word-of-the-Day site (definition, pronunciation, example).
- Use the project as a **learning/portfolio vehicle** for Docker and AWS — areas
  to strengthen for Canadian bank SWE/ML/Data roles.
- Keep the architecture realistic (frontend + backend + database + containers +
  cloud) without over-engineering.

> Note: Technically a static site would suffice for the app itself. The backend,
> database, Docker, and AWS layers are deliberately included for portfolio depth.

---

## 2. Final Stack Decisions

| Layer | Choice | Why |
|---|---|---|
| Frontend | **React + Vite** | Component reuse for history/favorites/search; fast dev. |
| Backend | **Python + FastAPI** | Matches Python/ML background; clean, fast, typed. |
| Database | **Postgres** | Real persistence for favorites/history; industry standard. |
| Word data | **Curated JSON list + Free Dictionary API** | Curation = quality words; API = rich definitions, no key needed. |
| Daily-word logic | **Deterministic by date** | Same word for everyone each day; no scheduler/DB needed for selection. |
| Persistence | **Postgres** (with localStorage fallback) | Stores favorites + view history. |
| Containerization | **Docker + docker-compose** | 3 services (frontend, backend, db); strong portfolio signal. |
| Hosting | **AWS EC2 + docker-compose** | Start simple; ECS Fargate as a later stretch goal. |

---

## 3. Architecture Overview

```
                 ┌─────────────────────────────────────────┐
                 │              AWS EC2 instance             │
                 │            (docker-compose up)            │
                 │                                           │
   Browser  ───► │  ┌───────────┐   ┌───────────┐   ┌─────┐ │
                 │  │ frontend  │──►│ backend   │──►│ db  │ │
                 │  │ (nginx +  │   │ (FastAPI) │   │(PG) │ │
                 │  │  React)   │   │           │   │     │ │
                 │  └───────────┘   └─────┬─────┘   └─────┘ │
                 │                        │                  │
                 └────────────────────────┼──────────────────┘
                                          ▼
                              Free Dictionary API
                              (external, for definitions)
```

- **frontend**: React build served by nginx; calls backend at `/api/*`.
- **backend**: FastAPI; selects the daily word, enriches via Free Dictionary API
  (cached), exposes REST endpoints, persists favorites/history to Postgres.
- **db**: Postgres for favorites, history, and cached word definitions.

---

## 4. Project Structure

Principle: **flat over nested.** Don't create a folder until there are enough
files to justify it. Start minimal; split only when a file grows unwieldy.

```
vocabio/
├── docker-compose.yml
├── README.md
├── vocabio-plan.md
├── .gitignore
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx           # layout + views (split later if it grows)
│       ├── api.js            # fetch wrapper for the backend
│       ├── components/       # WordCard, HistoryList, FavoritesList, SearchBar
│       └── styles.css
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── .env.example
    ├── words.json           # curated word list
    └── app/
        ├── main.py          # FastAPI app + routes
        ├── config.py        # settings / env
        ├── db.py            # engine, session, SQLAlchemy models
        ├── schemas.py       # Pydantic schemas
        └── words.py         # daily-word + next-word + dictionary logic
```

Notes on staying clean:
- **Backend**: one module per concern. Routes live in `main.py` until they grow,
  then split into a `routers/` folder. Models + DB setup share `db.py` until the
  schema is big enough to warrant a `models.py`.
- **Frontend**: a single `api.js` and one `styles.css` instead of `api/` and
  `styles/` folders; `components/` holds flat `.jsx` files.
- Promote a file to a folder **only when it actually needs siblings** — avoid empty
  scaffolding.

---

## 5. Data Model (Postgres)

**word_cache** — cached enrichment from the dictionary API
| column | type | notes |
|---|---|---|
| id | PK | |
| word | text, unique | |
| phonetic | text | nullable |
| definition | text | |
| part_of_speech | text | nullable |
| example | text | nullable |
| fetched_at | timestamp | for cache expiry |

**daily_word** — record of which word was shown on which date
| column | type | notes |
|---|---|---|
| id | PK | |
| date | date, unique | |
| word | text | |

**favorite** — user-saved words
| column | type | notes |
|---|---|---|
| id | PK | |
| word | text | |
| created_at | timestamp | |

**known_word** — words the user marked "I know this"
| column | type | notes |
|---|---|---|
| id | PK | |
| word | text, unique | |
| created_at | timestamp | |

> Single-user assumed for now (no auth). A `user_id` column can be added later if
> authentication is introduced.

---

## 6. API Endpoints (FastAPI)

| Method | Path | Description |
|---|---|---|
| GET | `/api/word-of-the-day` | Today's word, enriched (definition, phonetic, example). |
| GET | `/api/word-of-the-day?date=YYYY-MM-DD` | Word for a specific date (history). |
| GET | `/api/words/next?exclude=w1,w2` | A fresh enriched word, skipping known words + provided exclusions ("Show me another"). |
| GET | `/api/words/{word}` | Look up / search any word's definition. |
| GET | `/api/history?days=30` | Last N days of daily words. |
| GET | `/api/favorites` | List saved favorites. |
| POST | `/api/favorites` | Add a favorite (`{ "word": "..." }`). |
| DELETE | `/api/favorites/{word}` | Remove a favorite. |
| GET | `/api/known` | List words marked known. |
| POST | `/api/known` | Mark a word known (`{ "word": "..." }`), used by "I know this". |
| DELETE | `/api/known/{word}` | Un-mark a known word. |
| GET | `/health` | Healthcheck for Docker/compose. |

**Daily word selection (deterministic):**
`index = hash(today_iso_date) % len(words)` → stable per day, identical for all
users, no scheduler required.

**Dictionary enrichment:** On request, check `word_cache`; if missing/stale, call
the Free Dictionary API (`https://api.dictionaryapi.dev/api/v2/entries/en/{word}`),
store the result, then return it. Graceful fallback if the word isn't found.

**"Next word" selection (`/api/words/next`):** Pick a **random** word from the
curated list, excluding (a) words in `known_word`, (b) the `exclude` list the
client passes (words already seen this session), and (c) today's daily word. This
keeps the "Show me another" / "I know this" flow surfacing fresh vocabulary. If
all words are exhausted, return a friendly "you've seen them all" response.

---

## 7. Frontend Features

- **Today's word card**: word, phonetic spelling, part of speech, definition,
  usage example, favorite (★) toggle.
- **Keep-going mode**: after the daily word, two actions on the card —
  **"Show me another"** (fetch a fresh word) and **"I know this ✓"** (mark known,
  then fetch a different word). Known words don't resurface.
  - Client tracks words seen this session and passes them to `/api/words/next`
    via `exclude` so the same word isn't repeated.
- **History view**: browse previous days' words.
- **Favorites view**: list and manage saved words.
- **Known words view**: review words marked known; un-mark to bring them back.
- **Search**: look up any word on demand.
- **Responsive layout**, clean typography (the word is the hero element).

---

## 8. Build Phases

### Phase 1 — Backend core (local, no Docker)
- FastAPI skeleton, `config.py`, run with uvicorn.
- `words.json` curated list (start ~100–365 interesting words).
- `services/daily_word.py` — deterministic date→word.
- `services/dictionary.py` — Free Dictionary API client (in-memory cache first).
- Endpoints: `/api/word-of-the-day`, `/api/words/next` (exclude-based, no known
  list yet), `/api/words/{word}`, `/health`.
- **Done when:** hitting the API returns today's enriched word and "next" serves a
  different one.

### Phase 2 — Frontend
- React + Vite scaffold, API client, `WordCard`.
- Wire to backend; render today's word.
- Add History, Favorites (localStorage first), Search components.
- "Show me another" + "I know this" buttons on `WordCard`; track session-seen
  words and pass them to `/api/words/next`.
- **Done when:** the site shows today's word, "keep-going" mode works, and basic
  navigation works.

### Phase 3 — Postgres + persistence
- Add Postgres, SQLAlchemy models, `database.py`.
- Move favorites + history + known words + dictionary cache to the DB.
- Favorites endpoints (`GET/POST/DELETE`); known endpoints (`GET/POST/DELETE`).
- Wire `/api/words/next` to skip known words.
- **Done when:** favorites, history, and known words survive restarts via the database.

### Phase 4 — Dockerize
- `backend/Dockerfile` (python slim + uvicorn).
- `frontend/Dockerfile` (multi-stage: vite build → nginx) + `nginx.conf` proxying `/api`.
- `docker-compose.yml`: `frontend`, `backend`, `db` services + healthchecks + volumes.
- **Done when:** `docker-compose up` runs the full app locally on one command.

### Phase 5 — Deploy to AWS EC2
- Launch EC2 (Amazon Linux), install Docker + compose.
- Configure security groups (80/443, SSH).
- Copy code / pull from Git; `docker-compose up -d`.
- Optional polish: domain via Route 53, HTTPS via ACM/Let's Encrypt.
- **Done when:** the site is reachable at the EC2 public address.

### Phase 6 — Stretch: ECS Fargate (later)
- Push images to ECR.
- Define ECS task/service, load balancer, RDS for Postgres.
- **Done when:** the app runs cloud-native on ECS without a managed VM.

---

## 9. Open Items / Decisions Deferred

- **Auth / multi-user**: out of scope for v1 (single-user). Revisit if needed.
- **Word list size & curation**: start small, grow over time.
- **CI/CD** (GitHub Actions to build/push images): nice-to-have after Phase 5.
- **Custom domain + HTTPS**: optional polish in Phase 5.

---

## 10. Resume / Portfolio Talking Points

- Full-stack app: React frontend + FastAPI backend + Postgres.
- Containerized multi-service architecture with Docker Compose.
- Deployed to AWS (EC2 → ECS Fargate migration path).
- External API integration with caching strategy.
- Clean REST API design.
