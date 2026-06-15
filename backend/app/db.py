import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

DB_PATH: str = os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "pm.db"))

COLUMN_IDS: frozenset[str] = frozenset(
    {"col-backlog", "col-discovery", "col-progress", "col-review", "col-done"}
)

DEFAULT_COLUMNS: list[dict] = [
    {"id": "col-backlog",   "title": "Backlog",     "position": 0},
    {"id": "col-discovery", "title": "Discovery",   "position": 1},
    {"id": "col-progress",  "title": "In Progress", "position": 2},
    {"id": "col-review",    "title": "Review",      "position": 3},
    {"id": "col-done",      "title": "Done",        "position": 4},
]


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id       TEXT    PRIMARY KEY,
            board_id INTEGER NOT NULL REFERENCES boards(id),
            title    TEXT    NOT NULL,
            position INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id        TEXT    PRIMARY KEY,
            column_id TEXT    NOT NULL REFERENCES columns(id),
            title     TEXT    NOT NULL,
            details   TEXT    NOT NULL DEFAULT '',
            position  INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", ("user",))
    conn.commit()
    conn.close()


def get_or_create_board(user_id: int, conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM boards WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO boards (user_id) VALUES (?)", (user_id,))
    board_id = cur.lastrowid
    for col in DEFAULT_COLUMNS:
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col["id"], board_id, col["title"], col["position"]),
        )
    return board_id


def read_board(board_id: int, conn: sqlite3.Connection) -> dict:
    cols = conn.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    columns = []
    cards: dict[str, dict] = {}
    for col in cols:
        col_cards = conn.execute(
            "SELECT id, title, details FROM cards WHERE column_id = ? ORDER BY position",
            (col["id"],),
        ).fetchall()
        card_ids = []
        for card in col_cards:
            card_ids.append(card["id"])
            cards[card["id"]] = {
                "id": card["id"],
                "title": card["title"],
                "details": card["details"],
            }
        columns.append({"id": col["id"], "title": col["title"], "cardIds": card_ids})

    return {"columns": columns, "cards": cards}


def get_chat_history(user_id: int, conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def append_chat_message(user_id: int, role: str, content: str, conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO chat_messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (user_id, role, content, datetime.now(timezone.utc).isoformat()),
    )


def write_board(board_id: int, board_data: dict, conn: sqlite3.Connection) -> None:
    for idx, col in enumerate(board_data["columns"]):
        conn.execute(
            "UPDATE columns SET title = ?, position = ? WHERE id = ? AND board_id = ?",
            (col["title"], idx, col["id"], board_id),
        )

    incoming: dict[str, dict] = {}
    for col in board_data["columns"]:
        for pos, card_id in enumerate(col["cardIds"]):
            card = board_data["cards"][card_id]
            incoming[card_id] = {
                "id": card_id,
                "column_id": col["id"],
                "title": card["title"],
                "details": card["details"],
                "position": pos,
            }

    current_ids = {
        row["id"]
        for row in conn.execute(
            "SELECT cards.id FROM cards"
            " JOIN columns ON cards.column_id = columns.id"
            " WHERE columns.board_id = ?",
            (board_id,),
        )
    }

    for card_id in current_ids - set(incoming):
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))

    for c in incoming.values():
        conn.execute(
            "INSERT OR REPLACE INTO cards (id, column_id, title, details, position)"
            " VALUES (?, ?, ?, ?, ?)",
            (c["id"], c["column_id"], c["title"], c["details"], c["position"]),
        )
