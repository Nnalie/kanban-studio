# Scripts

Start and stop scripts for the Docker container.

| Script | Platform | Action |
|--------|----------|--------|
| `start.sh` | Linux / Mac | `docker compose up -d --build` |
| `stop.sh` | Linux / Mac | `docker compose down` |
| `start.bat` | Windows | `docker compose up -d --build` |
| `stop.bat` | Windows | `docker compose down` |
| `serve-built.sh` | Linux / Mac | Build frontend and serve via uvicorn on port 8000 (for e2e tests) |

All scripts run from the project root (they `cd` up one level from `scripts/`).
