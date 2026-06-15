# Project Management MVP

Kanban board with AI chat assistant. Runs in Docker.

## Start

Linux / Mac:

```bash
./scripts/start.sh
```

Windows:

```bat
scripts\start.bat
```

Open http://localhost:8000

## Stop

Linux / Mac:

```bash
./scripts/stop.sh
```

Windows:

```bat
scripts\stop.bat
```

## Tests

Backend (from `backend/`):

```bash
uv sync
uv run pytest
```

Frontend (from `frontend/`):

```bash
npm run test:unit
npm run test:e2e:integrated
```

`test:e2e:integrated` builds the static export and runs Playwright against FastAPI on port 8000, matching the Docker runtime.
