# Code review

Date: 2026-06-16
Scope: entire repository (backend, frontend, infra, tests, docs)

Overall the MVP is well structured, idiomatic, and matches the locked decisions in `docs/PLAN.md`. The findings below are ordered by severity. Each has a concrete action.

## Resolution status (2026-06-16)

All findings have been addressed. Tests after remediation: **28 backend, 14 frontend unit, 9 e2e (1 skipped by design)** — all passing.

| ID | Status | Notes |
|----|--------|-------|
| S1 | Done | Added `.env.example`. Key rotation is an external action for the owner (see S1). |
| S2 | Done | `*.db` added to `.gitignore`; `backend/pm.db` now ignored. |
| B1 | Done | New `build_validated_board()` rejects orphan/duplicate card refs with 400 on both `PUT` and AI paths; regression tests added. |
| B2 | Done | `columns` and `cards` now use composite `(board_id, id)` keys with a composite FK; IDs are board-scoped. Schema docs updated. |
| B3 | Done | Frontend shows a load-error state, a save-error banner, and returns to login on 401; `putBoard` throws on non-2xx. Unit test added. |
| M1 | Done | `get_chat_history` capped to the last `MAX_HISTORY_MESSAGES` (20). |
| M2 | Done | Documented in code: AI updates are server-authoritative; pending stale save is cancelled to keep local and server consistent. In practice unreachable (400 ms debounce vs multi-second AI latency). |
| M3 | Done | Validation + board-dict assembly unified in `build_validated_board()`. |
| M4 | Done | `PRAGMA journal_mode=WAL` and `busy_timeout=5000` set on every connection. |
| M5 | Verified | Parser already returns 502 on non-JSON (no crash); `response_format=json_object` retained. Live model confirmation remains a manual smoke test (needs key). |
| L1 | Done | `SKIP_FRONTEND_BUILD=1` opt-out added to `conftest.py` for fast backend-only iteration. |
| L2 | Done | `handleDeleteCard` now spreads `...board`. |
| L3 | Acknowledged | `StaticFiles(html=True)` is fine for the single-route app; revisit if client routing is added. No change. |
| L4 | Acknowledged | In-memory session expiry is acceptable for the local MVP. No change. |
| L5 | Done | Added orphan-card 400 tests (PUT + AI) and a frontend load-error test. |
| L6 | Acknowledged | No payload size limit; acceptable for local-only runtime. No change. |

The original findings are preserved below for reference.

---

## Security

### S1. Live OpenRouter API key sits in working-tree `.env` — rotate it
`/.env` contains a real `OPENROUTER_API_KEY`. Good news: `.env` is gitignored (`.gitignore:130`) and was never committed. However the key is a live secret that has been read during development and should be considered exposed.

- [ ] Rotate the OpenRouter key.
- [ ] Add a committed `.env.example` with `OPENROUTER_API_KEY=` (empty) so contributors know what is required.

### S2. `backend/pm.db` is untracked but NOT gitignored
There is no `*.db` rule in `.gitignore`, and a 40 KB local `backend/pm.db` exists in the working tree. It is currently untracked, but a stray `git add -A` would commit local data.

- [ ] Add `*.db` (or `backend/pm.db`) to `.gitignore`.

---

## Correctness (high)

### B1. Malformed board payload crashes with an unhandled 500
`write_board` (`backend/app/db.py:149`) does `card = board_data["cards"][card_id]` for every id in a column's `cardIds`. If a column lists a `cardId` that is absent from the `cards` map, this raises `KeyError`.

- `PUT /api/board`: `BoardIn` validates the column set but does not cross-check that every `cardId` referenced by a column exists in `cards`. A payload with an orphan `cardId` reaches `write_board` and returns an unhandled **500** (`backend/app/main.py:143`).
- `POST /api/ai/chat`: same gap. `write_board` is called at `backend/app/main.py:204`, **outside** the `try/except (KeyError, TypeError)` block that ends at line 203, so an inconsistent AI `boardUpdate` also yields a 500.

Actions:
- [ ] Add cross-validation (every `cardId` in `columns` must exist in `cards`, and ideally vice-versa) and return **400** for both the `PUT` and AI paths.
- [ ] Add regression tests: `PUT` with an orphan `cardId`, and an AI `boardUpdate` with an orphan `cardId`, both expecting 400.

### B2. Card IDs are globally unique across all boards (latent multi-user bug)
`cards.id` is a global `TEXT PRIMARY KEY` (`backend/app/db.py:60-66`), and `write_board` uses `INSERT OR REPLACE` keyed on `id` (`db.py:172-176`). The deletion query is board-scoped, but `INSERT OR REPLACE` is not: if two users' boards ever use the same card id (e.g. both `card-1`), one board would silently overwrite the other's row. Not triggerable today (single hardcoded user), but it contradicts the stated goal that "the database will support multiple users for future" (`AGENTS.md`).

- [ ] Either make card uniqueness per-column/per-board (composite key or a `board_id` column on `cards`), or document explicitly that card IDs must be globally unique and rely on `createId` entropy.

### B3. Frontend swallows all network errors silently
`KanbanBoard` does `getBoard().then(setBoard).catch(() => {})` (`KanbanBoard.tsx:30`) and `putBoard(next).catch(() => {})` (`KanbanBoard.tsx:39`).

- A failed initial load leaves the UI stuck on "Loading..." forever with no message.
- A failed save (e.g. the in-memory session was lost on a backend restart → 401) loses the user's change with no feedback; the board still looks saved.

Actions:
- [ ] Surface a load error state instead of an indefinite spinner.
- [ ] Surface save failures (toast/banner) and, on 401, drop back to the login modal.

---

## Correctness / robustness (medium)

### M1. AI chat history is unbounded
`get_chat_history` (`backend/app/db.py:124-129`) returns **every** message ever stored for the user, and all of them are sent on every `POST /api/ai/chat` call (`main.py:162-166`). Token usage and latency grow without limit over a long-lived session.

- [ ] Cap history to the last N messages (e.g. `ORDER BY id DESC LIMIT N` then reverse), or summarize older turns.

### M2. AI board update can discard a pending user edit
`handleBoardUpdate` (`KanbanBoard.tsx:114-117`) clears the debounced save timer and overwrites local board state. If a user mutation is mid-debounce (400 ms, `KanbanBoard.tsx:38`) when an AI response arrives, the pending `PUT` is cancelled and the local edit is replaced by the AI's board — the user edit is lost both locally and server-side.

- [ ] Flush a pending save before applying an AI update, or have the AI path reconcile rather than blind-replace.

### M3. Duplicated validation and board-building logic
The "5 columns + exact `COLUMN_IDS`" check and the `board_dict` assembly are duplicated between `put_board` (`main.py:129-143`) and `ai_chat` (`main.py:186-204`).

- [ ] Extract a `validate_board(columns)` and a `to_board_dict(columns, cards)` helper used by both paths. This also makes fixing B1 a single change.

### M4. SQLite concurrency settings
Connections use `check_same_thread=False` with a connection per request (`db.py:22-33`); FastAPI runs the sync endpoints in a threadpool. Under concurrent writes the default journal mode can raise "database is locked".

- [ ] Enable WAL and a busy timeout in `init_db`/`get_db` (`PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`). Low effort, removes a class of intermittent failures.

### M5. `response_format=json_object` depends on model support
`ai_chat` passes `response_format={"type": "json_object"}` (`main.py:172`). If `openai/gpt-oss-120b:free` does not honor it on OpenRouter, the call errors and the whole chat returns 503. The system prompt already instructs strict JSON, so the structured-output flag is belt-and-suspenders.

- [ ] Confirm the model supports it; if not, drop the flag and rely on the prompt (the parser already handles bad JSON with a 502).

---

## Low / style

- [ ] **L1.** `backend/tests/conftest.py:13-23` runs `npm ci && npm run build` on every backend pytest session, coupling backend unit tests to the Node toolchain and making them slow. Consider isolating the two static-serving tests (`test_root_returns_kanban_studio_html`, `test_next_static_assets_are_served`) behind a marker, or cache the build.
- [ ] **L2.** `handleDeleteCard` (`KanbanBoard.tsx:100-109`) builds `next` without spreading `...board`, unlike the sibling handlers. Harmless today (only `columns`/`cards` exist) but inconsistent and fragile if `BoardData` grows.
- [ ] **L3.** `app.mount("/", StaticFiles(..., html=True))` (`main.py:228`) is not a true SPA fallback — unknown client-side routes return 404. Fine for this single-route app; revisit if client routing is added (the plan mentioned SPA fallback).
- [ ] **L4.** In-memory `sessions` (`main.py:26`) never expire and are lost on restart. Acceptable for the MVP; note it if this ever leaves "local Docker only".
- [ ] **L5.** Add tests for the gaps above (B1 orphan-card 400s; a logout-then-PUT 401 path).
- [ ] **L6.** No request body size limit on board/chat payloads. Acceptable locally; worth a note if ever exposed.

---

## What is good (no action)

- Clean separation: `main.py` (routes), `db.py` (persistence), `ai.py` (model/client). DB access via a FastAPI dependency with commit/rollback handling (`db.py:22-33`).
- `PRAGMA foreign_keys = ON` is set on every connection.
- Board reconstruction/serialization in `read_board`/`write_board` maps exactly to the frontend `BoardData` shape, as documented in `docs/DATABASE.md`.
- Same-origin static serving means no CORS surface; API routes are registered before the static mount so `/api/*` is never shadowed.
- Chat history stores the raw user message, not the board-augmented prompt (`main.py:206` vs `ai.py:40`), keeping stored context clean.
- Multi-stage Dockerfile with `uv sync --frozen --no-dev` and a pinned `uv.lock`; reproducible builds.
- Test coverage is broad and meaningful across unit, integration, and e2e layers.

---

## Suggested order of work

1. S1, S2 (secrets / gitignore) — minutes.
2. B1 + M3 (validation crash, via shared helper) — highest correctness payoff.
3. B3 (frontend error surfacing).
4. M1, M4 (history cap, WAL).
5. B2, M2, M5 and the low items as follow-ups.
