# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Kanban board with AI chat assistant. Next.js static frontend served by FastAPI at `/`; everything packaged in a single Docker container on port 8000. SQLite database. AI via OpenRouter.

## Commands

### Run the app (Docker)

```bash
./scripts/start.sh   # builds and starts container on port 8000
./scripts/stop.sh
```

### Backend (from `backend/`)

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000   # local dev, no Docker
uv run pytest                                       # all tests
uv run pytest tests/test_main.py::test_health      # single test
```

### Frontend (from `frontend/`)

```bash
npm install
npm run dev              # standalone dev server on port 3000
npm run lint
npm run test:unit        # Vitest
npm run test:e2e         # Playwright against port 3000
npm run test:e2e:integrated  # builds static export, runs Playwright against FastAPI on port 8000
```

## Architecture

### Request flow

Browser → FastAPI (port 8000) → `/api/*` routes handled in Python → SQLite  
Static frontend assets are served by FastAPI's `StaticFiles` mount at `/`. API routes are registered before the static mount so `/api/*` is never caught by the file server.

### Frontend build

Next.js uses `output: 'export'` — produces a static site in `frontend/out/`. The Dockerfile copies `out/` into `backend/static/`, which FastAPI serves. There is no Next.js server at runtime.

### Data model

```
BoardData = { columns: Column[], cards: Record<string, Card> }
Column    = { id, title, cardIds: string[] }
Card      = { id, title, details }
```

Five fixed column IDs: `col-backlog`, `col-discovery`, `col-progress`, `col-review`, `col-done`. Column count and IDs are enforced on every `PUT /api/board` and on AI board updates.

### Auth

Server-side sessions stored in an in-process dict (`sessions: dict[str, str]`). HTTP-only `session_id` cookie. Hardcoded credentials: `user` / `password`. Sessions are lost on container restart.

### AI

`app/ai.py` exports `get_ai_client()` (AsyncOpenAI pointed at OpenRouter) and `MODEL` (`openai/gpt-oss-120b:free`). The chat endpoint (`POST /api/ai/chat`) sends current board state and per-user conversation history, and expects structured JSON back:

```json
{ "message": "string", "boardUpdate": BoardData | null }
```

If `boardUpdate` is present and valid, it replaces the board in the database. Chat history is stored in the `chat_messages` SQLite table.

### Database

SQLite, initialized at startup via `init_db()`. Tables: `users`, `boards`, `columns`, `cards`, `chat_messages`. See `docs/DATABASE.md` for schema details and `docs/schema.json` for the JSON schema.

### Environment

`OPENROUTER_API_KEY` must be set. In Docker it is loaded from the project root `.env`. Locally, export it before running uvicorn.

## Coding standards

- No over-engineering. No unnecessary defensive programming.
- No emojis anywhere.
- Identify root cause before fixing — prove with evidence, then fix.
