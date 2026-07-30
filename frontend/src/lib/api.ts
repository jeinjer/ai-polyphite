import type {
  HistoryEvent,
  ExperimentRun,
  Market,
  Observation,
  PaperPerformance,
  PaperPortfolio,
  PaperPosition,
  PaperSettlement,
  PaperTrade,
  Page,
  PredictionRun,
  PredictionListPage,
  ManualPaperTradeResponse,
  ReplayDataset,
  SourceHealth,
  SyncRun,
  TradeDecision,
  EquityCurvePoint,
} from "./api-types";
import { API_BASE_URL } from "./runtime-config";

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  markets: () =>
    request<Page<Market>>(
      "/markets?page=1&page_size=100&order_by=updated_at&direction=desc",
    ),
  sources: () => request<SourceHealth[]>("/sources"),
  syncRuns: () => request<Page<SyncRun>>("/collector-runs?page=1&page_size=50"),
  experimentRuns: () =>
    request<Page<ExperimentRun>>("/experiment-runs?page=1&page_size=50"),
  replayDatasets: () => request<ReplayDataset[]>("/replay-datasets"),
  agentPredictions: () =>
    request<Page<PredictionRun>>(
      "/agent-predictions?page=1&page_size=100",
    ),
  predictions: (query: string) =>
    request<PredictionListPage>(`/predictions?${query}`),
  prediction: (predictionId: string) =>
    request<PredictionRun>(`/predictions/${encodeURIComponent(predictionId)}`),
  manualPaperTrade: (payload: {
    prediction_run_id: string;
    side: "yes" | "no";
    requested_stake: string;
    override_reason: string;
    idempotency_key: string;
  }) =>
    request<ManualPaperTradeResponse>("/paper-trading/manual-trades", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  paperPortfolios: () =>
    request<Page<PaperPortfolio>>("/paper-portfolios?page=1&page_size=100"),
  tradeDecisions: () =>
    request<Page<TradeDecision>>("/trade-decisions?page=1&page_size=100"),
  paperTrades: () =>
    request<Page<PaperTrade>>("/paper-trades?page=1&page_size=100"),
  paperPositions: () =>
    request<Page<PaperPosition>>("/paper-positions?page=1&page_size=100"),
  paperSettlements: () =>
    request<Page<PaperSettlement>>("/paper-settlements?page=1&page_size=100"),
  paperPerformance: (portfolioId: string) =>
    request<PaperPerformance>(`/paper-portfolios/${portfolioId}/performance`),
  paperEquityCurve: (portfolioId: string) =>
    request<EquityCurvePoint[]>(
      `/paper-portfolios/${portfolioId}/equity-curve`,
    ),
  observations: (marketId: string) =>
    request<Page<Observation>>(
      `/markets/${marketId}/observations?page=1&page_size=500`,
    ),
  history: (marketId: string) =>
    request<Page<HistoryEvent>>(
      `/markets/${marketId}/history?page=1&page_size=500`,
    ),
};
