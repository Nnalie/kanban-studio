import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel

from app.ai import MODEL, SYSTEM_PROMPT, build_user_message, get_ai_client
from app.db import (
    COLUMN_IDS,
    append_chat_message,
    get_chat_history,
    get_db,
    get_or_create_board,
    init_db,
    read_board,
    write_board,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

CREDENTIALS = {"user": "password"}
sessions: dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Project Management MVP", lifespan=lifespan)


# --- Pydantic models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class CardIn(BaseModel):
    id: str
    title: str
    details: str


class ColumnIn(BaseModel):
    id: str
    title: str
    cardIds: list[str] = []


class BoardIn(BaseModel):
    columns: list[ColumnIn]
    cards: dict[str, CardIn]


class ChatRequest(BaseModel):
    message: str


# --- Helpers ---

def get_current_user(session_id: str | None = Cookie(default=None)) -> str:
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions[session_id]


def get_user_id(username: str, conn) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return row["id"]


# --- Routes ---

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: LoginRequest, response: Response) -> dict[str, str]:
    if CREDENTIALS.get(body.username) != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id = str(uuid.uuid4())
    sessions[session_id] = body.username
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return {"username": body.username}


@app.post("/api/auth/logout")
def logout(
    response: Response, session_id: str | None = Cookie(default=None)
) -> dict[str, str]:
    if session_id and session_id in sessions:
        del sessions[session_id]
    response.delete_cookie("session_id")
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(current_user: str = Depends(get_current_user)) -> dict[str, str]:
    return {"username": current_user}


@app.get("/api/board")
def get_board(
    current_user: str = Depends(get_current_user),
    conn=Depends(get_db),
) -> dict:
    user_id = get_user_id(current_user, conn)
    board_id = get_or_create_board(user_id, conn)
    return read_board(board_id, conn)


@app.put("/api/board", status_code=204)
def put_board(
    body: BoardIn,
    current_user: str = Depends(get_current_user),
    conn=Depends(get_db),
) -> None:
    if len(body.columns) != 5 or {col.id for col in body.columns} != COLUMN_IDS:
        raise HTTPException(status_code=400, detail="Invalid column IDs")
    user_id = get_user_id(current_user, conn)
    board_id = get_or_create_board(user_id, conn)
    board_dict = {
        "columns": [
            {"id": col.id, "title": col.title, "cardIds": col.cardIds}
            for col in body.columns
        ],
        "cards": {
            k: {"id": v.id, "title": v.title, "details": v.details}
            for k, v in body.cards.items()
        },
    }
    write_board(board_id, board_dict, conn)


@app.post("/api/ai/chat")
async def ai_chat(
    body: ChatRequest,
    current_user: str = Depends(get_current_user),
    conn=Depends(get_db),
) -> dict:
    user_id = get_user_id(current_user, conn)
    board_id = get_or_create_board(user_id, conn)
    board = read_board(board_id, conn)
    history = get_chat_history(user_id, conn)

    try:
        client = get_ai_client()
    except ValueError:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY not configured")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": build_user_message(board, body.message)},
    ]

    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=503, detail=f"AI service error: {exc}")

    raw = completion.choices[0].message.content

    try:
        parsed = json.loads(raw)
        ai_message = str(parsed["message"])
        board_update = parsed.get("boardUpdate")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=502, detail="AI returned invalid response")

    if board_update is not None:
        try:
            columns = board_update["columns"]
            cards = board_update.get("cards", {})
            if len(columns) != 5 or {col["id"] for col in columns} != COLUMN_IDS:
                raise HTTPException(status_code=400, detail="AI returned invalid board update")
            board_dict = {
                "columns": [
                    {"id": col["id"], "title": col["title"], "cardIds": col.get("cardIds", [])}
                    for col in columns
                ],
                "cards": {
                    k: {"id": v["id"], "title": v["title"], "details": v.get("details", "")}
                    for k, v in cards.items()
                },
            }
        except (KeyError, TypeError):
            raise HTTPException(status_code=400, detail="AI returned invalid board update")
        write_board(board_id, board_dict, conn)

    append_chat_message(user_id, "user", body.message, conn)
    append_chat_message(user_id, "assistant", ai_message, conn)

    return {"message": ai_message, "boardUpdate": board_update}


@app.post("/api/ai/test")
async def ai_test(current_user: str = Depends(get_current_user)) -> dict[str, str]:
    try:
        client = get_ai_client()
    except ValueError:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY not configured")
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "What is 2+2?"}],
        )
        return {"response": completion.choices[0].message.content}
    except OpenAIError as exc:
        raise HTTPException(status_code=503, detail=f"AI service error: {exc}")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
