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
  ReplayDataset,
  SourceHealth,
  SyncRun,
  TradeDecision,
  EquityCurvePoint,
  AutomationState,
  PredictionEvaluation,
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
  automation: () => request<AutomationState>("/automation"),
  predictionEvaluation: () =>
    request<PredictionEvaluation>("/prediction-evaluation"),
  pauseAutomation: () =>
    request<AutomationState>("/automation/pause", {
      method: "POST",
      body: JSON.stringify({ reason: "Pausa solicitada desde el dashboard." }),
    }),
  resumeAutomation: () =>
    request<AutomationState>("/automation/resume", { method: "POST" }),
  paperPortfolios: () =>
    request<Page<PaperPortfolio>>("/paper-portfolios?page=1&page_size=100"),
  tradeDecisions: (portfolioId: string) =>
    request<Page<TradeDecision>>(
      `/trade-decisions?page=1&page_size=100&portfolio_id=${encodeURIComponent(portfolioId)}`,
    ),
  paperTrades: (portfolioId: string) =>
    request<Page<PaperTrade>>(
      `/paper-trades?page=1&page_size=100&portfolio_id=${encodeURIComponent(portfolioId)}`,
    ),
  allPaperTrades: () =>
    request<Page<PaperTrade>>("/paper-trades?page=1&page_size=100"),
  paperPositions: (portfolioId: string) =>
    request<Page<PaperPosition>>(
      `/paper-positions?page=1&page_size=100&portfolio_id=${encodeURIComponent(portfolioId)}`,
    ),
  allPaperPositions: () =>
    request<Page<PaperPosition>>("/paper-positions?page=1&page_size=100"),
  paperSettlements: (portfolioId: string) =>
    request<Page<PaperSettlement>>(
      `/paper-settlements?page=1&page_size=100&portfolio_id=${encodeURIComponent(portfolioId)}`,
    ),
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
