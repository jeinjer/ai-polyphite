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
  status: "completed",
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
  delayMs?: number;
  status?: number;
};

async function installApi(page: Page, fixture: ApiFixture = {}) {
  await page.route(
    /\/(markets|sources|collector-runs|experiment-runs|replay-datasets|predictions)(\/.*)?(\?.*)?$/,
    async (route) => {
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
      json: page(fixture.predictions ?? [predictionRun]),
    });
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
    page.getByRole("button", { name: "Experimentos", exact: true }),
  ).toHaveCount(0);

  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(
    /\b(Provider|Collector|Snapshot|Checkpoint|DTO|Registry|ROI)\b/,
  );
  expect(visibleText).not.toContain("Operaciones");
  expect(visibleText).not.toContain("rentabilidad");
  expect(visibleText).not.toContain("Ganancia o pérdida");
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

  await page.getByRole("button", { name: "Vista avanzada" }).click();
  await page.getByRole("button", { name: "Experimentos", exact: true }).click();

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

  await page.getByRole("button", { name: "Predicciones", exact: true }).click();

  await expect(
    page.getByRole("heading", { name: "Predicciones reproducibles" }),
  ).toBeVisible();
  await expect(
    page.getByText(/AI-Polyphite estima 67.0%, mientras que la fuente mostraba 52.0%/),
  ).toBeVisible();
  await expect(
    page.getByLabel(/Estimación generada por AI-Polyphite/).first(),
  ).toBeVisible();
  await expect(
    page.getByLabel(/No equivale a probabilidad de acierto/).first(),
  ).toBeVisible();

  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(/\bROI\b/);
  expect(visibleText).not.toContain("rentabilidad");
});

test("shows advanced agent traceability and the agent monitor", async ({ page }) => {
  await installApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Vista avanzada" }).click();
  await page.getByRole("button", { name: "Predicciones", exact: true }).click();
  await expect(page.getByText("Resultados de los agentes")).toBeVisible();
  await expect(page.getByText("Hash de configuración")).toBeVisible();
  await expect(page.getByText("Pesos del consenso").first()).toBeVisible();

  await page.getByRole("button", { name: "Agentes", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Agentes deterministas" }),
  ).toBeVisible();
  await expect(page.getByText("Reasoning Agent").first()).toBeVisible();
  await expect(page.getByText("Consensus Agent").first()).toBeVisible();
  await expect(
    page.getByText("Backend determinista por reglas").first(),
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
  await page.getByRole("button", { name: "Mercados", exact: true }).click();
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
  await page.getByRole("button", { name: "Mercados", exact: true }).click();

  const secondRow = page.getByRole("row", { name: /Segundo mercado/ });
  await secondRow.focus();
  await secondRow.press("Enter");

  await expect(
    page.locator("h2").filter({ hasText: "Segundo mercado" }),
  ).toBeVisible();
  await expect(page.getByLabel("Abierto").first()).toBeVisible();
  await expect(
    page.getByLabel(/¿Qué significa\?: Estimación colectiva actual/).first(),
  ).toBeVisible();
});
