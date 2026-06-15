# Project plan

## Locked decisions

These were confirmed before implementation:

| Topic | Decision |
|-------|----------|
| Columns | Five fixed columns (`col-backlog`, `col-discovery`, `col-progress`, `col-review`, `col-done`). Only titles are editable; users cannot add or remove columns. |
| Card fields | `title` and `details` only |
| New user board | Blank board (empty columns, no seed cards) |
| Auth | Server-side session with HTTP-only cookie; credentials hardcoded to `user` / `password` |
| Login UX | Modal overlay on `/` |
| Frontend build | Next.js static export (`output: 'export'`), served by FastAPI at `/` |
| API prefix | `/api/...` |
| Runtime | Docker only; no non-container dev mode |
| Port | `8000` (single container) |
| Database | SQLite, created on first run; no host volume persistence required for MVP |
| AI model | `openai/gpt-oss-120b:free` via OpenRouter |
| AI history | Stored server-side per user session |
| AI structured output | `{ message: string, boardUpdate?: BoardData }` — proposed schema, review at Part 9 |
| Backend tests | pytest |
| Frontend tests | Vitest (unit) + Playwright (e2e) |
| Test environment | FastAPI + static frontend in-process; no full Docker stack in CI |
| Start/stop scripts | Wrap `docker compose up` / `docker compose down` |
| Env vars | `OPENROUTER_API_KEY` in project root `.env` only |

## Review gates

The agent stops and waits for user approval at:

- **Part 1** — this enriched plan and `frontend/AGENTS.md`
- **Part 5** — database schema JSON and `docs/` database approach

---

## Part 1: Plan

Document the existing frontend and produce this detailed plan.

### Substeps

- [x] Explore `frontend/` codebase
- [x] Create `frontend/AGENTS.md`
- [x] Enrich `docs/PLAN.md` with substeps, tests, and success criteria for Parts 2–10
- [x] User reviews and approves plan

### Success criteria

- `frontend/AGENTS.md` accurately describes the current frontend architecture, data model, components, and tests
- Every part (2–10) has a checklist, test plan, and success criteria
- Locked decisions are recorded and reflected in the plan

---

## Part 2: Scaffolding

Set up Docker, FastAPI backend, and start/stop scripts. Confirm a hello-world static page and a sample API call work inside the container.

### Substeps

- [x] Create `backend/` FastAPI app with a health/example route at `GET /api/health`
- [x] Add `pyproject.toml` managed with `uv`; pin FastAPI and dependencies
- [x] Create `Dockerfile` — multi-stage: build Next.js static export (placeholder HTML for now), install Python deps with `uv`, run FastAPI
- [x] Create `docker-compose.yml` — single service on port `8000`, mount `.env` for `OPENROUTER_API_KEY`
- [x] FastAPI serves static files at `/` (placeholder `index.html` confirming hello world)
- [x] FastAPI mounts API routes under `/api/`
- [x] Create `scripts/start.sh`, `scripts/start.bat`, `scripts/stop.sh`, `scripts/stop.bat` wrapping `docker compose up -d` and `docker compose down`
- [x] Create `backend/AGENTS.md` describing the backend layout
- [x] Update root `README.md` with minimal start/stop instructions

### Tests

- [x] `pytest`: `GET /api/health` returns 200 with expected JSON
- [x] `pytest`: `GET /` returns 200 with HTML containing "hello" (or equivalent placeholder)
- [x] Manual: `scripts/start.sh` brings up container; `curl localhost:8000/api/health` succeeds; `scripts/stop.sh` tears down

### Success criteria

- `docker compose up` starts the app on port 8000
- Browser at `http://localhost:8000` shows placeholder static page
- `http://localhost:8000/api/health` returns a JSON response
- Start/stop scripts work on Linux, Mac (.sh), and Windows (.bat)

---

## Part 3: Add in Frontend

Build the existing Next.js Kanban demo as a static export and serve it from FastAPI at `/`.

### Substeps

- [x] Add `output: 'export'` to `frontend/next.config.ts`
- [x] Update Dockerfile build stage to run `npm ci && npm run build` in `frontend/`
- [x] Copy `frontend/out/` into the container static directory served by FastAPI
- [x] Configure FastAPI static file serving with SPA fallback (serve `index.html` for non-API, non-file routes)
- [x] Verify all frontend assets (`_next/static/...`) are served correctly
- [x] Update Playwright config to target port 8000 when testing against the built app (or add a test mode flag)

### Tests

- [x] `pytest`: `GET /` returns 200 with HTML containing "Kanban Studio"
- [x] `pytest`: static assets under `/_next/` return 200
- [x] Frontend unit tests still pass: `npm run test:unit`
- [x] Playwright e2e: board loads, adds card, moves card (against FastAPI-served build or documented test setup)

### Success criteria

- `http://localhost:8000` displays the full Kanban board demo
- Drag-and-drop, rename, add, and delete all work in the browser
- No Next.js dev server required at runtime

---

## Part 4: Fake user sign in

Gate the Kanban behind login. Credentials: `user` / `password`. Login is a modal overlay on `/`. Logout available when signed in.

### Substeps

- [x] Backend: `POST /api/auth/login` — validate credentials, create server-side session, set HTTP-only cookie
- [x] Backend: `POST /api/auth/logout` — destroy session, clear cookie
- [x] Backend: `GET /api/auth/me` — return current user or 401
- [x] Backend: auth dependency/middleware protecting `/api/*` routes (except login)
- [x] Frontend: login modal component (username + password fields, submit button)
- [x] Frontend: on page load, check auth state; show modal if unauthenticated
- [x] Frontend: logout button in board header
- [x] Frontend: redirect or hide board content until authenticated

### Tests

- [x] `pytest`: login with valid credentials returns 200 and sets cookie
- [x] `pytest`: login with invalid credentials returns 401
- [x] `pytest`: protected route without cookie returns 401
- [x] `pytest`: protected route with valid session returns 200
- [x] `pytest`: logout clears session
- [x] Frontend unit: login modal renders, shows error on bad credentials
- [x] Playwright e2e: unauthenticated visit shows login modal; login reveals board; logout hides board

### Success criteria

- Visiting `/` without a session shows the login modal
- `user` / `password` grants access to the Kanban
- Wrong credentials show an error; board stays hidden
- Logout returns to login modal state
- API routes reject unauthenticated requests

---

## Part 5: Database modeling

Design the SQLite schema for the Kanban board. Save schema as JSON. Document the approach in `docs/`.

### Substeps

- [x] Define schema JSON (`docs/schema.json` or similar) covering:
  - `users` table (id, username — supports future multi-user)
  - `boards` table (id, user_id — one board per user for MVP)
  - `columns` table (id, board_id, title, position — five fixed rows per board)
  - `cards` table (id, column_id, title, details, position)
  - `chat_messages` table (id, user_id, role, content, created_at — for AI history)
- [x] Document table relationships and design rationale in `docs/DATABASE.md`
- [x] Define default column titles and IDs for new boards
- [x] Define blank-board initialization (five empty columns, no cards)
- [ ] **Stop for user review and approval**

### Tests

- N/A (design-only part; tests begin in Part 6)

### Success criteria

- Schema JSON is complete and maps to the frontend `BoardData` shape
- `docs/DATABASE.md` explains tables, relationships, and initialization
- User has reviewed and approved the schema

---

## Part 6: Backend

Implement API routes to read and modify the Kanban for the authenticated user. Create the SQLite database on first run.

### Substeps

- [x] Set up SQLAlchemy (or sqlite3) with models matching approved schema
- [x] Database init: create tables and seed the hardcoded `user` if not present
- [x] `GET /api/board` — return full board JSON for authenticated user (create blank board on first access)
- [x] `PUT /api/board` — replace full board state (used after drag/edit/add/delete)
- [x] Ensure column IDs are enforced (reject boards with wrong column count or IDs)
- [x] All board routes require authentication

### Tests

- [x] `pytest`: first `GET /api/board` for new user returns blank board with five default columns
- [x] `pytest`: `PUT /api/board` persists changes; subsequent `GET` returns updated state
- [x] `pytest`: move card, rename column, add card, delete card via PUT — state is correct
- [x] `pytest`: unauthenticated board access returns 401
- [x] `pytest`: invalid board payload (wrong column IDs) returns 400

### Success criteria

- Authenticated user can read and write their board via API
- New users get a blank board with five empty columns
- Board state persists across requests within the same container lifetime
- Invalid payloads are rejected

---

## Part 7: Frontend + Backend

Connect the frontend to the backend API so the Kanban is persistent.

### Substeps

- [x] Create `frontend/src/lib/api.ts` — fetch helpers for `/api/board`, `/api/auth/*` with credentials
- [x] Replace `initialData` initialization with `GET /api/board` on mount
- [x] On every board mutation (drag, rename, add, delete), debounce or immediately `PUT /api/board`
- [x] Handle loading and error states
- [x] Remove or repurpose `initialData` seed cards (backend provides blank board)
- [x] Ensure auth flow from Part 4 integrates with API calls (credentials: include)

### Tests

- [x] Frontend unit: API helpers mock fetch correctly
- [x] Frontend unit: board loads from API, mutations call PUT
- [x] `pytest` integration: full flow — login, get blank board, add card via PUT, get board shows card
- [x] Playwright e2e: login, add card, refresh page — card persists
- [x] Playwright e2e: rename column, refresh — title persists
- [x] Playwright e2e: drag card, refresh — position persists

### Success criteria

- All board operations persist across page refreshes
- New users see a blank board (not demo seed data)
- Frontend and backend stay in sync
- Error states are handled gracefully

---

## Part 8: AI connectivity

Backend can call OpenRouter. Verify connectivity with a simple prompt.

### Substeps

- [x] Add OpenAI-compatible client pointed at OpenRouter (`https://openrouter.ai/api/v1`)
- [x] Read `OPENROUTER_API_KEY` from environment
- [x] `POST /api/ai/test` (or internal test helper) — send "What is 2+2?" and return the model response
- [x] Handle API errors (missing key, network failure) with clear error responses
- [x] Document the AI setup in `backend/AGENTS.md`

### Tests

- [x] `pytest`: endpoint exists and validates auth
- [x] `pytest`: missing API key returns clear error
- [ ] Manual smoke test: call the test endpoint with a valid key and confirm a sensible response

### Success criteria

- Backend successfully calls OpenRouter with `openai/gpt-oss-120b:free`
- Missing or invalid API key produces a clear error, not a crash
- Manual smoke test confirms end-to-end AI connectivity

---

## Part 9: AI with board context

Extend the AI endpoint to include the Kanban JSON, user message, and server-stored conversation history. AI responds with structured output.

### Proposed structured output schema

```json
{
  "message": "string — reply shown to the user",
  "boardUpdate": "BoardData | null — full board replacement if the AI changed the Kanban"
}
```

### Substeps

- [x] Store chat messages in `chat_messages` table (role: user/assistant, content, timestamp)
- [x] `POST /api/ai/chat` — accept `{ message: string }`, load board + history, call AI
- [x] System prompt instructs AI to return JSON matching the schema above
- [x] Parse structured output; if `boardUpdate` is present, validate and persist to database
- [x] Append user message and assistant response to history
- [x] Return `{ message, boardUpdate }` to the client
- [x] AI can create, edit, move, and delete cards via `boardUpdate`

### Tests

- [x] `pytest`: chat endpoint requires auth
- [x] `pytest`: message is stored in history
- [x] `pytest`: mock AI response with `boardUpdate` — board is updated in database
- [x] `pytest`: mock AI response without `boardUpdate` — board unchanged
- [x] `pytest`: invalid `boardUpdate` (bad column IDs) is rejected
- [x] `pytest`: conversation history is included in subsequent AI calls
- [ ] Manual smoke test: ask AI to create a card; verify board updates

### Success criteria

- AI receives current board state and conversation history
- Structured output is parsed reliably
- Board updates from AI are validated and persisted
- Chat history accumulates across messages

---

## Part 10: AI chat sidebar

Add a sidebar chat widget to the UI. AI responses appear in the chat; board updates from AI refresh the board automatically.

### Substeps

- [x] Create `ChatSidebar` component — message list, input field, send button
- [x] Sidebar layout: board main area + fixed right sidebar
- [x] On send: `POST /api/ai/chat`, display assistant `message` in chat
- [x] If response includes `boardUpdate`, refresh board state in the UI (apply locally)
- [x] Show loading indicator while AI responds
- [x] Style sidebar using project color scheme
- [x] Handle AI errors gracefully in the chat UI

### Tests

- [x] Frontend unit: chat sidebar renders, sends message, displays response
- [x] Frontend unit: board refresh triggered when `boardUpdate` is returned
- [x] Playwright e2e: login, open chat, send message, see response
- [x] Playwright e2e: ask AI to add a card (mock AI response), verify card appears on board
- [x] `pytest`: existing Part 9 tests still pass

### Success criteria

- Chat sidebar is visible and functional alongside the Kanban board
- User can send messages and see AI replies
- When AI modifies the board, the UI updates without a manual refresh
- The feature works end-to-end inside Docker on port 8000
