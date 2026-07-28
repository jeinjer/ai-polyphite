import { expect, test } from "@playwright/test";

const LIVE_STACK_ENABLED = process.env.AI_POLYPHITE_LIVE_STACK === "true";
const API_ORIGIN = new URL(
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
).origin;
const DASHBOARD_ENDPOINTS = [
  "/markets",
  "/predictions",
  "/sources",
  "/collector-runs",
  "/experiment-runs",
  "/replay-datasets",
] as const;

test.describe("live Docker stack", () => {
  test.skip(
    !LIVE_STACK_ENABLED,
    "Set AI_POLYPHITE_LIVE_STACK=true to validate the rebuilt local stack.",
  );

  test("loads real API data through browser CORS", async ({ page }) => {
    const responses = DASHBOARD_ENDPOINTS.map((endpoint) =>
      page.waitForResponse((response) => {
        const url = new URL(response.url());
        return (
          url.origin === API_ORIGIN &&
          url.pathname === endpoint &&
          response.status() === 200
        );
      }),
    );

    await page.goto("/");
    const completed = await Promise.all(responses);

    for (const response of completed) {
      expect(response.headers()["access-control-allow-origin"]).toBe(
        "http://127.0.0.1:3000",
      );
    }

    const marketsResponse = completed[DASHBOARD_ENDPOINTS.indexOf("/markets")];
    const markets = (await marketsResponse.json()) as {
      items: { title: string }[];
    };

    await expect(
      page.getByRole("heading", {
        name: "No pudimos cargar la información",
      }),
    ).toHaveCount(0);
    if (markets.items[0]) {
      await page.getByRole("button", { name: "Mercados", exact: true }).click();
      await expect(page.getByText(markets.items[0].title).first()).toBeVisible();
    } else {
      await page.getByRole("button", { name: "Mercados", exact: true }).click();
      await expect(
        page.getByText("Todavía no hay mercados disponibles."),
      ).toBeVisible();
    }
  });
});
