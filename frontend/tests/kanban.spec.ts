import { expect, test } from "@playwright/test";

const useIntegrated =
  process.env.E2E_MODE === "integrated" || process.env.CI === "true";

const DEV_MOCK_BOARD = {
  columns: [
    { id: "col-backlog",   title: "Backlog",     cardIds: ["card-1"] },
    { id: "col-discovery", title: "Discovery",   cardIds: [] },
    { id: "col-progress",  title: "In Progress", cardIds: [] },
    { id: "col-review",    title: "Review",      cardIds: [] },
    { id: "col-done",      title: "Done",        cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Test card", details: "Test details" },
  },
};

async function loginViaModal(page: Parameters<Parameters<typeof test>[1]>[0]) {
  await page.getByPlaceholder("Username").fill("user");
  await page.getByPlaceholder("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
}

async function mockDevMode(page: Parameters<Parameters<typeof test>[1]>[0]) {
  await page.route("/api/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ username: "user" }),
    })
  );
  await page.route("/api/board", (route) => {
    if (route.request().method() === "PUT") {
      route.fulfill({ status: 204 });
    } else {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(DEV_MOCK_BOARD),
      });
    }
  });
  await page.goto("/");
}

test.describe("board (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    if (useIntegrated) {
      await page.goto("/");
      await loginViaModal(page);
    } else {
      await mockDevMode(page);
    }
  });

  test("loads the kanban board", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
    await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
  });

  test("adds a card to a column", async ({ page }) => {
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    await firstColumn.getByRole("button", { name: /add a card/i }).click();
    await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
    await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
    await firstColumn.getByRole("button", { name: /add card/i }).click();
    await expect(firstColumn.getByText("Playwright card")).toBeVisible();
  });

  test("moves a card between columns", async ({ page }) => {
    const card = page.getByTestId("card-card-1");
    const targetColumn = page.getByTestId("column-col-review");
    const cardBox = await card.boundingBox();
    const columnBox = await targetColumn.boundingBox();
    if (!cardBox || !columnBox) {
      throw new Error("Unable to resolve drag coordinates.");
    }

    await page.mouse.move(
      cardBox.x + cardBox.width / 2,
      cardBox.y + cardBox.height / 2
    );
    await page.mouse.down();
    await page.mouse.move(
      columnBox.x + columnBox.width / 2,
      columnBox.y + 120,
      { steps: 12 }
    );
    await page.mouse.up();
    await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
  });
});

test.describe("auth flow", () => {
  test("unauthenticated visit shows login modal", async ({ page }) => {
    test.skip(!useIntegrated, "Requires backend - run with E2E_MODE=integrated");
    await page.goto("/");
    await expect(page.getByPlaceholder("Username")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
  });

  test("login reveals board and logout returns to modal", async ({ page }) => {
    test.skip(!useIntegrated, "Requires backend - run with E2E_MODE=integrated");
    await page.goto("/");
    await loginViaModal(page);
    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page.getByPlaceholder("Username")).toBeVisible();
  });
});

test.describe("AI chat sidebar", () => {
  const CHAT_BOARD = {
    columns: [
      { id: "col-backlog",   title: "Backlog",     cardIds: ["card-ai"] },
      { id: "col-discovery", title: "Discovery",   cardIds: [] },
      { id: "col-progress",  title: "In Progress", cardIds: [] },
      { id: "col-review",    title: "Review",      cardIds: [] },
      { id: "col-done",      title: "Done",        cardIds: [] },
    ],
    cards: { "card-ai": { id: "card-ai", title: "AI created card", details: "" } },
  };

  test.beforeEach(async ({ page }) => {
    if (useIntegrated) {
      await page.goto("/");
      await loginViaModal(page);
    } else {
      await page.route("/api/auth/me", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ username: "user" }),
        })
      );
      await page.route("/api/board", (route) => {
        if (route.request().method() === "PUT") {
          route.fulfill({ status: 204 });
        } else {
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(DEV_MOCK_BOARD),
          });
        }
      });
      await page.goto("/");
    }
  });

  test("sends a message and sees AI response in chat", async ({ page }) => {
    await page.route("/api/ai/chat", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: "Got it!", boardUpdate: null }),
      })
    );

    await page.getByPlaceholder("Ask the AI...").fill("Hello AI");
    await page.getByRole("button", { name: /send/i }).click();

    await expect(page.getByText("Hello AI")).toBeVisible();
    await expect(page.getByText("Got it!")).toBeVisible();
  });

  test("AI board update appears on the board without reload", async ({ page }) => {
    test.skip(useIntegrated, "Uses route mock; integrated smoke test is manual");

    await page.route("/api/ai/chat", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: "Added a card", boardUpdate: CHAT_BOARD }),
      })
    );

    await page.getByPlaceholder("Ask the AI...").fill("Add a card");
    await page.getByRole("button", { name: /send/i }).click();

    await expect(page.getByText("Added a card")).toBeVisible();
    await expect(page.getByText("AI created card")).toBeVisible();
  });
});

test.describe("persistence", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!useIntegrated, "Requires backend - run with E2E_MODE=integrated");
    await page.goto("/");
    await loginViaModal(page);
  });

  test("added card persists after page reload", async ({ page }) => {
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    await firstColumn.getByRole("button", { name: /add a card/i }).click();
    await firstColumn.getByPlaceholder("Card title").fill("Persisted card");
    const putDone = page.waitForResponse(
      (r) => r.url().includes("/api/board") && r.request().method() === "PUT"
    );
    await firstColumn.getByRole("button", { name: /add card/i }).click();
    await putDone;

    await page.reload();
    await expect(page.getByText("Persisted card")).toBeVisible();
  });

  test("renamed column title persists after page reload", async ({ page }) => {
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const input = firstColumn.getByLabel("Column title");
    const putDone = page.waitForResponse(
      (r) => r.url().includes("/api/board") && r.request().method() === "PUT"
    );
    await input.fill("Renamed Column");
    await putDone;

    await page.reload();
    await expect(
      page.locator('[data-testid^="column-"]').first().getByLabel("Column title")
    ).toHaveValue("Renamed Column");
  });

  test("card position persists after drag and reload", async ({ page }) => {
    // Add a card first
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    await firstColumn.getByRole("button", { name: /add a card/i }).click();
    await firstColumn.getByPlaceholder("Card title").fill("Drag me");
    let putDone = page.waitForResponse(
      (r) => r.url().includes("/api/board") && r.request().method() === "PUT"
    );
    await firstColumn.getByRole("button", { name: /add card/i }).click();
    await putDone;

    // Drag the card to the review column
    const card = page.getByText("Drag me");
    const targetColumn = page.getByTestId("column-col-review");
    const cardBox = await card.boundingBox();
    const columnBox = await targetColumn.boundingBox();
    if (!cardBox || !columnBox) throw new Error("Unable to resolve drag coordinates.");

    putDone = page.waitForResponse(
      (r) => r.url().includes("/api/board") && r.request().method() === "PUT"
    );
    await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(columnBox.x + columnBox.width / 2, columnBox.y + 120, { steps: 12 });
    await page.mouse.up();
    await putDone;

    await page.reload();
    await expect(page.getByTestId("column-col-review").getByText("Drag me")).toBeVisible();
  });
});
