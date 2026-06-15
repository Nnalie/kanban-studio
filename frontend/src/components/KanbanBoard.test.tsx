import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

const BLANK_BOARD = {
  columns: [
    { id: "col-backlog",   title: "Backlog",     cardIds: [] },
    { id: "col-discovery", title: "Discovery",   cardIds: [] },
    { id: "col-progress",  title: "In Progress", cardIds: [] },
    { id: "col-review",    title: "Review",      cardIds: [] },
    { id: "col-done",      title: "Done",        cardIds: [] },
  ],
  cards: {},
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        return Promise.resolve({ ok: true, status: 204 });
      }
      return Promise.resolve({ ok: true, json: async () => BLANK_BOARD });
    })
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("KanbanBoard", () => {
  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const columns = await screen.findAllByTestId(/column-/i);
    const input = within(columns[0]).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const columns = await screen.findAllByTestId(/column-/i);
    const column = columns[0];

    await userEvent.click(
      within(column).getByRole("button", { name: /add a card/i })
    );
    await userEvent.type(
      within(column).getByPlaceholderText(/card title/i),
      "New card"
    );
    await userEvent.type(
      within(column).getByPlaceholderText(/details/i),
      "Notes"
    );
    await userEvent.click(
      within(column).getByRole("button", { name: /add card/i })
    );

    expect(within(column).getByText("New card")).toBeInTheDocument();

    await userEvent.click(
      within(column).getByRole("button", { name: /delete new card/i })
    );

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
