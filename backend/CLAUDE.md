# Backend

FastAPI application that serves the static frontend and exposes API routes under `/api/`.

## Layout

```
backend/
  app/
    main.py       # FastAPI app, routes, lifespan, Pydantic models
    db.py         # SQLite helpers: init_db, get_db, read_board, write_board
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
| GET | `/` | no | Serves static files from `static/` |

API routes are registered before the static mount so `/api/*` is never caught by the file server.

## Auth

Sessions are stored in a module-level dict (`sessions: dict[str, str]`). On login a UUID session ID is generated and stored as an HTTP-only cookie. No passwords are stored in the database; credentials are hardcoded in `CREDENTIALS`.

## Database

SQLite via the built-in `sqlite3` module. `DB_PATH` defaults to `pm.db` next to the backend directory; override with the `DB_PATH` env var (used in tests via `monkeypatch`). `init_db()` is called at startup via FastAPI's lifespan and is idempotent. The `get_db()` generator is a FastAPI dependency that opens a connection, yields it, commits on success, and rolls back on error.

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
