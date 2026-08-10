# Vocabio — Word of the Day

A full-stack word-of-the-day web app. Each day shows a curated word with its
definition, pronunciation, and part of speech. You can keep going past the daily
word ("Show me another"), mark words you already know so they stop reappearing
("I know this"), save favorites, and look up any word

**Live demo:** https://vocabio.duckdns.org

## Stack

- **Frontend:** React + Vite, served by nginx
- **Backend:** FastAPI (Python), with per-IP rate limiting
- **Database:** Postgres (SQLite for local dev)
- **Word data:** curated list + the [Free Dictionary API](https://dictionaryapi.dev) for definitions
- **Infra:** Docker Compose (3 services), deployed on AWS EC2

## Run it with Docker (recommended)

```bash
docker compose up --build
# open http://localhost:8080
```

That starts the frontend, backend, and Postgres together. Stop with
`docker compose down` (add `-v` to also wipe the database volume).

## Run it for local development (no Docker)

```bash
./dev.sh
```

Starts the FastAPI backend (`:8000`, auto-reload) and the Vite dev server
(`:5173`) together; Ctrl-C stops both. Uses a local SQLite file, so no database
setup is needed.

<details>
<summary>Manual two-terminal setup</summary>

```bash
# terminal 1 — backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd frontend && npm install && npm run dev
```
</details>

## Tests

```bash
cd backend && .venv/bin/pip install -r requirements-dev.txt
python -m pytest
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/word-of-the-day` | Today's word (`?on=YYYY-MM-DD` for any date) |
| GET | `/api/words/next?exclude=a,b` | A fresh word, skipping seen + known words |
| GET | `/api/words/{word}` | Look up any word |
| GET/POST/DELETE | `/api/favorites` | Manage favorites |
| GET/POST/DELETE | `/api/known` | Manage "I know this" words |
| GET | `/health` | Healthcheck |
