import { expect, test, type Page, type Route } from "@playwright/test";

const now = new Date().toISOString();
const marketId = "00000000-0000-4000-8000-000000000001";
const predictionId = "00000000-0000-4000-8000-000000000010";
const portfolioId = "00000000-0000-4000-8000-000000000020";

const market = {
  market_id: marketId,
  provider_market_id: "market-public-1",
  title: "¿Ocurrirá el evento de ejemplo?",
  description: "Un mercado público usado para explicar la experiencia.",
  category: "Ejemplos",
  resolution_at: null,
  source_created_at: now,
  status: "open",
  ingested_at: now,
  updated_at: now,
  provider: {
    provider_id: "00000000-0000-4000-8000-000000000002",
    code: "manifold",
    name: "Manifold Markets",
    enabled: true,
  },
  resolution_outcome: "unresolved",
  resolved_at: null,
  resolution_source: null,
  latest_observation: {
    observation_id: "00000000-0000-4000-8000-000000000003",
    observed_at: now,
    probability: "0.42",
    volume: "100",
    liquidity: "50",
    source_updated_at: now,
    ingested_at: now,
    provider_code: "manifold",
  },
  probability_change: "0.03",
};

const source = {
  code: "manifold",
  name: "Manifold Markets",
  status: "healthy",
  checked_at: now,
  latency_ms: 31,
  safe_error_type: null,
};

const syncRun = {
  run_id: "00000000-0000-4000-8000-000000000004",
  provider_code: "manifold",
  started_at: now,
  finished_at: now,
  status: "completed",
  markets_fetched: 1000,
  markets_created: 0,
  markets_updated: 8,
  markets_unchanged: 992,
  observations_fetched: 997,
  observations_created: 12,
  observations_duplicated: 985,
  observations_skipped: 0,
  retry_count: 0,
  duration_ms: 4200,
  safe_error_type: null,
  correlation_id: "collector-correlation",
};

const portfolio = {
  portfolio_id: portfolioId,
  name: "Autonomous Manifold paper validation [abc12345]",
  currency_unit: "MANA_SIMULATED",
  initial_balance: "100.00",
  cash_balance: "98.00",
  reserved_balance: "2.00",
  realized_pnl: "1.50",
  unrealized_pnl: "1.00",
  equity: "102.50",
  total_exposure: "2.00",
  status: "active",
  strategy_configuration_hash: "a".repeat(64),
  experiment_run_id: null,
  created_at: now,
  updated_at: now,
  simulation_only: true,
};

const automaticTrade = {
  trade_id: "00000000-0000-4000-8000-000000000030",
  order_id: "00000000-0000-4000-8000-000000000031",
  decision_id: "00000000-0000-4000-8000-000000000032",
  portfolio_id: portfolioId,
  prediction_run_id: predictionId,
  market_id: marketId,
  market_title: market.title,
  category: "Ejemplos",
  executed_at: now,
  side: "yes",
  entry_probability: "0.42",
  effective_probability: "0.43",
  units: "4.6",
  gross_cost: "1.95",
  fees: "0.01",
  slippage_cost: "0.04",
  net_cost: "2.00",
  maximum_loss: "2.00",
  potential_payout: "4.60",
  execution_model: "simulated",
  result_hash: "b".repeat(64),
  decision_reasons: ["risk:passed"],
  prediction_result_hash: "c".repeat(64),
  experiment_run_id: null,
  decision_source: "automatic",
  simulation_only: true,
  probability_is_informative: true,
};

const manualTrade = {
  ...automaticTrade,
  trade_id: "00000000-0000-4000-8000-000000000033",
  decision_id: "00000000-0000-4000-8000-000000000034",
  decision_source: "manual_override",
  side: "no",
};

const position = {
  position_id: "00000000-0000-4000-8000-000000000040",
  portfolio_id: portfolioId,
  market_id: marketId,
  market_title: market.title,
  category: "Ejemplos",
  side: "yes",
  opened_at: now,
  closed_at: null,
  status: "open",
  units: "4.6",
  average_entry_probability: "0.43",
  invested_amount: "2.00",
  current_mark_probability: "0.50",
  unrealized_pnl: "1.00",
  realized_pnl: "0.00",
  settlement_outcome: null,
  prediction_run_id: predictionId,
  trade_id: automaticTrade.trade_id,
  opportunity_level: "strong",
  entry_edge: "0.18",
  entry_confidence: "0.78",
  experiment_run_id: null,
  simulation_only: true,
  mark_is_informative: true,
};

const predictionListItem = {
  prediction_run_id: predictionId,
  market_id: marketId,
  market_title: market.title,
  provider_code: "manifold",
  category: "Ejemplos",
  predicted_at: now,
  market_probability: "0.42",
  consensus_probability: "0.67",
  consensus_confidence: "0.78",
  estimated_outcome: "yes",
  commercial_label: "actionable",
  potential_side: "buy_yes",
  gross_edge: "0.25",
  net_edge: "0.22",
  is_actionable: true,
  primary_reason: "commercial_thresholds_passed",
  portfolio_has_open_position: false,
  data_freshness_status: "fresh",
  campaign_id: "conservative-v1",
  portfolio_id: portfolioId,
};

const predictionDetail = {
  prediction_run_id: predictionId,
  experiment_run_id: null,
  market_id: marketId,
  market_title: market.title,
  category: "Ejemplos",
  predicted_at: now,
  market_probability: "0.42",
  consensus_probability: "0.67",
  consensus_confidence: "0.78",
  recommendation: "yes",
  edge: "0.25",
  no_edge: "-0.25",
  opportunity_level: "strong",
  disagreement_score: "0.05",
  status: "predicted",
  agent_configuration_hash: "d".repeat(64),
  input_hash: "e".repeat(64),
  result_hash: "f".repeat(64),
  duration_ms: "8",
  safe_error_type: null,
  abstention_reason: null,
  correlation_id: "prediction-correlation",
  causation_id: "paper-validation",
  created_at: now,
  agent_weights: {},
  agent_predictions: [],
  estimated_outcome: "yes",
  market_status: "open",
  provider_code: "manifold",
  commercial_evaluation: {
    evaluation_id: "00000000-0000-4000-8000-000000000050",
    portfolio_id: portfolioId,
    campaign_id: "conservative-v1",
    evaluated_at: now,
    estimated_outcome: "yes",
    potential_side: "buy_yes",
    market_probability: "0.42",
    consensus_probability: "0.67",
    gross_edge: "0.25",
    estimated_fees: "0.01",
    estimated_slippage: "0.02",
    estimated_other_costs: "0",
    net_edge: "0.22",
    confidence: "0.78",
    commercial_label: "actionable",
    is_actionable: true,
    reasons: ["commercial_thresholds_passed"],
    warnings: [],
    data_freshness_status: "fresh",
    portfolio_has_open_position: false,
  },
  related_executions: [],
};

type ApiFixture = {
  delayMs?: number;
  status?: number;
  markets?: object[];
  trades?: object[];
  predictions?: object[];
};

async function installApi(page: Page, fixture: ApiFixture = {}) {
  await page.route(/127\.0\.0\.1:8000\//, async (route) => {
    if (fixture.delayMs) {
      await new Promise((resolve) => setTimeout(resolve, fixture.delayMs));
    }
    if (fixture.status) {
      await route.fulfill({
        status: fixture.status,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Unavailable" }),
      });
      return;
    }
    await fulfillApiRoute(route, fixture);
  });
}

async function fulfillApiRoute(route: Route, fixture: ApiFixture) {
  const url = new URL(route.request().url());
  const path = url.pathname;
  if (path === "/markets") {
    await route.fulfill({ json: pageData(fixture.markets ?? [market]) });
    return;
  }
  if (path.endsWith("/observations")) {
    await route.fulfill({
      json: pageData([
        { ...market.latest_observation, observed_at: "2026-07-29T10:00:00Z", probability: "0.35" },
        { ...market.latest_observation, observed_at: now, probability: "0.42" },
      ]),
    });
    return;
  }
  if (path === "/sources") {
    await route.fulfill({ json: [source] });
    return;
  }
  if (path === "/collector-runs") {
    await route.fulfill({ json: pageData([syncRun]) });
    return;
  }
  if (path === "/paper-portfolios") {
    await route.fulfill({ json: pageData([portfolio]) });
    return;
  }
  if (path.endsWith("/performance")) {
    await route.fulfill({
      json: {
        portfolio,
        metrics: { net_profit: "2.50" },
        baselines: [],
        alerts: [],
        strategy_configuration_hash: portfolio.strategy_configuration_hash,
        simulation_only: true,
        disclaimer: "Simulado",
      },
    });
    return;
  }
  if (path.endsWith("/equity-curve")) {
    await route.fulfill({
      json: [
        { recorded_at: "2026-07-29T10:00:00Z", equity: "100.00" },
        { recorded_at: now, equity: "102.50" },
      ],
    });
    return;
  }
  if (path === "/paper-trades") {
    await route.fulfill({
      json: pageData(fixture.trades ?? [automaticTrade, manualTrade]),
    });
    return;
  }
  if (path === "/paper-positions") {
    await route.fulfill({ json: pageData([position]) });
    return;
  }
  if (path === "/predictions" && route.request().method() === "GET") {
    const items = fixture.predictions ?? [predictionListItem];
    await route.fulfill({
      json: {
        items,
        page: 1,
        page_size: 25,
        total_items: items.length,
        total_pages: 1,
        applied_filters: {},
      },
    });
    return;
  }
  if (path === `/predictions/${predictionId}`) {
    await route.fulfill({ json: predictionDetail });
    return;
  }
  if (path === "/paper-trading/manual-trades") {
    await route.fulfill({
      json: {
        status: "filled",
        trade_decision_id: "00000000-0000-4000-8000-000000000060",
        paper_order_id: "00000000-0000-4000-8000-000000000061",
        paper_trade_id: "00000000-0000-4000-8000-000000000062",
        position_id: "00000000-0000-4000-8000-000000000063",
        portfolio_id: portfolioId,
        side: "yes",
        rejection_reasons: [],
        decision_source: "manual_override",
        simulation_only: true,
        disclaimer: "Simulado",
      },
    });
    return;
  }
  await route.fulfill({ json: pageData([]) });
}

function pageData(items: object[]) {
  return { items, page: 1, page_size: 100, total: items.length, pages: items.length ? 1 : 0 };
}

test("shows a simple executive overview with only four navigation choices", async ({ page }) => {
  await installApi(page, { trades: [automaticTrade] });
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "El laboratorio está trabajando por vos" }),
  ).toBeVisible();
  await expect(page.getByText("+2,50").first()).toBeVisible();
  await expect(page.getByText("Operaciones automáticas")).toBeVisible();
  await expect(page.getByText("Mercados observados")).toBeVisible();
  await expect(page.locator("header nav").getByRole("link")).toHaveCount(4);

  const visible = await page.locator("main").innerText();
  expect(visible).not.toMatch(/hash|correlation|collector|snapshot|drawdown|edge/i);
  expect(visible).toContain("100% simulado");
});

test("keeps the executive overview inside a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installApi(page, { trades: [automaticTrade] });
  await page.goto("/");

  await expect(page.getByText("+2,50").first()).toBeVisible();
  const viewport = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    contentWidth: document.documentElement.scrollWidth,
  }));
  expect(viewport.contentWidth).toBeLessThanOrEqual(viewport.width);

  await page.getByRole("button", { name: "Abrir menú" }).click();
  await expect(page.locator("header nav").getByRole("link")).toHaveCount(4);
});

test("explains automatic and manual activity without technical details", async ({ page }) => {
  await installApi(page);
  await page.goto("/trades");

  await expect(page.getByRole("heading", { name: "Qué hizo el sistema" })).toBeVisible();
  await expect(page.locator("article").getByText("Automática", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Manual", exact: true }).click();
  await expect(page.getByText("Manual", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("Capital usado")).toBeVisible();
});

test("shows opportunities, lazy detail and the optional manual simulation", async ({ page }) => {
  await installApi(page);
  await page.goto("/predictions");

  await expect(
    page.getByRole("heading", { name: "Oportunidades que encontró el sistema" }),
  ).toBeVisible();
  await expect(page.getByText("El mercado dice")).toBeVisible();
  await expect(page.getByText("El sistema estima")).toBeVisible();
  await expect(page.getByText("Hay oportunidad")).toBeVisible();

  await page.getByRole("link", { name: "Entender" }).click();
  await expect(page).toHaveURL(new RegExp(`/predictions/${predictionId}$`));
  await expect(page.getByText("En palabras simples")).toBeVisible();
  await expect(page.getByText("El sistema detectó una oportunidad")).toBeVisible();

  await page.getByRole("button", { name: "Simular manualmente" }).click();
  await expect(page.getByRole("heading", { name: "Probá tu propia decisión" })).toBeVisible();
  await page.getByLabel("¿Por qué querés probarlo?").fill("Quiero comparar mi hipótesis.");
  await page.getByRole("button", { name: "Confirmar simulación" }).click();
  await expect(page.getByText("La prueba simulada fue creada.")).toBeVisible();
});

test("lets an executive search markets and open a plain-language detail", async ({ page }) => {
  await installApi(page);
  await page.goto("/markets");

  await expect(page.getByRole("heading", { name: "Mercados observados" })).toBeVisible();
  await page.getByPlaceholder("Buscar un mercado").fill("evento de ejemplo");
  await page.getByText(market.title).click();
  await expect(page).toHaveURL(new RegExp(`/markets/${marketId}$`));
  await expect(page.getByText("Cómo cambió la opinión del mercado")).toBeVisible();
  await expect(page.getByText("42%").first()).toBeVisible();
});

test("switches the redesigned experience to English", async ({ page }) => {
  await installApi(page, { trades: [automaticTrade] });
  await page.goto("/");

  await page.getByRole("button", { name: "Idioma" }).click();

  await expect(
    page.getByRole("heading", { name: "The laboratory is working for you" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Opportunities", exact: true })).toBeVisible();
  await expect(page.getByText("100% simulated")).toBeVisible();
});

test("uses clear loading, empty and error states", async ({ page }) => {
  await installApi(page, { delayMs: 700 });
  await page.goto("/");
  await expect(page.getByLabel("Cargando información")).toBeVisible();
});

test("shows a recoverable executive error", async ({ page }) => {
  await installApi(page, { status: 503 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "No pudimos actualizar el resumen" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
});
