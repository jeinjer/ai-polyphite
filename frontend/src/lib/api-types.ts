export type MarketStatus = "open" | "closed" | "resolved" | "cancelled";
export type ResolutionOutcome = "unresolved" | "yes" | "no" | "cancelled" | "other";

export type Observation = {
  observation_id: string;
  observed_at: string;
  probability: string | null;
  volume: string | null;
  liquidity: string | null;
  source_updated_at: string | null;
  ingested_at: string;
  provider_code: string;
};

export type Market = {
  market_id: string;
  provider_market_id: string;
  title: string;
  description?: string | null;
  category: string | null;
  resolution_at: string | null;
  source_created_at: string | null;
  status: MarketStatus;
  ingested_at: string;
  updated_at: string;
  provider: {
    provider_id: string;
    code: string;
    name: string;
    enabled: boolean;
  };
  resolution_outcome: ResolutionOutcome;
  resolved_at: string | null;
  resolution_source: string | null;
  latest_observation: Observation | null;
  probability_change: string | null;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type SourceHealth = {
  code: string;
  name: string;
  status: "healthy" | "degraded" | "unhealthy";
  checked_at: string;
  latency_ms: number;
  safe_error_type: string | null;
};

export type SyncRun = {
  run_id: string;
  provider_code: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "completed" | "failed" | "skipped_locked";
  markets_fetched: number;
  markets_created: number;
  markets_updated: number;
  markets_unchanged: number;
  observations_fetched: number;
  observations_created: number;
  observations_duplicated: number;
  observations_skipped: number;
  retry_count: number;
  duration_ms: number | null;
  safe_error_type: string | null;
  correlation_id: string;
};

export type ExperimentRun = {
  experiment_run_id: string;
  dataset_id: string;
  dataset_version: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "completed" | "failed";
  replay_start: string;
  replay_end: string;
  random_seed: number;
  configuration_hash: string;
  code_version: string | null;
  result_hash: string | null;
  correlation_id: string;
  safe_error_type: string | null;
  reproducible: boolean;
};

export type ReplayDataset = {
  dataset_id: string;
  version: string;
  schema_version: string;
  created_at: string;
  description: string;
  content_sha256: string;
  replay_start: string;
  replay_end: string;
  market_count: number;
  observation_count: number;
};

export type HistoryEvent = {
  event_id: string;
  event_type:
    | "source_created"
    | "ingested"
    | "state_changed"
    | "observation"
    | "scheduled_close"
    | "resolution";
  occurred_at: string;
  previous_status: MarketStatus | null;
  status: MarketStatus | null;
  resolution_outcome: ResolutionOutcome | null;
  probability: string | null;
  volume: string | null;
  liquidity: string | null;
  source: string | null;
};
