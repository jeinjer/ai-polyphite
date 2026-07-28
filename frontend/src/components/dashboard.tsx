"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  Database,
  FlaskConical,
  Gauge,
  Globe2,
  History,
  Home,
  Info,
  Languages,
  LineChart as LineChartIcon,
  ListChecks,
  LoaderCircle,
  Menu,
  RefreshCw,
  Settings,
  ShieldAlert,
  SlidersHorizontal,
  TriangleAlert,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { educationalTextKeys } from "@/i18n/educational";
import { useI18n } from "@/i18n/i18n-provider";
import type { MessageKey } from "@/i18n/messages";
import { api } from "@/lib/api";
import type {
  ExperimentRun,
  HistoryEvent,
  Market,
  MarketStatus,
  Observation,
  ReplayDataset,
  ResolutionOutcome,
  SourceHealth,
  SyncRun,
} from "@/lib/api-types";
import {
  useUiStore,
  type DashboardSection,
} from "@/stores/ui-store";

const STALE_AFTER_MS = 15 * 60 * 1_000;

type Severity = "success" | "info" | "warning" | "error" | "neutral";

type MiniAlert = {
  id: string;
  severity: Severity;
  title: MessageKey;
  description: MessageKey;
  timestamp: string;
  action: MessageKey;
  actionSection: DashboardSection;
};

const navigation: {
  section: DashboardSection;
  label: MessageKey;
  icon: LucideIcon;
}[] = [
  { section: "home", label: "nav.home", icon: Home },
  { section: "markets", label: "nav.markets", icon: BarChart3 },
  { section: "history", label: "nav.history", icon: History },
  { section: "experiments", label: "nav.experiments", icon: FlaskConical },
  { section: "sources", label: "nav.sources", icon: Database },
  { section: "system", label: "nav.system", icon: Activity },
  { section: "settings", label: "nav.settings", icon: Settings },
];

export function Dashboard() {
  const { locale, setLocale, t } = useI18n();
  const {
    mode,
    section,
    selectedMarketId,
    setMode,
    setSection,
    selectMarket,
  } = useUiStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const marketsQuery = useQuery({ queryKey: ["markets"], queryFn: api.markets });
  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const runsQuery = useQuery({ queryKey: ["sync-runs"], queryFn: api.syncRuns });
  const experimentsQuery = useQuery({
    queryKey: ["experiment-runs"],
    queryFn: api.experimentRuns,
  });
  const datasetsQuery = useQuery({
    queryKey: ["replay-datasets"],
    queryFn: api.replayDatasets,
  });
  const markets = useMemo(
    () => marketsQuery.data?.items ?? [],
    [marketsQuery.data?.items],
  );
  const selectedMarket =
    markets.find((market) => market.market_id === selectedMarketId) ??
    markets[0] ??
    null;

  useEffect(() => {
    if (selectedMarketId === null && markets[0]) {
      selectMarket(markets[0].market_id);
    }
  }, [markets, selectMarket, selectedMarketId]);

  useEffect(() => {
    if (mode === "simple" && section === "experiments") {
      setSection("home");
    }
  }, [mode, section, setSection]);

  const observationsQuery = useQuery({
    queryKey: ["observations", selectedMarket?.market_id],
    queryFn: () => api.observations(selectedMarket?.market_id ?? ""),
    enabled: selectedMarket !== null,
  });
  const historyQuery = useQuery({
    queryKey: ["history", selectedMarket?.market_id],
    queryFn: () => api.history(selectedMarket?.market_id ?? ""),
    enabled: selectedMarket !== null,
  });

  const loading =
    marketsQuery.isLoading ||
    sourcesQuery.isLoading ||
    runsQuery.isLoading ||
    experimentsQuery.isLoading ||
    datasetsQuery.isLoading;
  const hasError =
    marketsQuery.isError ||
    sourcesQuery.isError ||
    runsQuery.isError ||
    experimentsQuery.isError ||
    datasetsQuery.isError;

  const retry = () => {
    void marketsQuery.refetch();
    void sourcesQuery.refetch();
    void runsQuery.refetch();
    void experimentsQuery.refetch();
    void datasetsQuery.refetch();
  };

  const selectSection = (nextSection: DashboardSection) => {
    setSection(nextSection);
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside
          className={`fixed inset-y-0 left-0 z-40 w-72 border-r border-white/8 bg-[#0a101a]/98 p-5 backdrop-blur-xl transition-transform lg:static lg:translate-x-0 ${
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
          aria-label={t("nav.home")}
        >
          <div className="flex items-center gap-3 px-2 py-3">
            <div className="grid size-10 place-items-center rounded-xl bg-cyan-400/12 text-cyan-300 ring-1 ring-cyan-300/20">
              <Gauge aria-hidden="true" className="size-5" />
            </div>
            <div>
              <p className="font-semibold tracking-tight">{t("app.name")}</p>
              <p className="text-xs text-slate-500">{t("app.subtitle")}</p>
            </div>
          </div>

          <nav className="mt-8 space-y-1">
            {navigation
              .filter(
                (item) => mode === "advanced" || item.section !== "experiments",
              )
              .map((item) => (
              <NavigationButton
                key={item.section}
                active={section === item.section}
                icon={item.icon}
                label={t(item.label)}
                onClick={() => selectSection(item.section)}
              />
              ))}
          </nav>

          <div className="mt-8 border-t border-white/8 pt-5">
            <button
              type="button"
              disabled
              title={t("nav.disabled")}
              className="flex w-full cursor-not-allowed items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-slate-600"
            >
              <SlidersHorizontal aria-hidden="true" className="size-4" />
              <span>
                {t("nav.simulation")}
                <span className="mt-1 block text-[11px] leading-4">
                  {t("nav.disabled")}
                </span>
              </span>
            </button>
          </div>

          <div className="absolute inset-x-5 bottom-5 rounded-xl border border-cyan-300/10 bg-cyan-300/5 p-3 text-xs leading-5 text-slate-400">
            <Info aria-hidden="true" className="mb-2 size-4 text-cyan-300" />
            {t("app.disclaimer")}
          </div>
        </aside>

        {mobileMenuOpen && (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-black/60 lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            aria-label={t("nav.home")}
          />
        )}

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-white/8 bg-[#070b12]/88 px-4 py-4 backdrop-blur-xl sm:px-7">
            <div className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(true)}
                  className="rounded-lg border border-white/10 p-2 text-slate-300 lg:hidden"
                  aria-label={t("nav.home")}
                >
                  <Menu aria-hidden="true" className="size-5" />
                </button>
                <div className="min-w-0">
                  <h1 className="truncate text-lg font-semibold sm:text-xl">
                    {mode === "simple"
                      ? t("header.simpleTitle")
                      : t("header.advancedTitle")}
                  </h1>
                  <p className="mt-1 hidden text-sm text-slate-500 sm:block">
                    {mode === "simple"
                      ? t("header.simpleDescription")
                      : t("header.advancedDescription")}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <div
                  className="flex rounded-xl border border-white/10 bg-white/[0.03] p-1"
                  aria-label={t("settings.view")}
                >
                  {(["simple", "advanced"] as const).map((view) => (
                    <button
                      key={view}
                      type="button"
                      aria-pressed={mode === view}
                      onClick={() => setMode(view)}
                      className={`rounded-lg px-3 py-2 text-xs font-medium transition ${
                        mode === view
                          ? "bg-cyan-400/15 text-cyan-200"
                          : "text-slate-500 hover:text-slate-200"
                      }`}
                    >
                      {t(view === "simple" ? "mode.simple" : "mode.advanced")}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setLocale(locale === "es-ES" ? "en-US" : "es-ES")
                  }
                  className="grid size-10 place-items-center rounded-xl border border-white/10 text-slate-400 transition hover:border-cyan-300/30 hover:text-cyan-200"
                  aria-label={t("language.label")}
                  title={t("language.label")}
                >
                  <Languages aria-hidden="true" className="size-4" />
                </button>
              </div>
            </div>
          </header>

          <div className="p-4 sm:p-7">
            {loading ? (
              <LoadingState />
            ) : hasError ? (
              <ErrorState onRetry={retry} />
            ) : (
              <DashboardContent
                section={section}
                mode={mode}
                markets={markets}
                sources={sourcesQuery.data ?? []}
                runs={runsQuery.data?.items ?? []}
                experiments={experimentsQuery.data?.items ?? []}
                datasets={datasetsQuery.data ?? []}
                selectedMarket={selectedMarket}
                observations={observationsQuery.data?.items ?? []}
                history={historyQuery.data?.items ?? []}
                observationsLoading={observationsQuery.isLoading}
                historyLoading={historyQuery.isLoading}
                onSelectMarket={(marketId) => {
                  selectMarket(marketId);
                  setSection("markets");
                }}
                onNavigate={setSection}
              />
            )}
          </div>
          <footer className="border-t border-white/8 px-7 py-5 text-xs text-slate-600">
            {t("footer.research")}
          </footer>
        </main>
      </div>
    </div>
  );
}

function DashboardContent({
  section,
  mode,
  markets,
  sources,
  runs,
  experiments,
  datasets,
  selectedMarket,
  observations,
  history,
  observationsLoading,
  historyLoading,
  onSelectMarket,
  onNavigate,
}: Readonly<{
  section: DashboardSection;
  mode: "simple" | "advanced";
  markets: Market[];
  sources: SourceHealth[];
  runs: SyncRun[];
  experiments: ExperimentRun[];
  datasets: ReplayDataset[];
  selectedMarket: Market | null;
  observations: Observation[];
  history: HistoryEvent[];
  observationsLoading: boolean;
  historyLoading: boolean;
  onSelectMarket: (marketId: string) => void;
  onNavigate: (section: DashboardSection) => void;
}>) {
  if (section === "markets") {
    return (
      <MarketsView
        markets={markets}
        selectedMarket={selectedMarket}
        observations={observations}
        history={history}
        mode={mode}
        observationsLoading={observationsLoading}
        onSelectMarket={onSelectMarket}
      />
    );
  }
  if (section === "history") {
    return (
      <HistoryView
        market={selectedMarket}
        observations={observations}
        history={history}
        runs={runs}
        loading={observationsLoading || historyLoading}
        advanced={mode === "advanced"}
      />
    );
  }
  if (section === "sources") {
    return <SourcesView sources={sources} />;
  }
  if (section === "experiments") {
    return <ExperimentsView datasets={datasets} experiments={experiments} />;
  }
  if (section === "system") {
    return (
      <SystemView
        sources={sources}
        runs={runs}
        markets={markets}
        advanced={mode === "advanced"}
      />
    );
  }
  if (section === "settings") {
    return <SettingsView />;
  }
  return (
    <Overview
      mode={mode}
      markets={markets}
      sources={sources}
      runs={runs}
      onSelectMarket={onSelectMarket}
      onNavigate={onNavigate}
    />
  );
}

function Overview({
  mode,
  markets,
  sources,
  runs,
  onSelectMarket,
  onNavigate,
}: Readonly<{
  mode: "simple" | "advanced";
  markets: Market[];
  sources: SourceHealth[];
  runs: SyncRun[];
  onSelectMarket: (marketId: string) => void;
  onNavigate: (section: DashboardSection) => void;
}>) {
  const { t } = useI18n();
  const latest = latestTimestamp(markets);
  const healthy = sources.length > 0 && sources.every((item) => item.status === "healthy");
  const historyCount = markets.filter((market) => market.latest_observation).length;
  const quality = markets.length ? Math.round((historyCount / markets.length) * 100) : 0;
  const changes = [...markets]
    .filter((market) => market.probability_change !== null)
    .sort(
      (left, right) =>
        Math.abs(Number(right.probability_change)) -
        Math.abs(Number(left.probability_change)),
    )
    .slice(0, 5);
  const alerts = buildAlerts(markets, sources, runs);

  return (
    <div className="space-y-7">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label={t("kpi.system")}
          value={t(healthy ? "status.healthy" : "status.degraded")}
          icon={healthy ? CheckCircle2 : TriangleAlert}
          severity={healthy ? "success" : "warning"}
          tooltip={t(educationalTextKeys.system)}
        />
        <KpiCard
          label={t("kpi.markets")}
          value={String(markets.length)}
          icon={BarChart3}
          severity="info"
        />
        <KpiCard
          label={t("kpi.open")}
          value={String(markets.filter((market) => market.status === "open").length)}
          icon={Activity}
          severity="info"
        />
        <KpiCard
          label={t("kpi.resolved")}
          value={String(
            markets.filter(
              (market) =>
                market.status === "resolved" || market.status === "cancelled",
            ).length,
          )}
          icon={ListChecks}
          severity="success"
        />
        <KpiCard
          label={t("kpi.sources")}
          value={String(sources.length)}
          icon={Database}
          severity="neutral"
        />
        <KpiCard
          label={t("kpi.lastUpdate")}
          value={latest ? formatRelative(latest, t) : t("kpi.noData")}
          icon={Clock3}
          severity={latest && isStale(latest) ? "warning" : "neutral"}
          tooltip={t(educationalTextKeys.stale)}
        />
        <KpiCard
          label={t("kpi.quality")}
          value={t("simple.percent", { value: quality })}
          icon={Gauge}
          severity={quality >= 75 ? "success" : "warning"}
          tooltip={t(educationalTextKeys.quality)}
        />
      </section>

      {mode === "simple" && (
        <section className="flex items-center gap-3 rounded-2xl border border-violet-300/15 bg-violet-300/[0.05] p-4 text-sm text-violet-100">
          <FlaskConical aria-hidden="true" className="size-5 text-violet-300" />
          <span>{t("simple.historicalAvailable")}</span>
          <InfoTooltip text={t(educationalTextKeys.replay)} />
        </section>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel
          title={t("section.changes")}
          icon={LineChartIcon}
          tooltip={t(educationalTextKeys.change)}
        >
          {changes.length ? (
            <div className="divide-y divide-white/7">
              {changes.map((market) => (
                <button
                  type="button"
                  key={market.market_id}
                  onClick={() => onSelectMarket(market.market_id)}
                  className="flex w-full items-center gap-4 py-4 text-left transition hover:bg-white/[0.025]"
                >
                  <ProbabilityRing probability={market.latest_observation?.probability} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{market.title}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {market.provider.name}
                    </p>
                  </div>
                  <TrendValue value={market.probability_change} />
                  <ChevronRight aria-hidden="true" className="size-4 text-slate-600" />
                </button>
              ))}
            </div>
          ) : (
            <EmptyState message={t("empty.observations")} />
          )}
        </Panel>

        <Panel title={t("section.alerts")} icon={ShieldAlert}>
          <AlertList alerts={alerts.slice(0, mode === "simple" ? 5 : 10)} onNavigate={onNavigate} />
        </Panel>
      </div>

      {mode === "advanced" && (
        <div className="grid gap-6 xl:grid-cols-2">
          <MarketTable markets={markets.slice(0, 10)} onSelect={onSelectMarket} />
          <SyncTable runs={runs.slice(0, 10)} advanced />
        </div>
      )}
    </div>
  );
}

function MarketsView({
  markets,
  selectedMarket,
  observations,
  history,
  mode,
  observationsLoading,
  onSelectMarket,
}: Readonly<{
  markets: Market[];
  selectedMarket: Market | null;
  observations: Observation[];
  history: HistoryEvent[];
  mode: "simple" | "advanced";
  observationsLoading: boolean;
  onSelectMarket: (marketId: string) => void;
}>) {
  const { locale, t } = useI18n();
  if (!markets.length) {
    return <EmptyState message={t("empty.markets")} />;
  }
  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <MarketTable markets={markets} onSelect={onSelectMarket} />
      {selectedMarket && (
        <div className="space-y-6">
          <Panel title={t("section.marketDetail")} icon={Info}>
            <div className="space-y-5">
              <div>
                <StatusBadge status={selectedMarket.status} />
                <h2 className="mt-3 text-xl font-semibold leading-8">
                  {selectedMarket.title}
                </h2>
                <p className="mt-3 text-sm leading-6 text-slate-400">
                  {selectedMarket.description ?? t("detail.noDescription")}
                </p>
              </div>
              <dl className="grid gap-4 sm:grid-cols-2">
                <DetailTerm
                  label={t("metrics.probability")}
                  value={formatProbability(
                    selectedMarket.latest_observation?.probability,
                  )}
                  tooltip={t(educationalTextKeys.probability)}
                />
                <DetailTerm
                  label={t("metrics.resolution")}
                  value={t(outcomeKey(selectedMarket.resolution_outcome))}
                  tooltip={t(educationalTextKeys.resolution)}
                />
                <DetailTerm
                  label={t("detail.category")}
                  value={selectedMarket.category ?? "—"}
                />
                <DetailTerm
                  label={t("table.source")}
                  value={selectedMarket.provider.name}
                />
                {mode === "advanced" && (
                  <>
                    <DetailTerm
                      label={t("metrics.volume")}
                      value={selectedMarket.latest_observation?.volume ?? "—"}
                      tooltip={t(educationalTextKeys.volume)}
                    />
                    <DetailTerm
                      label={t("metrics.liquidity")}
                      value={selectedMarket.latest_observation?.liquidity ?? "—"}
                      tooltip={t(educationalTextKeys.liquidity)}
                    />
                    <DetailTerm
                      label={t("detail.externalCreated")}
                      value={formatDate(
                        selectedMarket.source_created_at,
                        locale,
                      )}
                    />
                    <DetailTerm
                      label={t("detail.localIngested")}
                      value={formatDate(selectedMarket.ingested_at, locale)}
                    />
                    <DetailTerm
                      label={t("detail.scheduledClose")}
                      value={formatDate(selectedMarket.resolution_at, locale)}
                    />
                    <DetailTerm
                      label={t("detail.resolvedAt")}
                      value={formatDate(selectedMarket.resolved_at, locale)}
                    />
                    <DetailTerm
                      label={t("detail.resolutionSource")}
                      value={selectedMarket.resolution_source ?? "—"}
                    />
                  </>
                )}
              </dl>
            </div>
          </Panel>
          <ProbabilityChart observations={observations} loading={observationsLoading} />
          {mode === "advanced" && <Timeline events={history.slice(0, 12)} />}
        </div>
      )}
    </div>
  );
}

function HistoryView({
  market,
  observations,
  history,
  runs,
  loading,
  advanced,
}: Readonly<{
  market: Market | null;
  observations: Observation[];
  history: HistoryEvent[];
  runs: SyncRun[];
  loading: boolean;
  advanced: boolean;
}>) {
  const { t } = useI18n();
  const [tab, setTab] = useState<"changes" | "observations" | "syncs">("changes");
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2" role="tablist">
        {(
          [
            ["changes", "history.marketChanges"],
            ["observations", "history.observations"],
            ["syncs", "history.syncs"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
            className={`rounded-xl border px-4 py-2 text-sm ${
              tab === value
                ? "border-cyan-300/30 bg-cyan-300/10 text-cyan-200"
                : "border-white/10 text-slate-500"
            }`}
          >
            {t(label)}
          </button>
        ))}
      </div>
      {loading ? (
        <LoadingState compact />
      ) : tab === "syncs" ? (
        <SyncTable runs={runs} advanced={advanced} />
      ) : tab === "observations" ? (
        <ProbabilityChart observations={observations} loading={false} />
      ) : market ? (
        <Timeline events={history} />
      ) : (
        <EmptyState message={t("empty.markets")} />
      )}
    </div>
  );
}

function SourcesView({ sources }: Readonly<{ sources: SourceHealth[] }>) {
  const { t } = useI18n();
  if (!sources.length) {
    return <EmptyState message={t("empty.sources")} />;
  }
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {sources.map((source) => (
        <article
          key={source.code}
          className="rounded-2xl border border-white/8 bg-white/[0.025] p-5"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="grid size-10 place-items-center rounded-xl bg-blue-400/10 text-blue-300">
              <Globe2 aria-hidden="true" className="size-5" />
            </div>
            <HealthBadge status={source.status} />
          </div>
          <h2 className="mt-5 font-semibold">{source.name}</h2>
          <p className="mt-2 text-sm text-slate-500">
            {t("simple.updatedAgo", {
              value: formatRelative(source.checked_at, t),
            })}
          </p>
          <div className="mt-5 border-t border-white/7 pt-4 text-xs text-slate-500">
            {t("units.milliseconds", {
              value: Math.round(source.latency_ms),
            })}
          </div>
        </article>
      ))}
    </section>
  );
}

function SystemView({
  sources,
  runs,
  markets,
  advanced,
}: Readonly<{
  sources: SourceHealth[];
  runs: SyncRun[];
  markets: Market[];
  advanced: boolean;
}>) {
  const { t } = useI18n();
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Panel title={t("section.system")} icon={Activity}>
        <div className="space-y-3">
          {sources.map((source) => (
            <div
              key={source.code}
              className="flex items-center justify-between rounded-xl border border-white/7 p-4"
            >
              <div>
                <p className="text-sm font-medium">{source.name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {formatRelative(source.checked_at, t)}
                </p>
              </div>
              <HealthBadge status={source.status} />
            </div>
          ))}
        </div>
      </Panel>
      <Panel title={t("section.alerts")} icon={ShieldAlert}>
        <AlertList alerts={buildAlerts(markets, sources, runs)} onNavigate={() => undefined} />
      </Panel>
      {advanced && (
        <div className="xl:col-span-2">
          <SyncTable runs={runs} advanced />
        </div>
      )}
    </div>
  );
}

function ExperimentsView({
  datasets,
  experiments,
}: Readonly<{
  datasets: ReplayDataset[];
  experiments: ExperimentRun[];
}>) {
  const { locale, t } = useI18n();
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold">{t("section.experiments")}</h2>
          <InfoTooltip text={t(educationalTextKeys.replay)} />
        </div>
        <p className="mt-2 text-sm text-slate-500">
          {t("experiments.description")}
        </p>
      </div>

      <Panel title={t("section.datasets")} icon={Database}>
        {!datasets.length ? (
          <EmptyState message={t("empty.datasets")} />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {datasets.map((dataset) => (
              <article
                key={`${dataset.dataset_id}-${dataset.version}`}
                className="rounded-xl border border-white/8 bg-black/10 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium">{dataset.dataset_id}</h3>
                    <p className="mt-1 text-xs text-slate-500">
                      {t("experiments.version", { value: dataset.version })} ·{" "}
                      {t("experiments.schema", {
                        value: dataset.schema_version,
                      })}
                    </p>
                  </div>
                  <span className="rounded-lg bg-violet-300/10 px-2 py-1 text-xs text-violet-200">
                    {dataset.market_count} {t("table.markets").toLowerCase()}
                  </span>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-400">
                  {dataset.description}
                </p>
                <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                  <DetailTerm
                    label={t("table.range")}
                    value={`${formatDate(dataset.replay_start, locale)} — ${formatDate(
                      dataset.replay_end,
                      locale,
                    )}`}
                  />
                  <DetailTerm
                    label={t("history.observations")}
                    value={t("experiments.observationCount", {
                      value: dataset.observation_count,
                    })}
                  />
                </dl>
              </article>
            ))}
          </div>
        )}
      </Panel>

      <Panel title={t("section.experimentRuns")} icon={FlaskConical} flush>
        {!experiments.length ? (
          <EmptyState message={t("empty.experiments")} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-white/8 text-xs uppercase tracking-wider text-slate-600">
                <tr>
                  <th className="px-5 py-4 font-medium">{t("table.dataset")}</th>
                  <th className="px-3 py-4 font-medium">{t("table.result")}</th>
                  <th className="px-3 py-4 font-medium">{t("table.range")}</th>
                  <th className="px-3 py-4 font-medium">
                    {t("table.reproducible")}
                  </th>
                  <th className="px-5 py-4 font-medium">{t("table.started")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/6">
                {experiments.map((experiment) => (
                  <tr key={experiment.experiment_run_id}>
                    <td className="px-5 py-4">
                      <p className="font-medium">{experiment.dataset_id}</p>
                      <p className="mt-1 text-xs text-slate-600">
                        {t("experiments.version", {
                          value: experiment.dataset_version,
                        })}{" "}
                        · {t("experiments.seed")} {experiment.random_seed}
                      </p>
                      {experiment.safe_error_type && (
                        <p className="mt-2 text-xs text-red-300">
                          {t("advanced.errorType")}: {experiment.safe_error_type}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-4">
                      <RunBadge status={experiment.status} />
                    </td>
                    <td className="px-3 py-4 text-xs text-slate-500">
                      {formatDate(experiment.replay_start, locale)}
                      <span className="block">
                        {formatDate(experiment.replay_end, locale)}
                      </span>
                    </td>
                    <td className="px-3 py-4">
                      <span
                        className={
                          experiment.reproducible
                            ? "text-emerald-300"
                            : "text-slate-500"
                        }
                      >
                        {t(
                          experiment.reproducible
                            ? "experiments.yes"
                            : "experiments.no",
                        )}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-xs text-slate-500">
                      {formatDate(experiment.started_at, locale)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

function SettingsView() {
  const { locale, setLocale, t } = useI18n();
  const { mode, setMode } = useUiStore();
  return (
    <Panel title={t("settings.title")} icon={Settings}>
      <p className="mb-7 text-sm text-slate-500">{t("settings.description")}</p>
      <div className="grid gap-6 md:grid-cols-2">
        <fieldset>
          <legend className="mb-3 text-sm font-medium">{t("settings.view")}</legend>
          <div className="grid gap-2">
            {(["simple", "advanced"] as const).map((value) => (
              <PreferenceButton
                key={value}
                selected={mode === value}
                label={t(value === "simple" ? "mode.simple" : "mode.advanced")}
                onClick={() => setMode(value)}
              />
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="mb-3 text-sm font-medium">
            {t("settings.language")}
          </legend>
          <div className="grid gap-2">
            <PreferenceButton
              selected={locale === "es-ES"}
              label={t("language.spanish")}
              onClick={() => setLocale("es-ES")}
            />
            <PreferenceButton
              selected={locale === "en-US"}
              label={t("language.english")}
              onClick={() => setLocale("en-US")}
            />
          </div>
        </fieldset>
      </div>
    </Panel>
  );
}

function MarketTable({
  markets,
  onSelect,
}: Readonly<{ markets: Market[]; onSelect: (marketId: string) => void }>) {
  const { t } = useI18n();
  return (
    <Panel title={t("section.markets")} icon={BarChart3} flush>
      {!markets.length ? (
        <EmptyState message={t("empty.markets")} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="border-b border-white/8 text-xs uppercase tracking-wider text-slate-600">
              <tr>
                <th className="px-5 py-4 font-medium">{t("table.market")}</th>
                <th className="px-3 py-4 font-medium">{t("table.status")}</th>
                <th className="px-3 py-4 font-medium">
                  <span className="inline-flex items-center gap-1">
                    {t("table.probability")}
                    <InfoTooltip text={t(educationalTextKeys.probability)} />
                  </span>
                </th>
                <th className="px-3 py-4 font-medium">
                  <span className="inline-flex items-center gap-1">
                    {t("table.change")}
                    <InfoTooltip text={t(educationalTextKeys.change)} />
                  </span>
                </th>
                <th className="px-5 py-4 font-medium">{t("table.updated")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/6">
              {markets.map((market) => (
                <tr
                  key={market.market_id}
                  tabIndex={0}
                  onClick={() => onSelect(market.market_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      onSelect(market.market_id);
                    }
                  }}
                  className="cursor-pointer transition hover:bg-white/[0.025] focus:bg-cyan-300/5 focus:outline-none"
                >
                  <td className="max-w-md px-5 py-4">
                    <p className="truncate font-medium">{market.title}</p>
                    <p className="mt-1 text-xs text-slate-600">
                      {market.provider.name}
                    </p>
                  </td>
                  <td className="px-3 py-4">
                    <StatusBadge status={market.status} />
                  </td>
                  <td className="px-3 py-4 font-mono text-slate-300">
                    {formatProbability(market.latest_observation?.probability)}
                  </td>
                  <td className="px-3 py-4">
                    <TrendValue value={market.probability_change} />
                  </td>
                  <td className="px-5 py-4 text-xs text-slate-500">
                    {formatRelative(
                      market.latest_observation?.observed_at ?? market.updated_at,
                      t,
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function SyncTable({
  runs,
  advanced = false,
}: Readonly<{ runs: SyncRun[]; advanced?: boolean }>) {
  const { locale, t } = useI18n();
  return (
    <Panel title={t("section.syncs")} icon={RefreshCw} flush>
      {!runs.length ? (
        <EmptyState message={t("empty.syncs")} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="border-b border-white/8 text-xs uppercase tracking-wider text-slate-600">
              <tr>
                <th className="px-5 py-4 font-medium">{t("table.source")}</th>
                <th className="px-3 py-4 font-medium">{t("table.result")}</th>
                <th className="px-3 py-4 font-medium">{t("table.started")}</th>
                <th className="px-3 py-4 font-medium">{t("table.observations")}</th>
                <th className="px-5 py-4 font-medium">{t("table.duration")}</th>
                {advanced && (
                  <>
                    <th className="px-3 py-4 font-medium">
                      {t("table.retries")}
                    </th>
                    <th className="px-3 py-4 font-medium">
                      {t("advanced.errorType")}
                    </th>
                    <th className="px-5 py-4 font-medium">
                      {t("advanced.correlation")}
                    </th>
                  </>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/6">
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td className="px-5 py-4 font-medium">{run.provider_code}</td>
                  <td className="px-3 py-4">
                    <RunBadge status={run.status} />
                  </td>
                  <td className="px-3 py-4 text-xs text-slate-500">
                    {formatDate(run.started_at, locale)}
                  </td>
                  <td className="px-3 py-4 font-mono">{run.observations_created}</td>
                  <td className="px-5 py-4 text-xs text-slate-500">
                    {run.duration_ms === null
                      ? "—"
                      : t("units.milliseconds", {
                          value: Math.round(run.duration_ms),
                        })}
                  </td>
                  {advanced && (
                    <>
                      <td className="px-3 py-4 font-mono text-xs">
                        {run.retry_count}
                      </td>
                      <td className="px-3 py-4 text-xs text-slate-500">
                        {run.safe_error_type ?? t("advanced.noError")}
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-slate-600">
                        {run.correlation_id}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function ProbabilityChart({
  observations,
  loading,
}: Readonly<{ observations: Observation[]; loading: boolean }>) {
  const { locale, t } = useI18n();
  const data = useMemo(
    () =>
      [...observations]
        .reverse()
        .filter((item) => item.probability !== null)
        .map((item) => ({
          time: new Date(item.observed_at).toLocaleDateString(locale),
          probability: Number(item.probability) * 100,
        })),
    [locale, observations],
  );
  return (
    <Panel
      title={t("section.probabilityHistory")}
      icon={LineChartIcon}
      tooltip={t(educationalTextKeys.probability)}
    >
      {loading ? (
        <LoadingState compact />
      ) : !data.length ? (
        <EmptyState message={t("empty.observations")} />
      ) : (
        <div className="h-72 w-full" aria-label={t("section.probabilityHistory")}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="rgba(148,163,184,.08)" vertical={false} />
              <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickFormatter={(value: number) => `${value}%`}
              />
              <ChartTooltip
                contentStyle={{
                  background: "#0b1220",
                  border: "1px solid rgba(148,163,184,.15)",
                  borderRadius: "12px",
                }}
                formatter={(value) => [`${Number(value).toFixed(1)}%`, t("metrics.probability")]}
              />
              <Line
                type="monotone"
                dataKey="probability"
                name={t("metrics.probability")}
                stroke="#22d3ee"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5, fill: "#22d3ee" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}

function Timeline({ events }: Readonly<{ events: HistoryEvent[] }>) {
  const { locale, t } = useI18n();
  return (
    <Panel title={t("section.timeline")} icon={History}>
      {!events.length ? (
        <EmptyState message={t("empty.history")} />
      ) : (
        <ol className="relative ml-2 border-l border-white/10 pl-6">
          {events.map((event) => (
            <li key={`${event.event_type}-${event.event_id}`} className="pb-7 last:pb-0">
              <span className="absolute -left-1.5 mt-1.5 size-3 rounded-full border-2 border-[#0a101a] bg-cyan-300" />
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-medium">
                  {t(`timeline.${event.event_type}` as MessageKey)}
                </p>
                {event.status && <StatusBadge status={event.status} />}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {formatDate(event.occurred_at, locale)}
              </p>
              {event.probability !== null && (
                <p className="mt-2 font-mono text-sm text-cyan-200">
                  {formatProbability(event.probability)}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

function AlertList({
  alerts,
  onNavigate,
}: Readonly<{
  alerts: MiniAlert[];
  onNavigate: (section: DashboardSection) => void;
}>) {
  const { t } = useI18n();
  return (
    <div className="space-y-3">
      {alerts.map((alert) => {
        return (
          <article
            key={alert.id}
            className={`rounded-xl border p-4 ${severityClasses(alert.severity)}`}
          >
            <div className="flex gap-3">
              <SeverityIcon
                severity={alert.severity}
                className="mt-0.5 size-4 shrink-0"
              />
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium">{t(alert.title)}</h3>
                <p className="mt-1 text-xs leading-5 opacity-75">
                  {t(alert.description)}
                </p>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <time className="text-[11px] opacity-60" dateTime={alert.timestamp}>
                    {formatRelative(alert.timestamp, t)}
                  </time>
                  <button
                    type="button"
                    onClick={() => onNavigate(alert.actionSection)}
                    className="text-xs font-medium underline decoration-current/30 underline-offset-4"
                  >
                    {t(alert.action)}
                  </button>
                </div>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function KpiCard({
  label,
  value,
  icon: Icon,
  severity,
  tooltip,
}: Readonly<{
  label: string;
  value: string;
  icon: LucideIcon;
  severity: Severity;
  tooltip?: string;
}>) {
  return (
    <article className="rounded-2xl border border-white/8 bg-white/[0.025] p-5 shadow-2xl shadow-black/5">
      <div className="flex items-center justify-between">
        <div className={`grid size-9 place-items-center rounded-xl ${iconClasses(severity)}`}>
          <Icon aria-hidden="true" className="size-4" />
        </div>
        {tooltip && <InfoTooltip text={tooltip} />}
      </div>
      <p className="mt-5 text-xs font-medium uppercase tracking-[0.14em] text-slate-600">
        {label}
      </p>
      <p className="mt-2 text-xl font-semibold tracking-tight">{value}</p>
    </article>
  );
}

function Panel({
  title,
  icon: Icon,
  children,
  tooltip,
  flush = false,
}: Readonly<{
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  tooltip?: string;
  flush?: boolean;
}>) {
  return (
    <section className="overflow-hidden rounded-2xl border border-white/8 bg-white/[0.025]">
      <header className="flex items-center gap-2 border-b border-white/7 px-5 py-4">
        <Icon aria-hidden="true" className="size-4 text-cyan-300" />
        <h2 className="text-sm font-semibold">{title}</h2>
        {tooltip && <InfoTooltip text={tooltip} />}
      </header>
      <div className={flush ? "" : "p-5"}>{children}</div>
    </section>
  );
}

function NavigationButton({
  active,
  icon: Icon,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${
        active
          ? "bg-cyan-300/10 text-cyan-100 ring-1 ring-inset ring-cyan-300/10"
          : "text-slate-500 hover:bg-white/[0.035] hover:text-slate-200"
      }`}
    >
      <Icon aria-hidden="true" className="size-4" />
      {label}
    </button>
  );
}

function StatusBadge({ status }: Readonly<{ status: MarketStatus }>) {
  const { t } = useI18n();
  const styles: Record<MarketStatus, string> = {
    open: "border-blue-300/20 bg-blue-300/8 text-blue-200",
    closed: "border-amber-300/20 bg-amber-300/8 text-amber-200",
    resolved: "border-emerald-300/20 bg-emerald-300/8 text-emerald-200",
    cancelled: "border-slate-400/20 bg-slate-400/8 text-slate-300",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] ${styles[status]}`}
      aria-label={t(statusKey(status))}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {t(statusKey(status))}
    </span>
  );
}

function HealthBadge({ status }: Readonly<{ status: SourceHealth["status"] }>) {
  const { t } = useI18n();
  const healthy = status === "healthy";
  const degraded = status === "degraded";
  const label = healthy
    ? t("status.healthy")
    : degraded
      ? t("status.degraded")
      : t("status.unavailable");
  const Icon = healthy ? CheckCircle2 : degraded ? AlertTriangle : XCircle;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] ${
        healthy
          ? "border-emerald-300/20 bg-emerald-300/8 text-emerald-200"
          : degraded
            ? "border-amber-300/20 bg-amber-300/8 text-amber-200"
            : "border-red-300/20 bg-red-300/8 text-red-200"
      }`}
      aria-label={label}
    >
      <Icon aria-hidden="true" className="size-3" />
      {label}
    </span>
  );
}

function RunBadge({ status }: Readonly<{ status: SyncRun["status"] }>) {
  const { t } = useI18n();
  const severity: Severity =
    status === "completed"
      ? "success"
      : status === "failed"
        ? "error"
        : status === "running"
          ? "info"
          : "neutral";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] ${severityClasses(severity)}`}
      aria-label={t(`status.${status}` as MessageKey)}
    >
      <SeverityIcon severity={severity} className="size-3" />
      {t(`status.${status}` as MessageKey)}
    </span>
  );
}

function DetailTerm({
  label,
  value,
  tooltip,
}: Readonly<{ label: string; value: string; tooltip?: string }>) {
  return (
    <div className="rounded-xl border border-white/7 bg-black/10 p-3">
      <dt className="flex items-center gap-1 text-xs text-slate-500">
        {label}
        {tooltip && <InfoTooltip text={tooltip} />}
      </dt>
      <dd className="mt-2 break-words text-sm text-slate-200">{value}</dd>
    </div>
  );
}

function InfoTooltip({ text }: Readonly<{ text: string }>) {
  const { t } = useI18n();
  return (
    <span
      tabIndex={0}
      title={text}
      aria-label={`${t("simple.explanation")}: ${text}`}
      className="inline-grid size-5 cursor-help place-items-center rounded-full text-slate-600 outline-none transition hover:text-cyan-300 focus:ring-2 focus:ring-cyan-300/40"
    >
      <CircleHelp aria-hidden="true" className="size-3.5" />
    </span>
  );
}

function ProbabilityRing({ probability }: Readonly<{ probability?: string | null }>) {
  const { t } = useI18n();
  const percentage = probability === null || probability === undefined
    ? null
    : Math.round(Number(probability) * 100);
  return (
    <div
      className="grid size-11 shrink-0 place-items-center rounded-full border border-cyan-300/20 bg-cyan-300/7 font-mono text-xs text-cyan-200"
      aria-label={
        percentage === null
          ? t("kpi.noData")
          : t("simple.probabilityValue", { value: percentage })
      }
    >
      {percentage === null ? "—" : `${percentage}%`}
    </div>
  );
}

function TrendValue({ value }: Readonly<{ value: string | null }>) {
  if (value === null) {
    return <span className="text-xs text-slate-600">—</span>;
  }
  const numeric = Number(value) * 100;
  const positive = numeric >= 0;
  return (
    <span
      className={`rounded-lg px-2 py-1 font-mono text-xs ${
        positive ? "bg-emerald-300/8 text-emerald-300" : "bg-red-300/8 text-red-300"
      }`}
      aria-label={`${positive ? "+" : ""}${numeric.toFixed(1)}%`}
    >
      {positive ? "+" : ""}
      {numeric.toFixed(1)}%
    </span>
  );
}

function PreferenceButton({
  selected,
  label,
  onClick,
}: Readonly<{ selected: boolean; label: string; onClick: () => void }>) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`flex items-center justify-between rounded-xl border p-4 text-left text-sm ${
        selected
          ? "border-cyan-300/30 bg-cyan-300/8 text-cyan-100"
          : "border-white/8 text-slate-400"
      }`}
    >
      {label}
      {selected && <CheckCircle2 aria-hidden="true" className="size-4" />}
    </button>
  );
}

function LoadingState({ compact = false }: Readonly<{ compact?: boolean }>) {
  const { t } = useI18n();
  return (
    <div
      className={`grid gap-4 ${compact ? "py-8" : "sm:grid-cols-2 xl:grid-cols-4"}`}
      aria-live="polite"
      aria-label={t("loading.label")}
    >
      {Array.from({ length: compact ? 1 : 8 }, (_, index) => (
        <div
          key={index}
          className="h-32 animate-pulse rounded-2xl border border-white/6 bg-white/[0.025]"
        />
      ))}
      <span className="sr-only">{t("loading.label")}</span>
    </div>
  );
}

function EmptyState({ message }: Readonly<{ message: string }>) {
  return (
    <div className="grid min-h-44 place-items-center px-6 text-center">
      <div>
        <Database aria-hidden="true" className="mx-auto size-6 text-slate-700" />
        <p className="mt-3 text-sm text-slate-500">{message}</p>
      </div>
    </div>
  );
}

function ErrorState({ onRetry }: Readonly<{ onRetry: () => void }>) {
  const { t } = useI18n();
  return (
    <div
      role="alert"
      className="mx-auto mt-20 max-w-lg rounded-2xl border border-red-300/15 bg-red-300/5 p-7 text-center"
    >
      <XCircle aria-hidden="true" className="mx-auto size-7 text-red-300" />
      <h2 className="mt-4 font-semibold">{t("error.title")}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">
        {t("error.description")}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-5 inline-flex items-center gap-2 rounded-xl bg-red-300/10 px-4 py-2 text-sm text-red-200"
      >
        <RefreshCw aria-hidden="true" className="size-4" />
        {t("error.retry")}
      </button>
    </div>
  );
}

function buildAlerts(
  markets: Market[],
  sources: SourceHealth[],
  runs: SyncRun[],
): MiniAlert[] {
  const now = new Date().toISOString();
  const alerts: MiniAlert[] = [];
  if (sources.some((source) => source.status === "unhealthy")) {
    alerts.push(alert("source-unavailable", "error", "sourceUnavailable", now, "sources"));
  }
  if (sources.some((source) => source.status === "degraded")) {
    alerts.push(alert("source-degraded", "warning", "sourceDegraded", now, "sources"));
  }
  const latest = latestTimestamp(markets);
  if (latest && isStale(latest)) {
    alerts.push(alert("stale", "warning", "stale", latest, "markets"));
  }
  if (runs.some((run) => run.status === "running")) {
    alerts.push(alert("running", "info", "running", now, "system"));
  }
  const latestRun = runs[0];
  if (latestRun?.status === "failed") {
    alerts.push(alert("failed", "error", "failed", latestRun.started_at, "system"));
  }
  if (latestRun && latestRun.observations_skipped > 0) {
    alerts.push(alert("skipped", "warning", "skipped", latestRun.started_at, "history"));
  }
  if (
    markets.some(
      (market) =>
        market.status === "closed" && market.resolution_outcome === "unresolved",
    )
  ) {
    alerts.push(alert("closed", "warning", "closed", now, "markets"));
  }
  if (markets.some((market) => market.resolution_outcome === "other")) {
    alerts.push(alert("incompatible", "warning", "incompatible", now, "markets"));
  }
  if (markets.some((market) => market.latest_observation === null)) {
    alerts.push(alert("no-history", "neutral", "noHistory", now, "history"));
  }
  alerts.push(alert("informational", "info", "informational", now, "markets"));
  return alerts;
}

function alert(
  id: string,
  severity: Severity,
  kind:
    | "sourceUnavailable"
    | "sourceDegraded"
    | "stale"
    | "running"
    | "failed"
    | "skipped"
    | "closed"
    | "incompatible"
    | "noHistory"
    | "informational",
  timestamp: string,
  actionSection: DashboardSection,
): MiniAlert {
  const action: Record<DashboardSection, MessageKey> = {
    home: "alerts.action.system",
    markets: "alerts.action.markets",
    history: "alerts.action.history",
    experiments: "alerts.action.history",
    sources: "alerts.action.sources",
    system: "alerts.action.system",
    settings: "alerts.action.system",
  };
  return {
    id,
    severity,
    title: `alerts.title.${kind}` as MessageKey,
    description: `alerts.description.${kind}` as MessageKey,
    timestamp,
    action: action[actionSection],
    actionSection,
  };
}

function latestTimestamp(markets: Market[]): string | null {
  const timestamps = markets.map(
    (market) => market.latest_observation?.observed_at ?? market.updated_at,
  );
  return timestamps.length
    ? timestamps.sort((left, right) => Date.parse(right) - Date.parse(left))[0]
    : null;
}

function isStale(timestamp: string): boolean {
  return Date.now() - Date.parse(timestamp) > STALE_AFTER_MS;
}

function formatRelative(
  timestamp: string,
  t: ReturnType<typeof useI18n>["t"],
): string {
  const seconds = Math.max(0, Math.floor((Date.now() - Date.parse(timestamp)) / 1_000));
  if (seconds < 60) return t("time.justNow");
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return t("time.minutes", { value: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("time.hours", { value: hours });
  return t("time.days", { value: Math.floor(hours / 24) });
}

function formatDate(value: string | null, locale: string): string {
  return value ? new Date(value).toLocaleString(locale) : "—";
}

function formatProbability(value: string | null | undefined): string {
  return value === null || value === undefined
    ? "—"
    : `${(Number(value) * 100).toFixed(1)}%`;
}

function statusKey(status: MarketStatus): MessageKey {
  return `status.${status}` as MessageKey;
}

function outcomeKey(outcome: ResolutionOutcome): MessageKey {
  return `outcome.${outcome}` as MessageKey;
}

function SeverityIcon({
  severity,
  className,
}: Readonly<{ severity: Severity; className: string }>) {
  if (severity === "success") {
    return <CheckCircle2 aria-hidden="true" className={className} />;
  }
  if (severity === "error") {
    return <XCircle aria-hidden="true" className={className} />;
  }
  if (severity === "warning") {
    return <AlertTriangle aria-hidden="true" className={className} />;
  }
  if (severity === "info") {
    return <Info aria-hidden="true" className={className} />;
  }
  return <LoaderCircle aria-hidden="true" className={className} />;
}

function severityClasses(severity: Severity): string {
  if (severity === "success") return "border-emerald-300/15 bg-emerald-300/5 text-emerald-200";
  if (severity === "error") return "border-red-300/15 bg-red-300/5 text-red-200";
  if (severity === "warning") return "border-amber-300/15 bg-amber-300/5 text-amber-200";
  if (severity === "info") return "border-blue-300/15 bg-blue-300/5 text-blue-200";
  return "border-slate-300/10 bg-slate-300/[0.03] text-slate-300";
}

function iconClasses(severity: Severity): string {
  if (severity === "success") return "bg-emerald-300/8 text-emerald-300";
  if (severity === "error") return "bg-red-300/8 text-red-300";
  if (severity === "warning") return "bg-amber-300/8 text-amber-300";
  if (severity === "info") return "bg-blue-300/8 text-blue-300";
  return "bg-slate-300/8 text-slate-400";
}
