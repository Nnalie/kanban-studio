import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatSidebar } from "@/components/ChatSidebar";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ChatSidebar", () => {
  it("renders with empty-state placeholder", () => {
    render(<ChatSidebar onBoardUpdate={vi.fn()} />);
    expect(screen.getByText(/ask me to add, move/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ask the AI/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("sends a message and displays user and assistant messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ message: "Hello back!", boardUpdate: null }),
      })
    );

    render(<ChatSidebar onBoardUpdate={vi.fn()} />);
    await userEvent.type(screen.getByPlaceholderText(/ask the AI/i), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(await screen.findByText("Hello back!")).toBeInTheDocument();
  });

  it("calls onBoardUpdate when boardUpdate is returned", async () => {
    const mockBoard = {
      columns: [
        { id: "col-backlog",   title: "Backlog",     cardIds: ["card-ai"] },
        { id: "col-discovery", title: "Discovery",   cardIds: [] },
        { id: "col-progress",  title: "In Progress", cardIds: [] },
        { id: "col-review",    title: "Review",      cardIds: [] },
        { id: "col-done",      title: "Done",        cardIds: [] },
      ],
      cards: { "card-ai": { id: "card-ai", title: "AI card", details: "" } },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ message: "Added a card", boardUpdate: mockBoard }),
      })
    );

    const onBoardUpdate = vi.fn();
    render(<ChatSidebar onBoardUpdate={onBoardUpdate} />);
    await userEvent.type(screen.getByPlaceholderText(/ask the AI/i), "Add a card");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => expect(onBoardUpdate).toHaveBeenCalledWith(mockBoard));
  });

  it("shows error message on failed request", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 })
    );

    render(<ChatSidebar onBoardUpdate={vi.fn()} />);
    await userEvent.type(screen.getByPlaceholderText(/ask the AI/i), "Test");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText(/failed to get a response/i)).toBeInTheDocument();
  });
});
