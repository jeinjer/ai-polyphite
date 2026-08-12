import { expect, test } from "@playwright/test";

const LIVE_STACK_ENABLED = process.env.AI_POLYPHITE_LIVE_STACK === "true";
const API_ORIGIN = new URL(
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
).origin;
const DASHBOARD_ENDPOINTS = [
  "/sources",
  "/collector-runs",
  "/paper-portfolios",
  "/automation",
  "/prediction-evaluation",
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

    await expect(
      page.getByRole("heading", { name: "No se pudo cargar el tablero" }),
    ).toHaveCount(0);
    await expect(page.getByText("Estado general")).toBeVisible();

    const predictionResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return (
        url.origin === API_ORIGIN &&
        url.pathname === "/predictions" &&
        response.status() === 200
      );
    });
    await page.goto("/predictions");
    expect(
      (await predictionResponse).headers()["access-control-allow-origin"],
    ).toBe("http://127.0.0.1:3000");
  });
});
