import type {
  HistoryEvent,
  ExperimentRun,
  Market,
  Observation,
  Page,
  PredictionRun,
  ReplayDataset,
  SourceHealth,
  SyncRun,
} from "./api-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json" },
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
  predictions: () =>
    request<Page<PredictionRun>>(
      "/predictions?page=1&page_size=100",
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
