"use client";

import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Info,
  ShieldCheck,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ReactNode } from "react";

import { useI18n } from "@/i18n/i18n-provider";
import type { MessageKey } from "@/i18n/messages";
import type {
  EquityCurvePoint,
  PaperPerformance,
  PaperPortfolio,
  PaperPosition,
  PaperSettlement,
  PaperTrade,
  TradeDecision,
} from "@/lib/api-types";

type PaperSection = "portfolio" | "trades" | "positions" | "performance";

type Props = Readonly<{
  section: PaperSection;
  mode: "simple" | "advanced";
  portfolios: PaperPortfolio[];
  portfolio: PaperPortfolio | null;
  decisions: TradeDecision[];
  trades: PaperTrade[];
  positions: PaperPosition[];
  settlements: PaperSettlement[];
  performance: PaperPerformance | null;
  equityCurve: EquityCurvePoint[];
  onSelectPortfolio: (portfolioId: string) => void;
}>;

export function PaperTradingView(props: Props) {
  if (props.section === "trades") {
    return <TradesView {...props} />;
  }
  if (props.section === "positions") {
    return <PositionsView {...props} />;
  }
  if (props.section === "performance") {
    return <PerformanceView {...props} />;
  }
  return <PortfolioView {...props} />;
}

function PortfolioView({
  portfolio,
  portfolios,
  positions,
  performance,
  mode,
  onSelectPortfolio,
}: Props) {
  const { t } = useI18n();
  if (!portfolio) {
    return <EmptyState message={t("empty.paperPortfolio")} />;
  }
  const metrics = performance?.metrics;
  const openCount = positions.filter((item) => item.status === "open").length;
  return (
    <PaperLayout
      title={t("paper.portfolioTitle")}
      description={t("paper.portfolioDescription")}
      portfolio={portfolio}
      portfolios={portfolios}
      onSelectPortfolio={onSelectPortfolio}
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label={t("paper.initialCapital")}
          value={amount(portfolio.initial_balance, portfolio.currency_unit)}
        />
        <Metric
          label={t("paper.equity")}
          value={amount(portfolio.equity, portfolio.currency_unit)}
          tooltip={t("paper.tooltip.equity")}
        />
        <Metric
          label={t("paper.netProfit")}
          value={signedAmount(
            metrics?.net_profit ?? "0",
            portfolio.currency_unit,
          )}
        />
        <Metric
          label={t("paper.cash")}
          value={amount(portfolio.cash_balance, portfolio.currency_unit)}
        />
        <Metric
          label={t("paper.exposure")}
          value={amount(portfolio.total_exposure, portfolio.currency_unit)}
          tooltip={t("paper.tooltip.exposure")}
        />
        <Metric label={t("paper.openPositions")} value={String(openCount)} />
        <Metric
          label={t("paper.closedTrades")}
          value={String(metrics?.closed_trade_count ?? 0)}
        />
        <Metric
          label={t("paper.maxDrawdown")}
          value={percent(metrics?.maximum_drawdown)}
          tooltip={t("paper.tooltip.drawdown")}
        />
      </div>

      {metrics && (
        <section className="rounded-2xl border border-white/8 bg-white/[0.025] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                {t("paper.evidence")}
              </p>
              <p className="mt-2 flex items-center gap-2 font-medium text-cyan-100">
                <ShieldCheck aria-hidden="true" className="size-4 text-cyan-300" />
                {t(evidenceKey[metrics.evidence_state])}
              </p>
            </div>
            <Help text={t("paper.tooltip.evidence")} />
          </div>
          {mode === "advanced" && (
            <Trace
              rows={[
                [t("paper.configHash"), portfolio.strategy_configuration_hash],
                ["Portfolio ID", portfolio.portfolio_id],
                ["Experiment ID", portfolio.experiment_run_id ?? "—"],
              ]}
            />
          )}
        </section>
      )}
    </PaperLayout>
  );
}

function TradesView({
  portfolio,
  portfolios,
  decisions,
  trades,
  positions,
  settlements,
  mode,
  onSelectPortfolio,
}: Props) {
  const { t } = useI18n();
  const decisionById = new Map(decisions.map((item) => [item.decision_id, item]));
  const positionByTrade = new Map(positions.map((item) => [item.trade_id, item]));
  const settlementByPosition = new Map(
    settlements.map((item) => [item.position_id, item]),
  );
  return (
    <PaperLayout
      title={t("paper.tradesTitle")}
      description={t("paper.tradesDescription")}
      portfolio={portfolio}
      portfolios={portfolios}
      onSelectPortfolio={onSelectPortfolio}
    >
      {!trades.length ? (
        <EmptyState message={t("empty.paperTrades")} />
      ) : (
        <div className="space-y-3">
          {trades.map((trade) => {
            const decision = decisionById.get(trade.decision_id);
            const position = positionByTrade.get(trade.trade_id);
            const settlement = position
              ? settlementByPosition.get(position.position_id)
              : undefined;
            return (
              <article
                key={trade.trade_id}
                className="rounded-2xl border border-white/8 bg-white/[0.025] p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-slate-100">
                      {trade.market_title}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {new Date(trade.executed_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-300">
                      {trade.decision_source === "manual_override"
                        ? t("paper.source.manual")
                        : t("paper.source.automatic")}
                    </span>
                    <StatusBadge
                      label={`${trade.side.toUpperCase()} · ${
                        settlement
                          ? t(outcomeKey[settlement.outcome])
                          : t("paper.noResult")
                      }`}
                      positive={
                        settlement
                          ? Number(settlement.realized_pnl) >= 0
                          : true
                      }
                    />
                  </div>
                </div>
                <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-5">
                  <Value label={t("paper.entry")} value={percent(trade.effective_probability)} />
                  <Value
                    label={t("paper.riskCapital")}
                    value={amount(
                      trade.maximum_loss,
                      portfolio?.currency_unit ?? "USD_SIMULATED",
                    )}
                  />
                  <Value
                    label={t("paper.costs")}
                    value={amount(
                      String(Number(trade.fees) + Number(trade.slippage_cost)),
                      portfolio?.currency_unit ?? "USD_SIMULATED",
                    )}
                  />
                  <Value
                    label={t("paper.result")}
                    value={
                      settlement
                        ? signedAmount(
                            settlement.realized_pnl,
                            portfolio?.currency_unit ?? "USD_SIMULATED",
                          )
                        : t("paper.noResult")
                    }
                  />
                  <Value
                    label={t("paper.whyOpened")}
                    value={decision?.risk_checks.join(", ") || "—"}
                  />
                </div>
                {mode === "advanced" && (
                  <Trace
                    rows={[
                      [t("paper.predictionHash"), trade.prediction_result_hash],
                      [t("paper.resultHash"), trade.result_hash],
                      [t("paper.configHash"), decision?.configuration_hash ?? "—"],
                      [t("paper.correlation"), decision?.correlation_id ?? "—"],
                    ]}
                  />
                )}
              </article>
            );
          })}
        </div>
      )}
    </PaperLayout>
  );
}

function PositionsView({
  portfolio,
  portfolios,
  positions,
  mode,
  onSelectPortfolio,
}: Props) {
  const { t } = useI18n();
  return (
    <PaperLayout
      title={t("paper.positionsTitle")}
      description={t("paper.positionsDescription")}
      portfolio={portfolio}
      portfolios={portfolios}
      onSelectPortfolio={onSelectPortfolio}
    >
      {!positions.length ? (
        <EmptyState message={t("empty.paperPositions")} />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {positions.map((position) => (
            <article
              key={position.position_id}
              className="rounded-2xl border border-white/8 bg-white/[0.025] p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{position.market_title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {position.category ?? "—"}
                  </p>
                </div>
                <StatusBadge
                  label={`${position.side.toUpperCase()} · ${t(statusKey[position.status])}`}
                  positive={Number(position.realized_pnl) >= 0}
                />
              </div>
              <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
                <Value
                  label={t("paper.riskCapital")}
                  value={amount(
                    position.invested_amount,
                    portfolio?.currency_unit ?? "USD_SIMULATED",
                  )}
                />
                <Value
                  label={t("paper.entry")}
                  value={percent(position.average_entry_probability)}
                />
                <Value
                  label={t("paper.mark")}
                  value={percent(position.current_mark_probability)}
                  tooltip={t("paper.tooltip.mark")}
                />
                <Value
                  label={
                    position.status === "open"
                      ? t("paper.unrealized")
                      : t("paper.realized")
                  }
                  value={signedAmount(
                    position.status === "open"
                      ? position.unrealized_pnl
                      : position.realized_pnl,
                    portfolio?.currency_unit ?? "USD_SIMULATED",
                  )}
                />
              </div>
              {mode === "advanced" && (
                <Trace
                  rows={[
                    ["Position ID", position.position_id],
                    ["Prediction ID", position.prediction_run_id],
                    ["Trade ID", position.trade_id],
                  ]}
                />
              )}
            </article>
          ))}
        </div>
      )}
    </PaperLayout>
  );
}

function PerformanceView({
  portfolio,
  portfolios,
  performance,
  equityCurve,
  mode,
  onSelectPortfolio,
}: Props) {
  const { t } = useI18n();
  if (!portfolio || !performance) {
    return <EmptyState message={t("empty.paperPortfolio")} />;
  }
  const metrics = performance.metrics;
  const chart = equityCurve.map((point) => ({
    date: new Date(point.recorded_at).toLocaleDateString(),
    equity: Number(point.equity),
    drawdown: Number(point.drawdown) * 100,
  }));
  return (
    <PaperLayout
      title={t("paper.performanceTitle")}
      description={t("paper.performanceDescription")}
      portfolio={portfolio}
      portfolios={portfolios}
      onSelectPortfolio={onSelectPortfolio}
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label={t("paper.netProfit")}
          value={signedAmount(metrics.net_profit, portfolio.currency_unit)}
        />
        <Metric
          label={t("paper.roi")}
          value={percent(metrics.simulated_roi)}
          tooltip={t("paper.tooltip.roi")}
        />
        <Metric label={t("paper.winRate")} value={percent(metrics.win_rate)} />
        <Metric
          label={t("paper.profitFactor")}
          value={metrics.profit_factor ?? "—"}
        />
        <Metric
          label={t("paper.maxDrawdown")}
          value={percent(metrics.maximum_drawdown)}
          tooltip={t("paper.tooltip.drawdown")}
        />
        <Metric label={t("paper.coverage")} value={percent(metrics.coverage)} />
        <Metric label={t("paper.decisions")} value={String(metrics.decision_count)} />
        <Metric label={t("paper.rejections")} value={String(metrics.rejection_count)} />
        <Metric
          label={t("paper.evidence")}
          value={t(evidenceKey[metrics.evidence_state])}
          tooltip={t("paper.tooltip.evidence")}
        />
      </div>

      <section className="rounded-2xl border border-white/8 bg-white/[0.025] p-5">
        <h3 className="font-medium">{t("paper.equityCurve")}</h3>
        <div className="mt-5 h-72" role="img" aria-label={t("paper.equityCurve")}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chart}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="4 4" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <ChartTooltip
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="#22d3ee"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="grid gap-3 xl:grid-cols-2">
        <Breakdown
          title={t("paper.baselines")}
          rows={performance.baselines.map((item) => ({
            name: t(baselineKey[item.name] ?? "paper.baseline.fixed_threshold"),
            value: signedAmount(item.net_profit, portfolio.currency_unit),
          }))}
        />
        <Breakdown
          title={t("paper.breakdown")}
          rows={metrics.by_category.map((item) => ({
            name: `${item.key} · ${item.trade_count}`,
            value: signedAmount(item.net_pnl, portfolio.currency_unit),
          }))}
        />
      </div>

      {!!performance.alerts.length && (
        <section className="rounded-2xl border border-amber-300/15 bg-amber-300/5 p-5">
          <h3 className="flex items-center gap-2 font-medium text-amber-100">
            <AlertTriangle aria-hidden="true" className="size-4" />
            {t("paper.alerts")}
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-amber-100/75">
            {performance.alerts.map((alert) => (
              <li key={alert.code}>
                <span className="font-medium">
                  {t(alertKey[alert.code] ?? "paper.alert.stale_data")}
                </span>
                {mode === "advanced" ? ` · ${alert.code}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
      {mode === "advanced" && (
        <Trace
          rows={[
            [t("paper.configHash"), performance.strategy_configuration_hash],
            ["Portfolio ID", portfolio.portfolio_id],
            ["Experiment ID", portfolio.experiment_run_id ?? "—"],
          ]}
        />
      )}
    </PaperLayout>
  );
}

function PaperLayout({
  title,
  description,
  portfolio,
  portfolios,
  onSelectPortfolio,
  children,
}: Readonly<{
  title: string;
  description: string;
  portfolio: PaperPortfolio | null;
  portfolios: PaperPortfolio[];
  onSelectPortfolio: (portfolioId: string) => void;
  children: ReactNode;
}>) {
  const { t } = useI18n();
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </div>
        <label className="min-w-64 text-xs text-slate-400">
          <span className="mb-1.5 block">{t("paper.portfolioSelector")}</span>
          <select
            aria-label={t("paper.portfolioSelector")}
            className="w-full rounded-xl border border-white/10 bg-[#0a101a] px-3 py-2 text-sm text-slate-200"
            value={portfolio?.portfolio_id ?? ""}
            onChange={(event) => onSelectPortfolio(event.target.value)}
          >
            {!portfolio && <option value="">—</option>}
            {portfolios.map((item) => (
              <option key={item.portfolio_id} value={item.portfolio_id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </header>
      <div
        className="flex items-start gap-3 rounded-2xl border border-cyan-300/15 bg-cyan-300/5 p-4 text-sm text-cyan-100"
        role="note"
      >
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        {t("paper.disclaimer")}
      </div>
      {children}
    </div>
  );
}

function Metric({
  label,
  value,
  tooltip,
}: Readonly<{ label: string; value: string; tooltip?: string }>) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.025] p-5">
      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-slate-500">
        {label}
        {tooltip && <Help text={tooltip} />}
      </p>
      <p className="mt-3 text-xl font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function Value({
  label,
  value,
  tooltip,
}: Readonly<{ label: string; value: string; tooltip?: string }>) {
  return (
    <div>
      <p className="flex items-center gap-1 text-xs text-slate-500">
        {label}
        {tooltip && <Help text={tooltip} />}
      </p>
      <p className="mt-1 break-words text-slate-200">{value}</p>
    </div>
  );
}

function Help({ text }: Readonly<{ text: string }>) {
  return (
    <span title={text} aria-label={text} className="inline-flex cursor-help">
      <CircleHelp aria-hidden="true" className="size-3.5 text-slate-500" />
    </span>
  );
}

function StatusBadge({
  label,
  positive,
}: Readonly<{ label: string; positive: boolean }>) {
  const Icon = positive ? CheckCircle2 : AlertTriangle;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
        positive
          ? "border-emerald-300/20 bg-emerald-300/8 text-emerald-200"
          : "border-amber-300/20 bg-amber-300/8 text-amber-200"
      }`}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      {label}
    </span>
  );
}

function Trace({ rows }: Readonly<{ rows: [string, string][] }>) {
  return (
    <dl className="mt-5 space-y-2 border-t border-white/8 pt-4 text-xs">
      {rows.map(([label, value]) => (
        <div key={label} className="grid gap-1 sm:grid-cols-[180px_1fr]">
          <dt className="text-slate-500">{label}</dt>
          <dd className="break-all font-mono text-slate-400">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Breakdown({
  title,
  rows,
}: Readonly<{ title: string; rows: { name: string; value: string }[] }>) {
  return (
    <section className="rounded-2xl border border-white/8 bg-white/[0.025] p-5">
      <h3 className="font-medium">{title}</h3>
      <div className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={row.name} className="flex justify-between gap-4 text-sm">
            <span className="text-slate-400">{row.name}</span>
            <span className="font-medium text-slate-100">{row.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function EmptyState({ message }: Readonly<{ message: string }>) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center text-sm text-slate-500">
      <Info aria-hidden="true" className="mx-auto mb-3 size-5" />
      {message}
    </div>
  );
}

function amount(value: string, currency: string): string {
  return `${Number(value).toFixed(2)} ${currency}`;
}

function signedAmount(value: string, currency: string): string {
  const numeric = Number(value);
  return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(2)} ${currency}`;
}

function percent(value: string | null | undefined): string {
  return value === null || value === undefined
    ? "—"
    : `${(Number(value) * 100).toFixed(2)}%`;
}

const evidenceKey = {
  insufficient_sample: "paper.evidence.insufficient_sample",
  preliminary_result: "paper.evidence.preliminary_result",
  under_observation: "paper.evidence.under_observation",
  sufficient_to_expand_validation:
    "paper.evidence.sufficient_to_expand_validation",
} satisfies Record<string, MessageKey>;

const outcomeKey = {
  unresolved: "outcome.unresolved",
  yes: "outcome.yes",
  no: "outcome.no",
  cancelled: "outcome.cancelled",
  other: "outcome.other",
} satisfies Record<string, MessageKey>;

const statusKey = {
  open: "status.open",
  settled: "status.settled",
  cancelled: "status.cancelled",
} satisfies Record<string, MessageKey>;

const baselineKey: Record<string, MessageKey> = {
  no_trade: "paper.baseline.no_trade",
  market_follow: "paper.baseline.market_follow",
  fixed_threshold: "paper.baseline.fixed_threshold",
};

const alertKey: Record<string, MessageKey> = {
  high_exposure: "paper.alert.high_exposure",
  category_concentration: "paper.alert.category_concentration",
  drawdown_limit: "paper.alert.drawdown_limit",
  consecutive_losses: "paper.alert.consecutive_losses",
  rejected_trade: "paper.alert.rejected_trade",
  unsettled_resolution: "paper.alert.unsettled_resolution",
  other_outcome_pending: "paper.alert.other_outcome_pending",
  excessive_costs: "paper.alert.excessive_costs",
  stale_data: "paper.alert.stale_data",
  insufficient_closed_trades: "paper.alert.insufficient_closed_trades",
};
