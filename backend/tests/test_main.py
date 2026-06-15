import json
import re
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db import DEFAULT_COLUMNS, get_db, init_db
from app.main import STATIC_DIR, app, sessions

BLANK_BOARD = {
    "columns": [
        {"id": col["id"], "title": col["title"], "cardIds": []}
        for col in DEFAULT_COLUMNS
    ],
    "cards": {},
}

VALID_BOARD_WITH_CARD = {
    "columns": [
        {"id": "col-backlog",   "title": "Backlog",     "cardIds": ["card-1"]},
        {"id": "col-discovery", "title": "Discovery",   "cardIds": []},
        {"id": "col-progress",  "title": "In Progress", "cardIds": []},
        {"id": "col-review",    "title": "Review",      "cardIds": []},
        {"id": "col-done",      "title": "Done",        "cardIds": []},
    ],
    "cards": {"card-1": {"id": "card-1", "title": "Task A", "details": "Details A"}},
}


@pytest.fixture(autouse=True)
def reset_sessions():
    sessions.clear()
    yield
    sessions.clear()


@pytest.fixture
def client(tmp_path):
    db_file = str(tmp_path / "test.db")

    def override_get_db():
        conn = sqlite3.connect(db_file, check_same_thread=False)
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

    import app.db as db_module

    original = db_module.DB_PATH
    db_module.DB_PATH = db_file
    init_db()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db_module.DB_PATH = original


@pytest.fixture
def authed(client: TestClient) -> TestClient:
    client.post("/api/auth/login", json={"username": "user", "password": "password"})
    return client


# --- Existing tests ---

def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_kanban_studio_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Kanban Studio" in response.text


def test_next_static_assets_are_served(client: TestClient) -> None:
    index_html = (STATIC_DIR / "index.html").read_text()
    match = re.search(r"/_next/static/[^\"']+", index_html)
    assert match is not None, "No _next/static asset reference found in index.html"

    response = client.get(match.group(0))
    assert response.status_code == 200


def test_login_valid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    assert response.status_code == 200
    assert response.json() == {"username": "user"}
    assert "session_id" in response.cookies


def test_login_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "wrong"}
    )
    assert response.status_code == 401


def test_me_without_session_returns_401(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_valid_session_returns_username(authed: TestClient) -> None:
    response = authed.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"username": "user"}


def test_logout_clears_session(authed: TestClient) -> None:
    authed.post("/api/auth/logout")
    response = authed.get("/api/auth/me")
    assert response.status_code == 401


# --- Board tests ---

def test_get_board_unauthenticated_returns_401(client: TestClient) -> None:
    assert client.get("/api/board").status_code == 401


def test_put_board_unauthenticated_returns_401(client: TestClient) -> None:
    assert client.put("/api/board", json=BLANK_BOARD).status_code == 401


def test_first_get_board_returns_blank_board(authed: TestClient) -> None:
    response = authed.get("/api/board")
    assert response.status_code == 200
    board = response.json()
    assert len(board["columns"]) == 5
    assert board["cards"] == {}
    col_ids = [col["id"] for col in board["columns"]]
    assert col_ids == [
        "col-backlog", "col-discovery", "col-progress", "col-review", "col-done"
    ]


def test_put_board_persists_and_get_returns_updated(authed: TestClient) -> None:
    assert authed.put("/api/board", json=VALID_BOARD_WITH_CARD).status_code == 204
    board = authed.get("/api/board").json()
    assert board["columns"][0]["cardIds"] == ["card-1"]
    assert board["cards"]["card-1"]["title"] == "Task A"


def test_rename_column_persists(authed: TestClient) -> None:
    renamed = {
        **BLANK_BOARD,
        "columns": [
            {"id": "col-backlog",   "title": "My Backlog",  "cardIds": []},
            *BLANK_BOARD["columns"][1:],
        ],
    }
    authed.put("/api/board", json=renamed)
    board = authed.get("/api/board").json()
    assert board["columns"][0]["title"] == "My Backlog"


def test_add_card_persists(authed: TestClient) -> None:
    authed.put("/api/board", json=VALID_BOARD_WITH_CARD)
    board = authed.get("/api/board").json()
    assert "card-1" in board["cards"]
    assert board["cards"]["card-1"]["details"] == "Details A"


def test_delete_card_persists(authed: TestClient) -> None:
    authed.put("/api/board", json=VALID_BOARD_WITH_CARD)
    authed.put("/api/board", json=BLANK_BOARD)
    board = authed.get("/api/board").json()
    assert board["cards"] == {}


def test_move_card_between_columns_persists(authed: TestClient) -> None:
    authed.put("/api/board", json=VALID_BOARD_WITH_CARD)
    moved = {
        "columns": [
            {"id": "col-backlog",   "title": "Backlog",     "cardIds": []},
            {"id": "col-discovery", "title": "Discovery",   "cardIds": ["card-1"]},
            {"id": "col-progress",  "title": "In Progress", "cardIds": []},
            {"id": "col-review",    "title": "Review",      "cardIds": []},
            {"id": "col-done",      "title": "Done",        "cardIds": []},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "Task A", "details": "Details A"}},
    }
    authed.put("/api/board", json=moved)
    board = authed.get("/api/board").json()
    assert board["columns"][0]["cardIds"] == []
    assert board["columns"][1]["cardIds"] == ["card-1"]


def test_put_board_invalid_column_ids_returns_400(authed: TestClient) -> None:
    bad = {
        "columns": [
            {"id": "col-wrong",     "title": "X", "cardIds": []},
            {"id": "col-discovery", "title": "Discovery", "cardIds": []},
            {"id": "col-progress",  "title": "In Progress", "cardIds": []},
            {"id": "col-review",    "title": "Review", "cardIds": []},
            {"id": "col-done",      "title": "Done", "cardIds": []},
        ],
        "cards": {},
    }
    assert authed.put("/api/board", json=bad).status_code == 400


def test_put_board_wrong_column_count_returns_400(authed: TestClient) -> None:
    bad = {
        "columns": BLANK_BOARD["columns"][:3],
        "cards": {},
    }
    assert authed.put("/api/board", json=bad).status_code == 400


# --- AI test endpoint tests ---

def test_ai_test_requires_auth(client: TestClient) -> None:
    assert client.post("/api/ai/test").status_code == 401


def test_ai_test_missing_key_returns_503(authed: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = authed.post("/api/ai/test")
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


# --- AI chat tests ---

FIVE_COLUMNS = [
    {"id": "col-backlog",   "title": "Backlog",     "cardIds": []},
    {"id": "col-discovery", "title": "Discovery",   "cardIds": []},
    {"id": "col-progress",  "title": "In Progress", "cardIds": []},
    {"id": "col-review",    "title": "Review",      "cardIds": []},
    {"id": "col-done",      "title": "Done",        "cardIds": []},
]


def _mock_ai(response_payload: dict):
    """Return a mock get_ai_client that yields the given payload as JSON."""
    content = json.dumps(response_payload)
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = content
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    return patch("app.main.get_ai_client", return_value=mock_client)


def test_ai_chat_requires_auth(client: TestClient) -> None:
    assert client.post("/api/ai/chat", json={"message": "hi"}).status_code == 401


def test_ai_chat_stores_message_in_history(authed: TestClient) -> None:
    payload = {"message": "Just chatting", "boardUpdate": None}
    with _mock_ai(payload):
        response = authed.post("/api/ai/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert response.json()["message"] == "Just chatting"
    assert response.json()["boardUpdate"] is None


def test_ai_chat_with_board_update_persists(authed: TestClient) -> None:
    board_with_card = {
        "columns": [
            {"id": "col-backlog",   "title": "Backlog",     "cardIds": ["card-new"]},
            {"id": "col-discovery", "title": "Discovery",   "cardIds": []},
            {"id": "col-progress",  "title": "In Progress", "cardIds": []},
            {"id": "col-review",    "title": "Review",      "cardIds": []},
            {"id": "col-done",      "title": "Done",        "cardIds": []},
        ],
        "cards": {"card-new": {"id": "card-new", "title": "AI Task", "details": "Created by AI"}},
    }
    payload = {"message": "Added a card", "boardUpdate": board_with_card}
    with _mock_ai(payload):
        response = authed.post("/api/ai/chat", json={"message": "Add a card"})
    assert response.status_code == 200
    assert response.json()["boardUpdate"] is not None

    board = authed.get("/api/board").json()
    assert "card-new" in board["cards"]
    assert board["cards"]["card-new"]["title"] == "AI Task"


def test_ai_chat_without_board_update_board_unchanged(authed: TestClient) -> None:
    authed.put("/api/board", json=VALID_BOARD_WITH_CARD)
    payload = {"message": "No changes", "boardUpdate": None}
    with _mock_ai(payload):
        authed.post("/api/ai/chat", json={"message": "What is on the board?"})

    board = authed.get("/api/board").json()
    assert "card-1" in board["cards"]


def test_ai_chat_invalid_board_update_rejected(authed: TestClient) -> None:
    bad_board = {
        "columns": [
            {"id": "col-wrong",     "title": "X",           "cardIds": []},
            {"id": "col-discovery", "title": "Discovery",   "cardIds": []},
            {"id": "col-progress",  "title": "In Progress", "cardIds": []},
            {"id": "col-review",    "title": "Review",      "cardIds": []},
            {"id": "col-done",      "title": "Done",        "cardIds": []},
        ],
        "cards": {},
    }
    payload = {"message": "Bad update", "boardUpdate": bad_board}
    with _mock_ai(payload):
        response = authed.post("/api/ai/chat", json={"message": "Do something bad"})
    assert response.status_code == 400


def test_ai_chat_history_included_in_subsequent_calls(authed: TestClient) -> None:
    captured_calls: list = []

    async def capturing_create(**kwargs):
        captured_calls.append(kwargs["messages"])
        content = json.dumps({"message": "ok", "boardUpdate": None})
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = content
        return mock_completion

    mock_client = MagicMock()
    mock_client.chat.completions.create = capturing_create

    with patch("app.main.get_ai_client", return_value=mock_client):
        authed.post("/api/ai/chat", json={"message": "First message"})
        authed.post("/api/ai/chat", json={"message": "Second message"})

    assert len(captured_calls) == 2
    second_call_messages = captured_calls[1]
    roles = [m["role"] for m in second_call_messages]
    assert roles.count("user") >= 2
    assert roles.count("assistant") >= 1
