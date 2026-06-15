# Backend

FastAPI application that serves the static frontend and exposes API routes under `/api/`.

## Layout

```
backend/
  app/
    main.py       # FastAPI app, routes, static file mount
    db.py         # SQLite helpers: init_db, get_db, read_board, write_board
    ai.py         # OpenRouter client and model constant
  static/
    .gitkeep      # Built frontend copied here at Docker/test time (from frontend/out)
  tests/
    test_main.py  # pytest tests
  pyproject.toml  # Python deps managed with uv
```

## Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | no | Health check, returns `{"status": "ok"}` |
| POST | `/api/auth/login` | no | Validate credentials, set HTTP-only `session_id` cookie |
| POST | `/api/auth/logout` | no | Destroy session, clear cookie |
| GET | `/api/auth/me` | yes | Return `{"username": ...}` or 401 |
| GET | `/api/board` | yes | Return full `BoardData` for the authenticated user |
| PUT | `/api/board` | yes | Replace full board state; returns 204 |
| POST | `/api/ai/test` | yes | Send "What is 2+2?" to OpenRouter; returns `{"response": ...}` |
| GET | `/` | no | Serves static files from `static/` |

API routes are registered before the static mount so `/api/*` is never caught by the file server.

## AI (OpenRouter)

`app/ai.py` exports `get_ai_client()` and `MODEL`. The client is an `AsyncOpenAI` instance pointed at `https://openrouter.ai/api/v1`, using model `openai/gpt-oss-120b:free`.

`OPENROUTER_API_KEY` must be set in the environment (loaded from the project root `.env` via Docker). If the key is absent, `get_ai_client()` raises `ValueError` and the endpoint returns 503.

`POST /api/ai/test` is a simple connectivity check: it sends "What is 2+2?" to OpenRouter and returns the model response as `{"response": "..."}`. It requires an authenticated session.

## Run locally (without Docker)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
cd backend
uv sync
uv run pytest
```

## Docker

The root `Dockerfile` copies this directory into the container, installs deps with `uv`, and runs uvicorn on port 8000.
