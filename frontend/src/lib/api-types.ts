export type MarketStatus = "open" | "closed" | "resolved" | "cancelled";
export type ResolutionOutcome = "unresolved" | "yes" | "no" | "cancelled" | "other";
export type Recommendation = "yes" | "no" | "abstain";
export type PredictionStatus = "predicted" | "completed" | "abstained" | "failed";
export type OpportunityLevel = "none" | "weak" | "moderate" | "strong";
export type CurrencyUnit = "USD_SIMULATED" | "MANA_SIMULATED";
export type PositionSide = "yes" | "no";
export type TradeDecisionType = "buy_yes" | "buy_no" | "abstain" | "rejected";
export type PaperPositionStatus = "open" | "settled" | "cancelled";

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

export type AgentEvidence = {
  code: string;
  summary: string;
  direction: Recommendation | "neutral";
  strength: string;
};

export type AgentPrediction = {
  agent_prediction_id: string;
  agent_name: string;
  agent_version: string;
  predicted_probability: string | null;
  confidence: string;
  recommendation: Recommendation;
  rationale_summary: string;
  evidence: AgentEvidence[];
  warnings: string[];
  input_hash: string;
  output_hash: string;
  duration_ms: string;
  disagreement_score: string | null;
  agent_weights: Record<string, string>;
};

export type PredictionRun = {
  prediction_run_id: string;
  experiment_run_id: string | null;
  market_id: string;
  market_title: string;
  category: string | null;
  predicted_at: string;
  market_probability: string | null;
  consensus_probability: string | null;
  consensus_confidence: string;
  recommendation: Recommendation;
  edge: string | null;
  no_edge: string | null;
  opportunity_level: OpportunityLevel;
  disagreement_score: string;
  status: PredictionStatus;
  agent_configuration_hash: string;
  input_hash: string;
  result_hash: string;
  duration_ms: string;
  safe_error_type: string | null;
  abstention_reason: string | null;
  correlation_id: string;
  causation_id: string | null;
  created_at: string;
  agent_weights: Record<string, string>;
  agent_predictions: AgentPrediction[];
  estimated_outcome: EstimatedOutcome | null;
  market_status: MarketStatus | null;
  provider_code: string | null;
  commercial_evaluation: CommercialEvaluation | null;
  related_executions: {
    decision_id: string;
    portfolio_id: string;
    portfolio_name: string;
    decision: TradeDecisionType;
    decision_source: "automatic" | "manual_override";
    override_reason: string | null;
    side: PositionSide | null;
    decided_at: string;
    order_id: string | null;
    trade_id: string | null;
    position_id: string | null;
  }[];
};

export type EstimatedOutcome = "yes" | "no";
export type CommercialLabel =
  | "actionable"
  | "not_actionable"
  | "not_evaluable";
export type PotentialSide = "buy_yes" | "buy_no" | "none";
export type DataFreshnessStatus = "fresh" | "stale" | "unavailable";

export type CommercialEvaluation = {
  evaluation_id: string;
  portfolio_id: string | null;
  campaign_id: string;
  evaluated_at: string;
  estimated_outcome: EstimatedOutcome | null;
  potential_side: PotentialSide;
  market_probability: string | null;
  consensus_probability: string | null;
  gross_edge: string | null;
  estimated_fees: string;
  estimated_slippage: string;
  estimated_other_costs: string;
  net_edge: string | null;
  confidence: string;
  commercial_label: CommercialLabel;
  is_actionable: boolean;
  reasons: string[];
  warnings: string[];
  data_freshness_status: DataFreshnessStatus;
  portfolio_has_open_position: boolean;
};

export type PredictionListItem = {
  prediction_run_id: string;
  market_id: string;
  market_title: string;
  provider_code: string;
  category: string | null;
  predicted_at: string;
  market_probability: string | null;
  consensus_probability: string | null;
  consensus_confidence: string;
  estimated_outcome: EstimatedOutcome | null;
  commercial_label: CommercialLabel;
  potential_side: PotentialSide;
  gross_edge: string | null;
  net_edge: string | null;
  is_actionable: boolean;
  primary_reason: string;
  portfolio_has_open_position: boolean;
  data_freshness_status: DataFreshnessStatus;
  campaign_id: string | null;
  portfolio_id: string | null;
};

export type PredictionListPage = {
  items: PredictionListItem[];
  page: number;
  page_size: 25 | 50;
  total_items: number;
  total_pages: number;
  applied_filters: Record<string, string>;
};

export type PaperPortfolio = {
  portfolio_id: string;
  name: string;
  currency_unit: CurrencyUnit;
  initial_balance: string;
  cash_balance: string;
  reserved_balance: string;
  realized_pnl: string;
  unrealized_pnl: string;
  equity: string;
  total_exposure: string;
  status: "active" | "paused" | "closed";
  strategy_configuration_hash: string;
  experiment_run_id: string | null;
  created_at: string;
  updated_at: string;
  simulation_only: true;
};

export type TradeDecision = {
  decision_id: string;
  prediction_run_id: string;
  portfolio_id: string;
  market_id: string;
  market_title: string;
  category: string | null;
  decided_at: string;
  decision: TradeDecisionType;
  side: PositionSide | null;
  market_probability: string | null;
  system_probability: string | null;
  edge: string | null;
  confidence: string;
  opportunity_level: OpportunityLevel;
  proposed_stake: string;
  approved_stake: string;
  rejection_reasons: string[];
  risk_checks: string[];
  configuration_hash: string;
  result_hash: string;
  correlation_id: string;
  causation_id: string | null;
  experiment_run_id: string | null;
  prediction_result_hash: string;
  decision_source: "automatic" | "manual_override";
  override_reason: string | null;
  simulation_only: true;
};

export type ManualPaperTradeResponse = {
  status: "filled" | "rejected" | "duplicate";
  trade_decision_id: string;
  paper_order_id: string | null;
  paper_trade_id: string | null;
  position_id: string | null;
  portfolio_id: string;
  side: PositionSide | null;
  rejection_reasons: string[];
  decision_source: "automatic" | "manual_override";
  simulation_only: true;
  disclaimer: string;
};

export type PaperTrade = {
  trade_id: string;
  order_id: string;
  decision_id: string;
  portfolio_id: string;
  prediction_run_id: string;
  market_id: string;
  market_title: string;
  category: string | null;
  executed_at: string;
  side: PositionSide;
  entry_probability: string;
  effective_probability: string;
  units: string;
  gross_cost: string;
  fees: string;
  slippage_cost: string;
  net_cost: string;
  maximum_loss: string;
  potential_payout: string;
  execution_model: string;
  result_hash: string;
  decision_reasons: string[];
  prediction_result_hash: string;
  experiment_run_id: string | null;
  simulation_only: true;
  probability_is_informative: true;
};

export type PaperPosition = {
  position_id: string;
  portfolio_id: string;
  market_id: string;
  market_title: string;
  category: string | null;
  side: PositionSide;
  opened_at: string;
  closed_at: string | null;
  status: PaperPositionStatus;
  units: string;
  average_entry_probability: string;
  invested_amount: string;
  current_mark_probability: string | null;
  unrealized_pnl: string;
  realized_pnl: string;
  settlement_outcome: ResolutionOutcome | null;
  prediction_run_id: string;
  trade_id: string;
  opportunity_level: OpportunityLevel;
  entry_edge: string;
  entry_confidence: string;
  experiment_run_id: string | null;
  simulation_only: true;
  mark_is_informative: true;
};

export type PaperSettlement = {
  settlement_id: string;
  position_id: string;
  portfolio_id: string;
  market_id: string;
  market_title: string;
  resolved_at: string;
  outcome: ResolutionOutcome;
  gross_payout: string;
  fees: string;
  net_payout: string;
  realized_pnl: string;
  settlement_policy: string;
  result_hash: string;
  created_at: string;
  correlation_id: string;
  causation_id: string | null;
  experiment_run_id: string | null;
  simulation_only: true;
};

export type EquityCurvePoint = {
  recorded_at: string;
  equity: string;
  drawdown: string;
  exposure: string;
  realized_pnl: string;
  unrealized_pnl: string;
  cumulative_costs: string;
  result_hash: string;
  valuation_is_simulated: true;
};

export type StrategyBreakdown = {
  key: string;
  trade_count: number;
  net_pnl: string;
};

export type BaselinePerformance = {
  name: string;
  initial_capital: string;
  final_capital: string;
  net_profit: string;
  simulated_roi: string;
  trade_count: number;
  total_costs: string;
};

export type SimulationAlert = {
  code: string;
  severity: string;
  message: string;
};

export type PaperPerformance = {
  portfolio: PaperPortfolio;
  metrics: {
    initial_capital: string;
    final_capital: string;
    net_profit: string;
    simulated_roi: string;
    realized_pnl: string;
    unrealized_pnl: string;
    total_costs: string;
    decision_count: number;
    open_trade_count: number;
    closed_trade_count: number;
    abstention_count: number;
    rejection_count: number;
    win_rate: string | null;
    average_profit: string | null;
    average_loss: string | null;
    profit_factor: string | null;
    maximum_drawdown: string;
    maximum_exposure: string;
    coverage: string;
    independent_resolved_markets: number;
    largest_trade_profit_share: string;
    evidence_state:
      | "insufficient_sample"
      | "preliminary_result"
      | "under_observation"
      | "sufficient_to_expand_validation";
    by_category: StrategyBreakdown[];
    by_opportunity_level: StrategyBreakdown[];
    by_edge_range: StrategyBreakdown[];
    by_confidence_range: StrategyBreakdown[];
  };
  baselines: BaselinePerformance[];
  alerts: SimulationAlert[];
  strategy_configuration_hash: string;
  simulation_only: true;
  disclaimer: string;
};
