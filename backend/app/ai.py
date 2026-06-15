import json
import os

from openai import AsyncOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-oss-120b:free"

SYSTEM_PROMPT = """\
You are an AI assistant that helps manage a Kanban board.

Respond ONLY with valid JSON in exactly this format:
{
  "message": "<your reply to the user>",
  "boardUpdate": <full board JSON if you changed the board, or null if unchanged>
}

Board structure:
{
  "columns": [{"id": "...", "title": "...", "cardIds": ["card-id-1", ...]}],
  "cards": {"card-id-1": {"id": "card-id-1", "title": "...", "details": "..."}}
}

Rules:
- The five column IDs are fixed and must always be present: col-backlog, col-discovery, col-progress, col-review, col-done
- Card IDs must be unique strings (e.g. "card-abc123"). Generate a new unique ID for each new card.
- If you add, move, edit, or delete cards, include the full updated board in boardUpdate.
- If you only answer a question or chat without modifying the board, set boardUpdate to null.
- Always include all five columns in boardUpdate even if some are unchanged.\
"""


def get_ai_client() -> AsyncOpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    return AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)


def build_user_message(board: dict, user_message: str) -> str:
    return f"[Board state: {json.dumps(board)}]\n\n{user_message}"
