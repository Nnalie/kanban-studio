# Database design

SQLite, created on first run inside the Docker container. No host volume mount required for MVP — data lives for the lifetime of the container.

## Tables

```
users ──< boards ──< columns ──< cards
users ──< chat_messages
```

### users

Stores credentials. Seeded on startup with the hardcoded MVP user.

| Column   | Type    | Notes              |
|----------|---------|--------------------|
| id       | INTEGER | PK, autoincrement  |
| username | TEXT    | unique, not null   |

### boards

One board per user for MVP. The extra table keeps future multi-board expansion cheap.

| Column  | Type    | Notes              |
|---------|---------|--------------------|
| id      | INTEGER | PK, autoincrement  |
| user_id | INTEGER | FK → users(id)     |

### columns

Five fixed rows per board. The `id` column holds the frontend stable IDs (`col-backlog`, `col-discovery`, `col-progress`, `col-review`, `col-done`), so no translation is needed between the API and the frontend.

| Column   | Type    | Notes               |
|----------|---------|---------------------|
| id       | TEXT    | PK, e.g. col-backlog|
| board_id | INTEGER | FK → boards(id)     |
| title    | TEXT    | user-editable       |
| position | INTEGER | 0–4, fixed order    |

Column IDs are fixed. Only `title` changes.

### cards

One row per card. The `id` column holds the frontend-generated IDs (e.g. `card-abc123`), matching the `createId` function output.

| Column    | Type    | Notes                    |
|-----------|---------|--------------------------|
| id        | TEXT    | PK, frontend-generated   |
| column_id | TEXT    | FK → columns(id)         |
| title     | TEXT    | not null                 |
| details   | TEXT    | not null, default ''     |
| position  | INTEGER | order within the column  |

### chat_messages

Conversation history per user, sent as context on every AI call.

| Column     | Type    | Notes                    |
|------------|---------|--------------------------|
| id         | INTEGER | PK, autoincrement        |
| user_id    | INTEGER | FK → users(id)           |
| role       | TEXT    | 'user' or 'assistant'    |
| content    | TEXT    | message body             |
| created_at | TEXT    | ISO 8601 UTC timestamp   |

## Mapping to frontend BoardData

The frontend type:

```ts
BoardData = {
  columns: { id, title, cardIds: string[] }[]
  cards:   Record<string, { id, title, details }>
}
```

`GET /api/board` reconstructs this from SQL:
1. Select all columns for the user's board, ordered by `position`.
2. For each column, select its cards ordered by `position`; collect their ids into `cardIds`.
3. Build the `cards` map from all card rows.

`PUT /api/board` writes back the full state:
1. For each column in the payload: update `title` and `position` (by array index).
2. Delete cards no longer present; insert new cards; update existing cards' `title`, `details`, `column_id`, and `position`.

## Blank-board initialization

When a new user first calls `GET /api/board`:
1. Create a `boards` row for the user.
2. Insert five `columns` rows with default titles and positions (see `schema.json` → `default_columns`).
3. Return the empty board (no cards).

## Startup seeding

On application startup:
1. Create all tables if they do not exist.
2. Insert the hardcoded user (`username = 'user'`) if not present. The MVP does not store passwords in the database; authentication is handled entirely in memory against the hardcoded credentials map.
