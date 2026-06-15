import type { BoardData } from "@/lib/kanban";

export async function getBoard(): Promise<BoardData> {
  const res = await fetch("/api/board", { credentials: "include" });
  if (!res.ok) throw new Error(`GET /api/board ${res.status}`);
  return res.json();
}

export async function putBoard(board: BoardData): Promise<void> {
  await fetch("/api/board", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(board),
    credentials: "include",
  });
}

export async function sendChatMessage(
  message: string
): Promise<{ message: string; boardUpdate: BoardData | null }> {
  const res = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    credentials: "include",
  });
  if (!res.ok) throw new Error(`POST /api/ai/chat ${res.status}`);
  return res.json();
}
