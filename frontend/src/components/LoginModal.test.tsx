import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginModal } from "@/components/LoginModal";

describe("LoginModal", () => {
  it("renders username and password fields with a submit button", () => {
    render(<LoginModal onLogin={vi.fn()} />);
    expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls onLogin with username on successful login", async () => {
    const onLogin = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ username: "user" }),
      })
    );

    render(<LoginModal onLogin={onLogin} />);
    await userEvent.type(screen.getByPlaceholderText("Username"), "user");
    await userEvent.type(screen.getByPlaceholderText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(onLogin).toHaveBeenCalledWith("user");
    vi.unstubAllGlobals();
  });

  it("shows error message on invalid credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Invalid credentials" }),
      })
    );

    render(<LoginModal onLogin={vi.fn()} />);
    await userEvent.type(screen.getByPlaceholderText("Username"), "user");
    await userEvent.type(screen.getByPlaceholderText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Invalid credentials.")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
