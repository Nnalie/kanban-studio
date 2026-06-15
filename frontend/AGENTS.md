# Frontend

A Next.js 16 client-side Kanban board demo. All board state lives in React memory; there is no backend, auth, or persistence yet.

## Stack

- Next.js 16 (App Router), React 19, TypeScript
- Tailwind CSS 4 with CSS variables for the project color scheme
- `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` for drag and drop
- Vitest + Testing Library for unit tests; Playwright for e2e tests

## Directory layout

```
src/
  app/
    layout.tsx      # Root layout, Google fonts (Space Grotesk, Manrope)
    page.tsx        # Renders <KanbanBoard />
    globals.css     # Color tokens and base styles
  components/
    KanbanBoard.tsx       # Top-level board; owns all state
    KanbanColumn.tsx      # Single column with droppable area
    KanbanCard.tsx        # Sortable card with delete button
    KanbanCardPreview.tsx # Drag overlay preview
    NewCardForm.tsx       # Collapsible add-card form per column
  lib/
    kanban.ts             # Types, initialData, moveCard, createId
  test/
    setup.ts              # Vitest setup (jest-dom)
tests/
  kanban.spec.ts          # Playwright e2e tests
```

## Data model (`src/lib/kanban.ts`)

```ts
Card     = { id, title, details }
Column   = { id, title, cardIds: string[] }
BoardData = { columns: Column[], cards: Record<string, Card> }
```

- Five fixed columns with stable IDs: `col-backlog`, `col-discovery`, `col-progress`, `col-review`, `col-done`
- Column titles are user-editable; column count and IDs are fixed
- Cards have only `title` and `details` (no priority, assignee, etc.)
- `initialData` seeds the demo board with 8 sample cards; this will be replaced with an empty board when persistence is added
- `moveCard(columns, activeId, overId)` handles reorder within a column and moves between columns
- `createId(prefix)` generates unique IDs for new cards

## Components

### KanbanBoard

The single source of truth. Uses `useState<BoardData>` initialized from `initialData`.

Handlers (all update local state only):
- `handleDragStart` / `handleDragEnd` — dnd-kit drag lifecycle; calls `moveCard` on drop
- `handleRenameColumn` — updates column title in place
- `handleAddCard` — creates card via `createId`, appends to column `cardIds`
- `handleDeleteCard` — removes card from `cards` map and column `cardIds`

Renders a header (board title, column pills), a 5-column grid inside `DndContext`, and a `DragOverlay` with `KanbanCardPreview`.

### KanbanColumn

- Droppable zone (`useDroppable`) with yellow ring on hover
- Inline `<input>` for renaming the column title
- `SortableContext` wrapping `KanbanCard` list
- Empty-state placeholder ("Drop a card here")
- `NewCardForm` at the bottom
- `data-testid="column-{id}"` for tests

### KanbanCard

- Sortable (`useSortable`) with drag handle on the whole card
- Displays title and details; "Remove" button calls `onDelete`
- `data-testid="card-{id}"` for tests

### NewCardForm

- Toggle between "Add a card" button and a title/details form
- Title is required; details default to empty string (board sets "No details yet." if blank)

## Styling

Colors are defined as CSS variables in `globals.css`, matching the project palette:

| Token | Value | Usage |
|-------|-------|-------|
| `--accent-yellow` | `#ecad0a` | Accents, column indicators |
| `--primary-blue` | `#209dd7` | Links, add-card button |
| `--secondary-purple` | `#753991` | Submit buttons |
| `--navy-dark` | `#032147` | Headings |
| `--gray-text` | `#888888` | Supporting text |

Display font: Space Grotesk (`font-display`). Body font: Manrope.

## Tests

### Unit (`npm run test:unit`)

- `src/lib/kanban.test.ts` — `moveCard`: reorder within column, move to another column, drop on empty column
- `src/components/KanbanBoard.test.tsx` — renders 5 columns, renames column, adds and removes card

### E2E (`npm run test:e2e` / `npm run test:e2e:integrated`)

- `tests/kanban.spec.ts` — loads board, adds card, drags card between columns
- `test:e2e` — against Next.js dev server (port 3000)
- `test:e2e:integrated` — builds static export, serves via FastAPI on port 8000 (matches Docker runtime)

## What changes in later parts

| Part | Frontend change |
|------|-----------------|
| 3 | `output: 'export'` in `next.config.ts`; built to `out/`, served by FastAPI at `/` |
| 4 | Login modal overlay on `/`; logout button; gate board behind auth |
| 6–7 | Replace `initialData` / local state with API calls to `/api/...`; blank board for new users |
| 10 | AI chat sidebar; refresh board when AI returns a `boardUpdate` |

## Run locally (standalone)

```bash
npm install
npm run dev        # http://localhost:3000
npm run test:unit
npm run test:e2e
```

This standalone dev mode is for frontend work only. The final app runs inside Docker via `scripts/`.
