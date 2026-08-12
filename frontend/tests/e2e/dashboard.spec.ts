import { expect, test, type Page, type Route } from "@playwright/test";

const now = new Date().toISOString();
const portfolioId = "00000000-0000-4000-8000-000000000100";
const predictionId = "00000000-0000-4000-8000-000000000200";

const portfolio = {
  portfolio_id: portfolioId,
  name: "Autonomous Manifold paper validation [test]",
  currency_unit: "MANA_SIMULATED",
  initial_balance: "100.00",
  cash_balance: "84.50",
  reserved_balance: "15.50",
  realized_pnl: "1.20",
  unrealized_pnl: "-0.30",
  equity: "100.90",
  total_exposure: "15.50",
  status: "active",
  strategy_configuration_hash: "a".repeat(64),
  experiment_run_id: null,
  created_at: now,
  updated_at: now,
  simulation_only: true,
};

const prediction = {
  prediction_run_id: predictionId,
  market_id: "00000000-0000-4000-8000-000000000300",
  market_title: "Will the public event happen this week?",
  provider_code: "manifold",
  category: null,
  predicted_at: now,
  market_probability: "0.5400000000",
  consensus_probability: "0.6300000000",
  consensus_confidence: "0.6800000000",
  estimated_outcome: "yes",
  commercial_label: "actionable",
  potential_side: "buy_yes",
  gross_edge: "0.0900000000",
  net_edge: "0.0750000000",
  is_actionable: true,
  primary_reason: "commercial_edge_available",
  portfolio_has_open_position: false,
  data_freshness_status: "fresh",
  campaign_id: "conservative-v1",
  portfolio_id: portfolioId,
};

const trade = {
  trade_id: "00000000-0000-4000-8000-000000000400",
  order_id: "00000000-0000-4000-8000-000000000401",
  decision_id: "00000000-0000-4000-8000-000000000402",
  portfolio_id: portfolioId,
  prediction_run_id: predictionId,
  market_id: prediction.market_id,
  market_title: prediction.market_title,
  category: null,
  executed_at: now,
  side: "yes",
  entry_probability: "0.54",
  effective_probability: "0.55",
  units: "1.8",
  gross_cost: "1.00",
  fees: "0.01",
  slippage_cost: "0.01",
  net_cost: "1.02",
  maximum_loss: "1.02",
  potential_payout: "1.80",
  execution_model: "informative_probability",
  result_hash: "b".repeat(64),
  decision_reasons: [],
  prediction_result_hash: "c".repeat(64),
  experiment_run_id: null,
  decision_source: "automatic",
  simulation_only: true,
  probability_is_informative: true,
};

const position = {
  position_id: "00000000-0000-4000-8000-000000000500",
  portfolio_id: portfolioId,
  market_id: prediction.market_id,
  market_title: prediction.market_title,
  category: null,
  side: "yes",
  opened_at: now,
  closed_at: null,
  status: "open",
  units: "1.8",
  average_entry_probability: "0.55",
  invested_amount: "1.02",
  current_mark_probability: "0.56",
  unrealized_pnl: "0.02",
  realized_pnl: "0",
  settlement_outcome: null,
  prediction_run_id: predictionId,
  trade_id: trade.trade_id,
  opportunity_level: "weak",
  entry_edge: "0.09",
  entry_confidence: "0.68",
  experiment_run_id: null,
  simulation_only: true,
  mark_is_informative: true,
};

function pageData<T>(items: T[]) {
  return { items, page: 1, page_size: 100, total: items.length, pages: 1 };
}

async function mockApi(page: Page) {
  let paused = false;
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path === "/sources") return json(route, [{ code: "manifold", name: "Manifold Markets", status: "healthy", checked_at: now, latency_ms: 12, safe_error_type: null }]);
    if (path === "/collector-runs") return json(route, pageData([{ run_id: "run-1", provider_code: "manifold", started_at: now, finished_at: now, status: "completed", markets_fetched: 300, markets_created: 2, markets_updated: 18, markets_unchanged: 280, observations_fetched: 300, observations_created: 20, observations_duplicated: 280, observations_skipped: 0, retry_count: 0, duration_ms: 900, safe_error_type: null, correlation_id: "test" }]));
    if (path === "/paper-portfolios") return json(route, pageData([portfolio]));
    if (path === `/paper-portfolios/${portfolioId}/performance`) return json(route, { portfolio, metrics: { evidence_state: "insufficient_sample", net_profit: "0.90", open_trade_count: 1 }, baselines: [], alerts: [], strategy_configuration_hash: "a".repeat(64), simulation_only: true, disclaimer: "paper" });
    if (path === `/paper-portfolios/${portfolioId}/equity-curve`) return json(route, [{ recorded_at: "2026-08-11T14:30:00Z", equity: "100.00", drawdown: "0", exposure: "0", realized_pnl: "0", unrealized_pnl: "0", cumulative_costs: "0", result_hash: "a".repeat(64), valuation_is_simulated: true }, { recorded_at: now, equity: "100.90", drawdown: "0", exposure: "15.5", realized_pnl: "1.2", unrealized_pnl: "-0.3", cumulative_costs: "0.1", result_hash: "b".repeat(64), valuation_is_simulated: true }]);
    if (path === "/paper-trades") return json(route, pageData([trade]));
    if (path === "/paper-positions") return json(route, pageData([position]));
    if (path === "/prediction-evaluation") return json(route, { experiment_run_id: null, resolved_count: 24, emitted_count: 24, abstained_count: 0, coverage: "1", system: { brier_score: "0.18", log_loss: "0.5", absolute_error: "0.3", directional_accuracy: "0.7" }, market_baseline: { brier_score: "0.17", log_loss: "0.49", absolute_error: "0.29", directional_accuracy: "0.7" }, constant_baseline: null, calibration: [] });
    if (path === "/automation") {
      if (request.method() === "GET") return json(route, { paused, updated_at: null, reason: null, simulation_only: true });
    }
    if (path === "/automation/pause") { paused = true; return json(route, { paused, updated_at: now, reason: "Pausa solicitada desde el dashboard.", simulation_only: true }); }
    if (path === "/automation/resume") { paused = false; return json(route, { paused, updated_at: now, reason: null, simulation_only: true }); }
    if (path === `/predictions/${predictionId}`) return json(route, { ...prediction, experiment_run_id: null, status: "predicted", recommendation: "yes", edge: "0.09", no_edge: "-0.09", opportunity_level: "moderate", disagreement_score: "0.05", agent_configuration_hash: "a".repeat(64), input_hash: "b".repeat(64), result_hash: "c".repeat(64), duration_ms: "1200", safe_error_type: null, abstention_reason: null, correlation_id: "test", causation_id: null, created_at: now, agent_weights: {}, market_status: "open", agent_predictions: [{ agent_prediction_id: "agent-1", agent_name: "reasoning", agent_version: "2.0.0", predicted_probability: "0.66", confidence: "0.7", recommendation: "yes", rationale_summary: "Contrato público, verificable y de corto plazo.", evidence: [], warnings: [], input_hash: "a".repeat(64), output_hash: "b".repeat(64), duration_ms: "900", disagreement_score: null, agent_weights: {} }, { agent_prediction_id: "agent-2", agent_name: "market", agent_version: "1.0.0", predicted_probability: "0.60", confidence: "0.6", recommendation: "yes", rationale_summary: "Tendencia reciente moderada.", evidence: [], warnings: [], input_hash: "a".repeat(64), output_hash: "c".repeat(64), duration_ms: "1", disagreement_score: null, agent_weights: {} }], commercial_evaluation: { evaluation_id: "eval-1", portfolio_id: portfolioId, campaign_id: "conservative-v1", evaluated_at: now, estimated_outcome: "yes", potential_side: "buy_yes", market_probability: "0.54", consensus_probability: "0.63", gross_edge: "0.09", estimated_fees: "0.005", estimated_slippage: "0.01", estimated_other_costs: "0", net_edge: "0.075", confidence: "0.68", commercial_label: "actionable", is_actionable: true, reasons: ["commercial_edge_available"], warnings: [], data_freshness_status: "fresh", portfolio_has_open_position: false }, related_executions: [] });
    if (path === "/predictions") {
      const actionable = url.searchParams.get("commercial_label") === "actionable";
      return json(route, { items: [prediction], page: 1, page_size: 25, total_items: actionable ? 1 : 4, total_pages: 1, applied_filters: {} });
    }
    return route.abort("failed");
  });
}

async function json(route: Route, body: unknown) {
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("shows a compact executive overview and only three navigation choices", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("aside nav").getByRole("link")).toHaveCount(3);
  await expect(page.getByText("El sistema está trabajando")).toBeVisible();
  await expect(page.getByText("Invertido", { exact: true })).toBeVisible();
  await expect(page.getByText("Disponible", { exact: true })).toBeVisible();
  await expect(page.getByText("Ganancia / pérdida", { exact: true })).toBeVisible();
  await expect(page.getByText("Total actual", { exact: true })).toBeVisible();
  await expect(page.getByText("15,50 créditos", { exact: true })).toBeVisible();
  await expect(page.getByText("84,50 créditos", { exact: true })).toBeVisible();
  await expect(page.getByText("100,90 créditos", { exact: true })).toBeVisible();
  await expect(page.getByText("Analizadas", { exact: true })).toBeVisible();
  await expect(page.getByText("Sin estimación", { exact: true })).toBeVisible();
  await expect(page.getByText("Descartadas", { exact: true })).toBeVisible();
  await expect(page.getByText("Operadas", { exact: true })).toBeVisible();
  await expect(page.getByText("Mercados resueltos")).toBeVisible();
  await expect(page.getByText("Todavía no hay evidencia suficiente")).toBeVisible();
});

test("updates the current time after hydration and keeps it live", async ({ page }) => {
  await page.goto("/");
  await page.clock.install({ time: new Date("2030-01-01T12:34:00Z") });
  await page.clock.fastForward(30_000);
  const currentTime = page.getByText(/Ahora · hora del equipo/).locator("..").locator("strong");
  await expect(currentTime).toContainText("01:34:30 p. m.");
  await page.clock.fastForward(1_000);
  await expect(currentTime).toContainText("01:34:31 p. m.");
});

test("lists predictions without manual controls and loads debate only on detail", async ({ page }) => {
  await page.goto("/predictions");
  await expect(page.getByText(prediction.market_title)).toBeVisible();
  await expect(page.locator(".status-good").filter({ hasText: "Conviene" })).toBeVisible();
  await expect(page.getByText("Simular manualmente")).toHaveCount(0);
  await page.getByLabel("Orden").selectOption("consensus_probability");
  await expect(page).toHaveURL(/sort=consensus_probability/);
  await page.getByText(prediction.market_title).click();
  await expect(page).toHaveURL(new RegExp(`/predictions/${predictionId}$`));
  await expect(page.getByText("Debate de agentes")).toBeVisible();
  await expect(page.getByText("Análisis semántico")).toBeVisible();
});

test("shows only automatic paper activity", async ({ page }) => {
  await page.goto("/trades");
  await expect(page.getByText("Registro automático")).toBeVisible();
  await expect(page.getByText(prediction.market_title)).toBeVisible();
  await expect(page.getByText("Esperando resultado")).toBeVisible();
  await expect(page.getByRole("button", { name: /manual/i })).toHaveCount(0);
});

test("can pause future automatic operations after confirmation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Pausar automatización" }).click();
  await expect(page.getByText("¿Pausar nuevas operaciones?")).toBeVisible();
  await page.getByRole("button", { name: "Pausar", exact: true }).click();
  await expect(page.getByRole("button", { name: "Reanudar automatización" })).toBeVisible();
});

test("switches between light and dark theme", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cambiar tema" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
