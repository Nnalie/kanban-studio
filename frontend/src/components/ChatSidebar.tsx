"use client";

import { useRef, useState } from "react";
import { sendChatMessage } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

interface Message {
  role: "user" | "assistant";
  text: string;
}

interface Props {
  onBoardUpdate: (board: BoardData) => void;
}

export const ChatSidebar = ({ onBoardUpdate }: Props) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const result = await sendChatMessage(text);
      setMessages((prev) => [...prev, { role: "assistant", text: result.message }]);
      if (result.boardUpdate) {
        onBoardUpdate(result.boardUpdate);
      }
    } catch {
      setError("Failed to get a response. Please try again.");
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <aside
      data-testid="chat-sidebar"
      className="flex h-screen w-80 flex-shrink-0 flex-col border-l border-[var(--stroke)] bg-white/90 sticky top-0 backdrop-blur"
    >
      <div className="border-b border-[var(--stroke)] px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
          AI Assistant
        </p>
        <h2 className="mt-1 font-display text-lg font-semibold text-[var(--navy-dark)]">
          Chat
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && !loading && (
          <p className="text-sm text-[var(--gray-text)]">
            Ask me to add, move, or edit cards on your board.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`rounded-xl px-4 py-3 text-sm leading-6 ${
              msg.role === "user"
                ? "ml-4 bg-[var(--navy-dark)] text-white"
                : "mr-4 border border-[var(--stroke)] bg-[var(--surface)] text-[var(--navy-dark)]"
            }`}
          >
            {msg.text}
          </div>
        ))}
        {loading && (
          <div className="mr-4 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--gray-text)]">
            Thinking...
          </div>
        )}
        {error && (
          <p className="px-1 text-xs text-red-500">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[var(--stroke)] p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the AI..."
            rows={2}
            disabled={loading}
            className="flex-1 resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] placeholder:text-[var(--gray-text)] focus:border-[var(--primary-blue)] focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="self-end rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </aside>
  );
};
