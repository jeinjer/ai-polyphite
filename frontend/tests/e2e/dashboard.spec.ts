import { expect, test, type Page, type Route } from "@playwright/test";

const now = new Date().toISOString();

const market = {
  market_id: "00000000-0000-4000-8000-000000000001",
  provider_market_id: "external-1",
  title: "¿Ocurrirá el evento de ejemplo?",
  description: "Mercado sanitizado para comprobar la interfaz.",
  category: "ejemplos",
  resolution_at: null,
  source_created_at: now,
  status: "open",
  ingested_at: now,
  updated_at: now,
  provider: {
    provider_id: "00000000-0000-4000-8000-000000000010",
    code: "mock",
    name: "Fuente simulada",
    enabled: true,
  },
  resolution_outcome: "unresolved",
  resolved_at: null,
  resolution_source: null,
  latest_observation: {
    observation_id: "00000000-0000-4000-8000-000000000020",
    observed_at: now,
    probability: "0.6250000000",
    volume: "120.50000000",
    liquidity: null,
    source_updated_at: now,
    ingested_at: now,
    provider_code: "mock",
  },
  probability_change: "0.0250000000",
};

const secondMarket = {
  ...market,
  market_id: "00000000-0000-4000-8000-000000000002",
  provider_market_id: "external-2",
  title: "Segundo mercado",
  latest_observation: {
    ...market.latest_observation,
    observation_id: "00000000-0000-4000-8000-000000000021",
    probability: "0.4000000000",
  },
  probability_change: "-0.1000000000",
};

const observation = market.latest_observation;
const historyEvent = {
  event_id: "observation:00000000-0000-4000-8000-000000000020",
  event_type: "observation",
  occurred_at: now,
  previous_status: null,
  status: null,
  resolution_outcome: null,
  probability: "0.6250000000",
  volume: "120.50000000",
  liquidity: null,
  source: "mock",
};

const source = {
  code: "mock",
  name: "Fuente simulada",
  status: "healthy",
  checked_at: now,
  latency_ms: 1.2,
  safe_error_type: null,
};

const syncRun = {
  run_id: "00000000-0000-4000-8000-000000000030",
  provider_code: "mock",
  started_at: now,
  finished_at: now,
  status: "completed",
  markets_fetched: 2,
  markets_created: 2,
  markets_updated: 0,
  markets_unchanged: 0,
  observations_fetched: 2,
  observations_created: 2,
  observations_duplicated: 0,
  observations_skipped: 0,
  retry_count: 0,
  duration_ms: 12.5,
  safe_error_type: null,
  correlation_id: "test-correlation",
};

const replayDataset = {
  dataset_id: "synthetic-lab",
  version: "1.0.0",
  schema_version: "1",
  created_at: now,
  description: "Dataset sintético y controlado.",
  content_sha256: "a".repeat(64),
  replay_start: now,
  replay_end: now,
  market_count: 20,
  observation_count: 80,
};

const experimentRun = {
  experiment_run_id: "00000000-0000-4000-8000-000000000040",
  dataset_id: "synthetic-lab",
  dataset_version: "1.0.0",
  started_at: now,
  finished_at: now,
  status: "completed",
  replay_start: now,
  replay_end: now,
  random_seed: 0,
  configuration_hash: "b".repeat(64),
  code_version: "test",
  result_hash: "c".repeat(64),
  correlation_id: "experiment-correlation",
  safe_error_type: null,
  reproducible: true,
};

const agentPrediction = {
  agent_prediction_id: "00000000-0000-4000-8000-000000000051",
  agent_name: "consensus",
  agent_version: "1.0.0",
  predicted_probability: "0.6700000000",
  confidence: "0.7200000000",
  recommendation: "yes",
  rationale_summary: "Consenso ponderado por rol y confianza.",
  evidence: [
    {
      code: "weighted_consensus",
      summary: "Los agentes se ponderaron por rol.",
      direction: "yes",
      strength: "0.6000000000",
    },
  ],
  warnings: ["No se utilizó conocimiento externo ni noticias."],
  input_hash: "d".repeat(64),
  output_hash: "e".repeat(64),
  duration_ms: "1.200",
  disagreement_score: "0.0800000000",
  agent_weights: {
    reasoning: "0.2500000000",
    market: "0.3500000000",
    skeptic: "0.4000000000",
  },
};

const predictionRun = {
  prediction_run_id: "00000000-0000-4000-8000-000000000050",
  experiment_run_id: experimentRun.experiment_run_id,
  market_id: market.market_id,
  market_title: market.title,
  category: market.category,
  predicted_at: now,
  market_probability: "0.5200000000",
  consensus_probability: "0.6700000000",
  consensus_confidence: "0.7200000000",
  recommendation: "yes",
  edge: "0.1500000000",
  no_edge: "-0.1500000000",
  opportunity_level: "strong",
  disagreement_score: "0.0800000000",
  status: "predicted",
  agent_configuration_hash: "f".repeat(64),
  input_hash: "a".repeat(64),
  result_hash: "b".repeat(64),
  duration_ms: "5.400",
  safe_error_type: null,
  abstention_reason: null,
  correlation_id: "prediction-correlation",
  causation_id: "replay-predict",
  created_at: now,
  agent_weights: agentPrediction.agent_weights,
  agent_predictions: [
    {
      ...agentPrediction,
      agent_prediction_id: "00000000-0000-4000-8000-000000000052",
      agent_name: "reasoning",
    },
    {
      ...agentPrediction,
      agent_prediction_id: "00000000-0000-4000-8000-000000000053",
      agent_name: "market",
    },
    {
      ...agentPrediction,
      agent_prediction_id: "00000000-0000-4000-8000-000000000054",
      agent_name: "skeptic",
    },
    agentPrediction,
  ],
  estimated_outcome: "yes",
  market_status: "open",
  provider_code: "mock",
  commercial_evaluation: {
    evaluation_id: "00000000-0000-4000-8000-000000000055",
    portfolio_id: null,
    campaign_id: "experimental-v1",
    evaluated_at: now,
    estimated_outcome: "yes",
    potential_side: "buy_yes",
    market_probability: "0.5200000000",
    consensus_probability: "0.6700000000",
    gross_edge: "0.1500000000",
    estimated_fees: "0.0050000000",
    estimated_slippage: "0.0050000000",
    estimated_other_costs: "0.0000000000",
    net_edge: "0.1400000000",
    confidence: "0.7200000000",
    commercial_label: "actionable",
    is_actionable: true,
    reasons: ["commercial_thresholds_passed"],
    warnings: [],
    data_freshness_status: "fresh",
    portfolio_has_open_position: false,
  },
  related_executions: [],
};

const predictionListItem = {
  prediction_run_id: predictionRun.prediction_run_id,
  market_id: predictionRun.market_id,
  market_title: predictionRun.market_title,
  provider_code: "mock",
  category: predictionRun.category,
  predicted_at: now,
  market_probability: predictionRun.market_probability,
  consensus_probability: predictionRun.consensus_probability,
  consensus_confidence: predictionRun.consensus_confidence,
  estimated_outcome: "yes",
  commercial_label: "actionable",
  potential_side: "buy_yes",
  gross_edge: "0.1500000000",
  net_edge: "0.1400000000",
  is_actionable: true,
  primary_reason: "commercial_thresholds_passed",
  portfolio_has_open_position: false,
  data_freshness_status: "fresh",
  campaign_id: "experimental-v1",
  portfolio_id: null,
};

const paperPortfolio = {
  portfolio_id: "00000000-0000-4000-8000-000000000060",
  name: "Replay synthetic-lab-v1",
  currency_unit: "USD_SIMULATED",
  initial_balance: "100.00000000",
  cash_balance: "101.00000000",
  reserved_balance: "0.00000000",
  realized_pnl: "1.00000000",
  unrealized_pnl: "0.00000000",
  equity: "101.00000000",
  total_exposure: "0.00000000",
  status: "active",
  strategy_configuration_hash: "1".repeat(64),
  experiment_run_id: experimentRun.experiment_run_id,
  created_at: now,
  updated_at: now,
  simulation_only: true,
};

const tradeDecision = {
  decision_id: "00000000-0000-4000-8000-000000000061",
  prediction_run_id: predictionRun.prediction_run_id,
  portfolio_id: paperPortfolio.portfolio_id,
  market_id: market.market_id,
  market_title: market.title,
  category: market.category,
  decided_at: now,
  decision: "buy_yes",
  side: "yes",
  market_probability: "0.5200000000",
  system_probability: "0.6700000000",
  edge: "0.1500000000",
  confidence: "0.7200000000",
  opportunity_level: "strong",
  proposed_stake: "1.00000000",
  approved_stake: "1.00000000",
  rejection_reasons: [],
  risk_checks: ["capital:passed", "market_exposure:passed"],
  configuration_hash: "2".repeat(64),
  result_hash: "3".repeat(64),
  correlation_id: "paper-correlation",
  causation_id: "replay-trade",
  experiment_run_id: experimentRun.experiment_run_id,
  prediction_result_hash: predictionRun.result_hash,
  simulation_only: true,
};

const paperTrade = {
  trade_id: "00000000-0000-4000-8000-000000000062",
  order_id: "00000000-0000-4000-8000-000000000063",
  decision_id: tradeDecision.decision_id,
  portfolio_id: paperPortfolio.portfolio_id,
  prediction_run_id: predictionRun.prediction_run_id,
  market_id: market.market_id,
  market_title: market.title,
  category: market.category,
  executed_at: now,
  side: "yes",
  entry_probability: "0.5200000000",
  effective_probability: "0.5250000000",
  units: "1.89573459",
  gross_cost: "0.98578199",
  fees: "0.00495262",
  slippage_cost: "0.00947867",
  net_cost: "1.00021328",
  maximum_loss: "1.00021328",
  potential_payout: "1.89573459",
  execution_model: "conservative_cost:1.0.0",
  result_hash: "4".repeat(64),
  decision_reasons: tradeDecision.risk_checks,
  prediction_result_hash: predictionRun.result_hash,
  experiment_run_id: experimentRun.experiment_run_id,
  simulation_only: true,
  probability_is_informative: true,
};

const paperPosition = {
  position_id: "00000000-0000-4000-8000-000000000064",
  portfolio_id: paperPortfolio.portfolio_id,
  market_id: market.market_id,
  market_title: market.title,
  category: market.category,
  side: "yes",
  opened_at: now,
  closed_at: now,
  status: "settled",
  units: paperTrade.units,
  average_entry_probability: paperTrade.effective_probability,
  invested_amount: paperTrade.net_cost,
  current_mark_probability: "1.0000000000",
  unrealized_pnl: "0.00000000",
  realized_pnl: "0.89552131",
  settlement_outcome: "yes",
  prediction_run_id: predictionRun.prediction_run_id,
  trade_id: paperTrade.trade_id,
  opportunity_level: "strong",
  entry_edge: "0.1500000000",
  entry_confidence: "0.7200000000",
  experiment_run_id: experimentRun.experiment_run_id,
  simulation_only: true,
  mark_is_informative: true,
};

const paperSettlement = {
  settlement_id: "00000000-0000-4000-8000-000000000065",
  position_id: paperPosition.position_id,
  portfolio_id: paperPortfolio.portfolio_id,
  market_id: market.market_id,
  market_title: market.title,
  resolved_at: now,
  outcome: "yes",
  gross_payout: paperTrade.units,
  fees: "0.00000000",
  net_payout: paperTrade.units,
  realized_pnl: paperPosition.realized_pnl,
  settlement_policy: "official_binary_outcome",
  result_hash: "5".repeat(64),
  created_at: now,
  correlation_id: "paper-correlation",
  causation_id: "replay-settle",
  experiment_run_id: experimentRun.experiment_run_id,
  simulation_only: true,
};

const equityCurve = [
  {
    recorded_at: now,
    equity: "100.00000000",
    drawdown: "0.0000000000",
    exposure: "0.00000000",
    realized_pnl: "0.00000000",
    unrealized_pnl: "0.00000000",
    cumulative_costs: "0.00000000",
    result_hash: "6".repeat(64),
    valuation_is_simulated: true,
  },
  {
    recorded_at: now,
    equity: "101.00000000",
    drawdown: "0.0000000000",
    exposure: "0.00000000",
    realized_pnl: "1.00000000",
    unrealized_pnl: "0.00000000",
    cumulative_costs: "0.01443129",
    result_hash: "7".repeat(64),
    valuation_is_simulated: true,
  },
];

const paperPerformance = {
  portfolio: paperPortfolio,
  metrics: {
    initial_capital: "100",
    final_capital: "101",
    net_profit: "1",
    simulated_roi: "0.01",
    realized_pnl: "1",
    unrealized_pnl: "0",
    total_costs: "0.01443129",
    decision_count: 1,
    open_trade_count: 0,
    closed_trade_count: 1,
    abstention_count: 0,
    rejection_count: 0,
    win_rate: "1",
    average_profit: "1",
    average_loss: null,
    profit_factor: "999",
    maximum_drawdown: "0",
    maximum_exposure: "1",
    coverage: "1",
    independent_resolved_markets: 1,
    largest_trade_profit_share: "1",
    evidence_state: "insufficient_sample",
    by_category: [{ key: "ejemplos", trade_count: 1, net_pnl: "1" }],
    by_opportunity_level: [{ key: "strong", trade_count: 1, net_pnl: "1" }],
    by_edge_range: [{ key: "10-20pp", trade_count: 1, net_pnl: "1" }],
    by_confidence_range: [{ key: "70-85%", trade_count: 1, net_pnl: "1" }],
  },
  baselines: [
    {
      name: "no_trade",
      initial_capital: "100",
      final_capital: "100",
      net_profit: "0",
      simulated_roi: "0",
      trade_count: 0,
      total_costs: "0",
    },
  ],
  alerts: [
    {
      code: "insufficient_closed_trades",
      severity: "info",
      message: "The resolved sample is too small.",
    },
  ],
  strategy_configuration_hash: paperPortfolio.strategy_configuration_hash,
  simulation_only: true,
  disclaimer: "Simulated research results.",
};

type ApiFixture = {
  markets?: object[];
  sources?: object[];
  runs?: object[];
  observations?: object[];
  history?: object[];
  datasets?: object[];
  experiments?: object[];
  predictions?: object[];
  paperPortfolios?: object[];
  tradeDecisions?: object[];
  paperTrades?: object[];
  paperPositions?: object[];
  paperSettlements?: object[];
  paperPerformance?: object;
  equityCurve?: object[];
  delayMs?: number;
  status?: number;
};

async function installApi(page: Page, fixture: ApiFixture = {}) {
  await page.route(
    /\/(markets|sources|collector-runs|experiment-runs|replay-datasets|predictions|agent-predictions|paper-portfolios|paper-trading|trade-decisions|paper-trades|paper-positions|paper-settlements)(\/.*)?(\?.*)?$/,
    async (route) => {
      if (new URL(route.request().url()).port !== "8000") {
        await route.continue();
        return;
      }
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
    },
  );
}

async function fulfillApiRoute(route: Route, fixture: ApiFixture) {
  const path = new URL(route.request().url()).pathname;
  if (path === "/markets") {
    await route.fulfill({
      json: page(fixture.markets ?? [market, secondMarket]),
    });
    return;
  }
  if (path.endsWith("/observations")) {
    await route.fulfill({
      json: page(fixture.observations ?? [observation]),
    });
    return;
  }
  if (path.endsWith("/history")) {
    await route.fulfill({
      json: page(fixture.history ?? [historyEvent]),
    });
    return;
  }
  if (path === "/sources") {
    await route.fulfill({ json: fixture.sources ?? [source] });
    return;
  }
  if (path === "/replay-datasets") {
    await route.fulfill({ json: fixture.datasets ?? [replayDataset] });
    return;
  }
  if (path === "/experiment-runs") {
    await route.fulfill({
      json: page(fixture.experiments ?? [experimentRun]),
    });
    return;
  }
  if (path === "/predictions") {
    await route.fulfill({
      json: {
        items: fixture.predictions ?? [predictionListItem],
        page: 1,
        page_size: 25,
        total_items: (fixture.predictions ?? [predictionListItem]).length,
        total_pages: 1,
        applied_filters: {},
      },
    });
    return;
  }
  if (path === `/predictions/${predictionRun.prediction_run_id}`) {
    await route.fulfill({ json: predictionRun });
    return;
  }
  if (path === "/agent-predictions") {
    await route.fulfill({
      json: page([predictionRun]),
    });
    return;
  }
  if (path === "/paper-trading/manual-trades") {
    await route.fulfill({
      json: {
        status: "filled",
        trade_decision_id: tradeDecision.decision_id,
        paper_order_id: paperTrade.order_id,
        paper_trade_id: paperTrade.trade_id,
        position_id: paperPosition.position_id,
        portfolio_id: paperPortfolio.portfolio_id,
        rejection_reasons: [],
        decision_source: "manual_override",
        simulation_only: true,
        disclaimer:
          "Esta operación es exclusivamente simulada. No utiliza dinero real.",
      },
    });
    return;
  }
  if (path.endsWith("/performance")) {
    await route.fulfill({
      json: fixture.paperPerformance ?? paperPerformance,
    });
    return;
  }
  if (path.endsWith("/equity-curve")) {
    await route.fulfill({ json: fixture.equityCurve ?? equityCurve });
    return;
  }
  if (path === "/paper-portfolios") {
    await route.fulfill({
      json: page(fixture.paperPortfolios ?? []),
    });
    return;
  }
  if (path === "/trade-decisions") {
    await route.fulfill({ json: page(fixture.tradeDecisions ?? []) });
    return;
  }
  if (path === "/paper-trades") {
    await route.fulfill({ json: page(fixture.paperTrades ?? []) });
    return;
  }
  if (path === "/paper-positions") {
    await route.fulfill({ json: page(fixture.paperPositions ?? []) });
    return;
  }
  if (path === "/paper-settlements") {
    await route.fulfill({ json: page(fixture.paperSettlements ?? []) });
    return;
  }
  await route.fulfill({ json: page(fixture.runs ?? [syncRun]) });
}

function page(items: object[]) {
  return {
    items,
    page: 1,
    page_size: 100,
    total: items.length,
    pages: items.length ? 1 : 0,
  };
}

test("defaults to an understandable Spanish simple view", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Todo lo importante, de un vistazo",
    }),
  ).toBeVisible();
  await expect(page.getByText("Estado general")).toBeVisible();
  await expect(page.getByText("Mercados disponibles")).toBeVisible();
  await expect(page.getByText("Datos sólo informativos")).toBeVisible();
  await expect(page.getByText("Laboratorio histórico disponible")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Predicciones", exact: true }),
  ).toHaveAttribute("href", "/predictions");
  await expect(
    page.getByRole("link", { name: "Experimentos", exact: true }),
  ).toHaveCount(0);

  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(
    /\b(Provider|Collector|Snapshot|Checkpoint|DTO|Registry|ROI)\b/,
  );
  expect(visibleText).not.toContain("rentabilidad");
  expect(visibleText).not.toContain("Ganancia o pérdida");
});

test("shows simulated portfolio, trades, positions and performance", async ({
  page,
}) => {
  await installApi(page, {
    paperPortfolios: [paperPortfolio],
    tradeDecisions: [tradeDecision],
    paperTrades: [paperTrade],
    paperPositions: [paperPosition],
    paperSettlements: [paperSettlement],
    paperPerformance,
    equityCurve,
  });
  await page.goto("/");

  await page.goto("/portfolio");
  await expect(
    page.getByText(
      "Resultados simulados. No representan dinero real ni garantizan rendimientos futuros.",
    ),
  ).toBeVisible();
  await expect(page.getByText("101.00 USD_SIMULATED").first()).toBeVisible();

  await page.goto("/trades");
  await expect(
    page.getByRole("heading", { name: "Operaciones simuladas" }),
  ).toBeVisible();
  await expect(page.getByText("Capital en riesgo")).toBeVisible();

  await page.goto("/positions");
  await expect(
    page.getByRole("heading", { name: "Posiciones simuladas" }),
  ).toBeVisible();

  await page.goto("/performance");
  await expect(
    page.getByRole("heading", { name: "Rendimiento experimental" }),
  ).toBeVisible();
  await expect(page.getByText("Muestra insuficiente")).toBeVisible();
});

test("switches the complete interface to English", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Idioma" }).click();

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Everything important, at a glance",
    }),
  ).toBeVisible();
  await expect(page.getByText("Informational data only")).toBeVisible();
  await expect(page.getByText("Data sources")).toBeVisible();
});

test("reveals operational details only in advanced mode", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await expect(page.getByText("Tipo seguro de error")).toHaveCount(0);
  await page.getByRole("button", { name: "Vista avanzada" }).click();

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Datos técnicos e históricos",
    }),
  ).toBeVisible();
  await expect(page.getByText("Tipo seguro de error")).toBeVisible();
  await expect(page.getByText("Identificador de seguimiento")).toBeVisible();
});

test("shows reproducible experiments only in advanced mode", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await page.goto("/experiments");
  await page.getByRole("button", { name: "Vista avanzada" }).click();

  await expect(
    page.getByRole("heading", { name: "Experimentos históricos" }),
  ).toBeVisible();
  await expect(page.getByText("synthetic-lab").first()).toBeVisible();
  await expect(page.getByText("80 observaciones")).toBeVisible();
  await expect(page.getByText("Sí", { exact: true })).toBeVisible();
});

test("explains predictions without presenting fictional returns", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await page.goto("/predictions");
  await expect(page).toHaveURL(/\/predictions$/);

  await expect(
    page.getByRole("heading", { name: "Predicciones", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("67.00%")).toBeVisible();
  await expect(
    page.getByLabel("Conviene", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver detalle" })).toBeVisible();
  await expect(page.getByText(/operación automática sigue activa/)).toBeVisible();

  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(/\bROI\b/);
  expect(visibleText).not.toContain("rentabilidad");
});

test("shows advanced agent traceability and the agent monitor", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await page.goto("/predictions");
  await page.getByRole("link", { name: "Ver detalle" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/predictions/${predictionRun.prediction_run_id}$`),
  );
  await page.getByRole("button", { name: "Vista avanzada" }).click();
  await expect(page.getByText("Salidas de agentes")).toBeVisible();
  await expect(page.getByText("Trazabilidad")).toBeVisible();

  await page.goto("/agents");
  await page.getByRole("button", { name: "Vista avanzada" }).click();
  await expect(
    page.getByRole("heading", { name: "Agentes deterministas" }),
  ).toBeVisible();
  await expect(page.getByText("Reasoning Agent").first()).toBeVisible();
  await expect(page.getByText("Consensus Agent").first()).toBeVisible();
  await expect(
    page.getByText("Backend determinista por reglas").first(),
  ).toBeVisible();
});

test("manual trade is an override and does not replace automation", async ({
  page,
}) => {
  await installApi(page);
  await page.goto("/predictions");

  await page.getByRole("button", { name: "Operar", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Override manual de paper trading",
    }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Esta operación es exclusivamente simulada. No utiliza dinero real.",
    ),
  ).toBeVisible();
  await page
    .getByLabel("Motivo del override")
    .fill("Quiero comprobar una hipótesis contraria.");
  await page
    .getByRole("button", { name: "Confirmar operación simulada" })
    .click();
  await expect(
    page.getByText("La operación simulada fue creada."),
  ).toBeVisible();
});

test("shows a translated loading state", async ({ page }) => {
  await installApi(page, { delayMs: 700 });
  await page.goto("/");
  await expect(page.getByLabel("Cargando información")).toBeVisible();
});

test("shows an empty market state", async ({ page }) => {
  await installApi(page, {
    markets: [],
    sources: [],
    runs: [],
    observations: [],
    history: [],
    datasets: [],
    experiments: [],
    predictions: [],
  });
  await page.goto("/");
  await page.goto("/markets");
  await expect(
    page.getByText("Todavía no hay mercados disponibles."),
  ).toBeVisible();
});

test("shows a safe error state", async ({ page }) => {
  await installApi(page, { status: 503 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "No pudimos cargar la información",
    }),
  ).toBeVisible();
});

test("supports keyboard navigation and labeled status indicators", async ({
  page,
}) => {
  await installApi(page);
  await page.goto("/");
  await page.goto("/markets");

  const secondRow = page.getByRole("row", { name: /Segundo mercado/ });
  await secondRow.focus();
  await secondRow.press("Enter");
  await expect(page).toHaveURL(
    new RegExp(`/markets/${secondMarket.market_id}$`),
  );

  await expect(
    page.locator("h2").filter({ hasText: "Segundo mercado" }),
  ).toBeVisible();
  await expect(page.getByLabel("Abierto").first()).toBeVisible();
  await expect(
    page.getByLabel(/¿Qué significa\?: Estimación colectiva actual/).first(),
  ).toBeVisible();
});
