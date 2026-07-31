"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleDollarSign,
  Globe2,
  Languages,
  Menu,
  Radar,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  WalletCards,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";

import { PredictionsWorkspace } from "@/components/predictions-workspace";
import { useI18n } from "@/i18n/i18n-provider";
import type { MessageKey } from "@/i18n/messages";
import { api } from "@/lib/api";
import type {
  EquityCurvePoint,
  Market,
  PaperPerformance,
  PaperPortfolio,
  PaperPosition,
  PaperTrade,
  SourceHealth,
  SyncRun,
} from "@/lib/api-types";

type ExecutiveSection = "overview" | "predictions" | "trades" | "markets";
type TradeFilter = "all" | "automatic" | "manual_override";

const navigation: {
  section: ExecutiveSection;
  href: string;
  label: MessageKey;
  icon: LucideIcon;
}[] = [
  { section: "overview", href: "/", label: "exec.nav.overview", icon: BarChart3 },
  {
    section: "predictions",
    href: "/predictions",
    label: "exec.nav.opportunities",
    icon: Target,
  },
  { section: "trades", href: "/trades", label: "exec.nav.activity", icon: Zap },
  { section: "markets", href: "/markets", label: "exec.nav.markets", icon: Globe2 },
];

export function ExecutiveDashboard() {
  const pathname = usePathname();
  const { locale, setLocale, t } = useI18n();
  const pathParts = pathname.split("/").filter(Boolean);
  const section = executiveSection(pathParts[0]);
  const predictionId = section === "predictions" ? pathParts[1] ?? null : null;
  const marketId = section === "markets" ? pathParts[1] ?? null : null;
  const [menuOpen, setMenuOpen] = useState(false);

  const marketsQuery = useQuery({ queryKey: ["markets"], queryFn: api.markets });
  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const runsQuery = useQuery({ queryKey: ["sync-runs"], queryFn: api.syncRuns });
  const portfoliosQuery = useQuery({
    queryKey: ["paper-portfolios"],
    queryFn: api.paperPortfolios,
  });
  const portfolio = useMemo(
    () => preferredPortfolio(portfoliosQuery.data?.items ?? []),
    [portfoliosQuery.data?.items],
  );
  const performanceQuery = useQuery({
    queryKey: ["paper-performance", portfolio?.portfolio_id],
    queryFn: () => api.paperPerformance(portfolio?.portfolio_id ?? ""),
    enabled: portfolio !== null,
  });
  const tradesQuery = useQuery({
    queryKey: ["paper-trades", portfolio?.portfolio_id],
    queryFn: () => api.paperTrades(portfolio?.portfolio_id ?? ""),
    enabled: portfolio !== null,
  });
  const positionsQuery = useQuery({
    queryKey: ["paper-positions", portfolio?.portfolio_id],
    queryFn: () => api.paperPositions(portfolio?.portfolio_id ?? ""),
    enabled: portfolio !== null,
  });
  const equityQuery = useQuery({
    queryKey: ["paper-equity", portfolio?.portfolio_id],
    queryFn: () => api.paperEquityCurve(portfolio?.portfolio_id ?? ""),
    enabled: portfolio !== null,
  });

  const commonLoading =
    marketsQuery.isLoading ||
    sourcesQuery.isLoading ||
    runsQuery.isLoading ||
    portfoliosQuery.isLoading;
  const commonError =
    marketsQuery.isError ||
    sourcesQuery.isError ||
    runsQuery.isError ||
    portfoliosQuery.isError;

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-[#182033]">
      <PointerAura />
      <header className="sticky top-0 z-40 border-b border-[#182033]/8 bg-[#f5f2ea]/90 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-[1440px] items-center gap-4 px-4 sm:px-7">
          <Link
            href="/"
            className="group flex cursor-pointer items-center gap-3 rounded-2xl outline-none"
            onClick={() => setMenuOpen(false)}
          >
            <span className="grid size-11 place-items-center rounded-2xl bg-[#5b43f1] text-white shadow-[0_10px_30px_rgba(91,67,241,.28)] transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-105 group-active:scale-95">
              <Sparkles aria-hidden="true" className="size-5" />
            </span>
            <span>
              <span className="block text-base font-black tracking-[-0.03em]">
                AI-Polyphite
              </span>
              <span className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-[#777b87]">
                {t("exec.brand.subtitle")}
              </span>
            </span>
          </Link>

          <nav className="mx-auto hidden items-center gap-1 rounded-2xl border border-[#182033]/8 bg-white/70 p-1.5 shadow-sm lg:flex">
            {navigation.map((item) => (
              <TopNavigationItem key={item.section} item={item} active={section === item.section} />
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2 lg:ml-0">
            <SystemPill
              sources={sourcesQuery.data ?? []}
              latestRun={runsQuery.data?.items[0] ?? null}
              compact
            />
            <button
              type="button"
              className="interactive-button grid size-11 cursor-pointer place-items-center rounded-2xl border border-[#182033]/10 bg-white text-[#5b43f1] shadow-sm"
              aria-label={t("language.label")}
              title={t("language.label")}
              onClick={() => setLocale(locale === "es-ES" ? "en-US" : "es-ES")}
            >
              <Languages aria-hidden="true" className="size-5" />
            </button>
            <button
              type="button"
              className="interactive-button grid size-11 cursor-pointer place-items-center rounded-2xl border border-[#182033]/10 bg-white text-[#182033] shadow-sm lg:hidden"
              aria-label={t("exec.nav.menu")}
              onClick={() => setMenuOpen((value) => !value)}
            >
              {menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav className="animate-slide-down border-t border-[#182033]/8 bg-[#f5f2ea] p-3 lg:hidden">
            <div className="mx-auto grid max-w-[1440px] grid-cols-2 gap-2">
              {navigation.map((item) => (
                <MobileNavigationItem
                  key={item.section}
                  item={item}
                  active={section === item.section}
                  onClick={() => setMenuOpen(false)}
                />
              ))}
            </div>
          </nav>
        )}
      </header>

      <main className="mx-auto min-h-[calc(100vh-80px)] max-w-[1440px] px-4 py-7 sm:px-7 sm:py-10">
        {section === "predictions" ? (
          <PredictionsWorkspace predictionId={predictionId} />
        ) : commonLoading ? (
          <ExecutiveLoading />
        ) : commonError ? (
          <ExecutiveError />
        ) : section === "trades" ? (
          <ActivityView />
        ) : section === "markets" ? (
          <MarketsView
            markets={marketsQuery.data?.items ?? []}
            marketId={marketId}
          />
        ) : (
          <Overview
            marketsTotal={marketsQuery.data?.total ?? 0}
            sources={sourcesQuery.data ?? []}
            latestRun={runsQuery.data?.items[0] ?? null}
            portfolio={portfolio}
            performance={performanceQuery.data ?? null}
            trades={tradesQuery.data?.items ?? []}
            tradeTotal={tradesQuery.data?.total ?? 0}
            positions={positionsQuery.data?.items ?? []}
            equity={equityQuery.data ?? []}
            loading={
              performanceQuery.isLoading ||
              tradesQuery.isLoading ||
              positionsQuery.isLoading ||
              equityQuery.isLoading
            }
          />
        )}
      </main>

      <footer className="border-t border-[#182033]/8 bg-white/40 px-4 py-6 text-center text-xs font-medium text-[#777b87]">
        {t("exec.footer")}
      </footer>
    </div>
  );
}

function Overview({
  marketsTotal,
  sources,
  latestRun,
  portfolio,
  performance,
  trades,
  tradeTotal,
  positions,
  equity,
  loading,
}: Readonly<{
  marketsTotal: number;
  sources: SourceHealth[];
  latestRun: SyncRun | null;
  portfolio: PaperPortfolio | null;
  performance: PaperPerformance | null;
  trades: PaperTrade[];
  tradeTotal: number;
  positions: PaperPosition[];
  equity: EquityCurvePoint[];
  loading: boolean;
}>) {
  const { locale, t } = useI18n();
  const healthy = systemHealthy(sources, latestRun);
  const netProfit = Number(performance?.metrics.net_profit ?? 0);
  const openPositions = positions.filter((item) => item.status === "open").length;
  const lastActivity = latestRun?.finished_at ?? latestRun?.started_at ?? null;

  return (
    <div className="space-y-8 animate-page-in">
      <section className="relative overflow-hidden rounded-[2rem] bg-[#182033] px-6 py-8 text-white shadow-[0_24px_70px_rgba(24,32,51,.18)] sm:px-10 sm:py-11">
        <div className="pointer-events-none absolute -right-20 -top-24 size-80 rounded-full bg-[#ff7759]/25 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-1/3 size-80 rounded-full bg-[#5b43f1]/35 blur-3xl" />
        <div className="relative grid items-end gap-8 lg:grid-cols-[1fr_auto]">
          <div className="max-w-3xl">
            <div className="mb-5 flex flex-wrap items-center gap-3">
              <SystemPill sources={sources} latestRun={latestRun} />
              <span className="rounded-full border border-white/15 bg-white/8 px-3 py-1.5 text-xs font-bold text-white/75">
                {t("exec.simulation.badge")}
              </span>
            </div>
            <h1 className="max-w-2xl text-3xl font-black tracking-[-0.045em] sm:text-5xl">
              {healthy ? t("exec.hero.healthy") : t("exec.hero.attention")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-white/68 sm:text-lg">
              {healthy ? t("exec.hero.healthyDescription") : t("exec.hero.attentionDescription")}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-4">
              <Link
                href="/predictions"
                className="interactive-button inline-flex cursor-pointer items-center gap-2 rounded-2xl bg-[#ff7759] px-5 py-3 text-sm font-black text-white shadow-[0_12px_30px_rgba(255,119,89,.25)]"
              >
                <Target className="size-4" />
                {t("exec.hero.cta")}
                <ArrowRight className="size-4" />
              </Link>
              <span className="text-sm font-semibold text-white/55">
                {lastActivity
                  ? t("exec.hero.updated", {
                      value: relativeTime(lastActivity, locale),
                    })
                  : t("exec.hero.waiting")}
              </span>
            </div>
          </div>
          <div className="rounded-3xl border border-white/12 bg-white/8 p-5 backdrop-blur-sm sm:min-w-64">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/50">
              {t("exec.hero.currentResult")}
            </p>
            <p className={`mt-2 text-4xl font-black ${netProfit >= 0 ? "text-[#72e0b1]" : "text-[#ff9a85]"}`}>
              {loading ? "—" : signedCredits(netProfit, locale)}
            </p>
            <p className="mt-2 text-sm text-white/55">{t("exec.hero.resultHelp")}</p>
          </div>
        </div>
      </section>

      <section>
        <SectionHeading
          eyebrow={t("exec.overview.eyebrow")}
          title={t("exec.overview.title")}
          description={t("exec.overview.description")}
        />
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ExecutiveMetric
            icon={CircleDollarSign}
            color="violet"
            label={t("exec.metric.result")}
            value={loading ? "—" : signedCredits(netProfit, locale)}
            help={t("exec.metric.resultHelp")}
          />
          <ExecutiveMetric
            icon={Zap}
            color="orange"
            label={t("exec.metric.trades")}
            value={loading ? "—" : String(tradeTotal)}
            help={t("exec.metric.tradesHelp")}
          />
          <ExecutiveMetric
            icon={WalletCards}
            color="green"
            label={t("exec.metric.open")}
            value={loading ? "—" : String(openPositions)}
            help={t("exec.metric.openHelp")}
          />
          <ExecutiveMetric
            icon={Radar}
            color="blue"
            label={t("exec.metric.markets")}
            value={String(marketsTotal)}
            help={t("exec.metric.marketsHelp")}
          />
        </div>
      </section>

      <div className="grid min-w-0 gap-6 xl:grid-cols-[1.15fr_.85fr]">
        <CapitalPanel equity={equity} portfolio={portfolio} />
        <RecentActivity trades={trades.slice(0, 4)} portfolio={portfolio} />
      </div>

      <section className="rounded-[2rem] border border-[#182033]/8 bg-white p-6 shadow-[0_18px_50px_rgba(24,32,51,.06)] sm:p-8">
        <SectionHeading
          eyebrow={t("exec.how.eyebrow")}
          title={t("exec.how.title")}
          description={t("exec.how.description")}
        />
        <div className="mt-7 grid gap-4 md:grid-cols-3">
          <SimpleStep number="01" icon={Globe2} title={t("exec.how.observe")} text={t("exec.how.observeText")} />
          <SimpleStep number="02" icon={BrainCircuit} title={t("exec.how.decide")} text={t("exec.how.decideText")} />
          <SimpleStep number="03" icon={TrendingUp} title={t("exec.how.simulate")} text={t("exec.how.simulateText")} />
        </div>
      </section>
    </div>
  );
}

function ActivityView() {
  const { locale, t } = useI18n();
  const [filter, setFilter] = useState<TradeFilter>("all");
  const tradesQuery = useQuery({
    queryKey: ["all-paper-trades"],
    queryFn: api.allPaperTrades,
  });
  const positionsQuery = useQuery({
    queryKey: ["all-paper-positions"],
    queryFn: api.allPaperPositions,
  });
  const positions = positionsQuery.data?.items ?? [];
  const positionByTrade = new Map(positions.map((item) => [item.trade_id, item]));
  const trades = (tradesQuery.data?.items ?? [])
    .filter((item) => item.experiment_run_id === null)
    .filter((item) => filter === "all" || item.decision_source === filter);

  return (
    <div className="space-y-7 animate-page-in">
      <SectionHeading
        eyebrow={t("exec.activity.eyebrow")}
        title={t("exec.activity.title")}
        description={t("exec.activity.description")}
      />
      <div className="flex flex-wrap gap-2">
        {(["all", "automatic", "manual_override"] as const).map((value) => (
          <button
            key={value}
            type="button"
            className={`interactive-button cursor-pointer rounded-full px-4 py-2 text-sm font-bold ${
              filter === value
                ? "bg-[#182033] text-white shadow-lg"
                : "border border-[#182033]/10 bg-white text-[#626777]"
            }`}
            onClick={() => setFilter(value)}
          >
            {t(
              value === "all"
                ? "exec.filter.all"
                : value === "automatic"
                  ? "exec.filter.automatic"
                  : "exec.filter.manual",
            )}
          </button>
        ))}
      </div>

      {tradesQuery.isLoading || positionsQuery.isLoading ? (
        <ExecutiveLoading compact />
      ) : trades.length === 0 ? (
        <EmptyPanel icon={Activity} title={t("exec.activity.empty")} text={t("exec.activity.emptyText")} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {trades.map((trade) => (
            <TradeCard
              key={trade.trade_id}
              trade={trade}
              position={positionByTrade.get(trade.trade_id) ?? null}
              locale={locale}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MarketsView({
  markets,
  marketId,
}: Readonly<{ markets: Market[]; marketId: string | null }>) {
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  if (marketId) {
    return <MarketDetail market={markets.find((item) => item.market_id === marketId) ?? null} />;
  }
  const visible = markets.filter((market) =>
    market.title.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
  );
  return (
    <div className="space-y-7 animate-page-in">
      <SectionHeading
        eyebrow={t("exec.markets.eyebrow")}
        title={t("exec.markets.title")}
        description={t("exec.markets.description")}
      />
      <label className="relative block max-w-xl">
        <Search className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-[#8b8e98]" />
        <span className="sr-only">{t("exec.markets.search")}</span>
        <input
          className="w-full rounded-2xl border border-[#182033]/10 bg-white py-3.5 pl-12 pr-4 text-sm font-semibold shadow-sm outline-none transition focus:border-[#5b43f1]/50 focus:ring-4 focus:ring-[#5b43f1]/10"
          value={search}
          placeholder={t("exec.markets.search")}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>
      {visible.length === 0 ? (
        <EmptyPanel icon={Search} title={t("exec.markets.empty")} text={t("exec.markets.emptyText")} />
      ) : (
        <div className="overflow-hidden rounded-[2rem] border border-[#182033]/8 bg-white shadow-[0_18px_50px_rgba(24,32,51,.06)]">
          {visible.map((market) => (
            <MarketRow key={market.market_id} market={market} />
          ))}
        </div>
      )}
    </div>
  );
}

function MarketDetail({ market }: Readonly<{ market: Market | null }>) {
  const { locale, t } = useI18n();
  const observationsQuery = useQuery({
    queryKey: ["observations", market?.market_id],
    queryFn: () => api.observations(market?.market_id ?? ""),
    enabled: market !== null,
  });
  if (!market) {
    return <EmptyPanel icon={Globe2} title={t("exec.market.missing")} text={t("exec.market.missingText")} />;
  }
  const chart = [...(observationsQuery.data?.items ?? [])]
    .reverse()
    .filter((item) => item.probability !== null)
    .map((item) => ({
      date: new Date(item.observed_at).toLocaleDateString(locale, { month: "short", day: "numeric" }),
      probability: Number(item.probability) * 100,
    }));
  return (
    <div className="space-y-7 animate-page-in">
      <Link href="/markets" className="inline-flex cursor-pointer items-center gap-2 text-sm font-black text-[#5b43f1] transition hover:gap-3">
        <ArrowRight className="size-4 rotate-180" /> {t("exec.market.back")}
      </Link>
      <section className="rounded-[2rem] bg-[#182033] p-7 text-white shadow-xl sm:p-10">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <StatusChip status={market.status} />
            <h1 className="mt-5 text-3xl font-black tracking-[-0.04em] sm:text-4xl">{market.title}</h1>
            {market.description && <p className="mt-4 line-clamp-3 leading-7 text-white/62">{market.description}</p>}
          </div>
          <ProbabilityDisplay value={market.latest_observation?.probability ?? null} dark />
        </div>
      </section>
      <section className="rounded-[2rem] border border-[#182033]/8 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-black">{t("exec.market.evolution")}</h2>
        <p className="mt-1 text-sm text-[#777b87]">{t("exec.market.evolutionHelp")}</p>
        <div className="mt-6 h-72">
          {observationsQuery.isLoading ? (
            <ExecutiveLoading compact />
          ) : chart.length < 2 ? (
            <div className="grid h-full place-items-center text-sm font-semibold text-[#8b8e98]">{t("exec.market.noHistory")}</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chart}>
                <defs>
                  <linearGradient id="marketFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#5b43f1" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#5b43f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "#8b8e98", fontSize: 11 }} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, t("exec.metric.probability")]} />
                <Area type="monotone" dataKey="probability" stroke="#5b43f1" strokeWidth={3} fill="url(#marketFill)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
    </div>
  );
}

function CapitalPanel({ equity, portfolio }: Readonly<{ equity: EquityCurvePoint[]; portfolio: PaperPortfolio | null }>) {
  const { locale, t } = useI18n();
  const chart = equity.map((item) => ({
    date: new Date(item.recorded_at).toLocaleDateString(locale, { month: "short", day: "numeric" }),
    value: Number(item.equity),
  }));
  return (
    <section className="min-w-0 rounded-[2rem] border border-[#182033]/8 bg-white p-6 shadow-[0_18px_50px_rgba(24,32,51,.06)] sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-[#5b43f1]">{t("exec.capital.eyebrow")}</p>
          <h2 className="mt-2 text-xl font-black">{t("exec.capital.title")}</h2>
        </div>
        <span className="rounded-full bg-[#e9fff4] px-3 py-1.5 text-xs font-black text-[#16845f]">{t("exec.capital.simulated")}</span>
      </div>
      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-black tracking-[-0.04em]">{portfolio ? credits(Number(portfolio.equity), locale) : "—"}</span>
        <span className="text-xs font-bold text-[#8b8e98]">{t("exec.capital.credits")}</span>
      </div>
      <div className="mt-5 h-56">
        {chart.length < 2 ? (
          <div className="grid h-full place-items-center rounded-2xl bg-[#f7f5f0] text-center text-sm font-semibold text-[#8b8e98]">{t("exec.capital.collecting")}</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chart}>
              <defs>
                <linearGradient id="capitalFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ff7759" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#ff7759" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "#999ca5", fontSize: 11 }} />
              <Tooltip formatter={(value) => [credits(Number(value), locale), t("exec.capital.title")]} />
              <Area type="monotone" dataKey="value" stroke="#ff7759" strokeWidth={3} fill="url(#capitalFill)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}

function RecentActivity({ trades, portfolio }: Readonly<{ trades: PaperTrade[]; portfolio: PaperPortfolio | null }>) {
  const { locale, t } = useI18n();
  return (
    <section className="min-w-0 rounded-[2rem] border border-[#182033]/8 bg-white p-6 shadow-[0_18px_50px_rgba(24,32,51,.06)] sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-[#ff7759]">{t("exec.recent.eyebrow")}</p>
          <h2 className="mt-2 text-xl font-black">{t("exec.recent.title")}</h2>
        </div>
        <Link href="/trades" className="interactive-button grid size-10 cursor-pointer place-items-center rounded-full bg-[#f5f2ea] text-[#182033]">
          <ArrowRight className="size-4" />
          <span className="sr-only">{t("exec.recent.all")}</span>
        </Link>
      </div>
      {trades.length === 0 ? (
        <div className="mt-8 rounded-2xl bg-[#f7f5f0] p-6 text-center text-sm font-semibold text-[#8b8e98]">{t("exec.recent.empty")}</div>
      ) : (
        <div className="mt-5 divide-y divide-[#182033]/7">
          {trades.map((trade) => (
            <div key={trade.trade_id} className="flex items-center gap-3 py-4 first:pt-0 last:pb-0">
              <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${trade.side === "yes" ? "bg-[#e9fff4] text-[#16845f]" : "bg-[#fff0ec] text-[#d95034]"}`}>
                {trade.side === "yes" ? <Check className="size-4" /> : <X className="size-4" />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-black">{trade.market_title}</p>
                <p className="mt-1 text-xs font-semibold text-[#8b8e98]">
                  {t(trade.side === "yes" ? "exec.side.yes" : "exec.side.no")} · {relativeTime(trade.executed_at, locale)}
                </p>
              </div>
              <span className="text-sm font-black text-[#626777]">{credits(Number(trade.maximum_loss), locale)}</span>
            </div>
          ))}
        </div>
      )}
      {portfolio && <p className="mt-6 text-xs font-semibold text-[#a0a2aa]">{t("exec.recent.portfolio")}</p>}
    </section>
  );
}

function TradeCard({ trade, position, locale }: Readonly<{ trade: PaperTrade; position: PaperPosition | null; locale: "es-ES" | "en-US" }>) {
  const { t } = useI18n();
  const result = position?.status === "open" ? null : Number(position?.realized_pnl ?? 0);
  return (
    <article className="executive-card group rounded-[1.6rem] border border-[#182033]/8 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <span className={`grid size-11 shrink-0 place-items-center rounded-2xl ${trade.side === "yes" ? "bg-[#e9fff4] text-[#16845f]" : "bg-[#fff0ec] text-[#d95034]"}`}>
          {trade.side === "yes" ? <Check className="size-5" /> : <X className="size-5" />}
        </span>
        <span className={`rounded-full px-3 py-1.5 text-xs font-black ${trade.decision_source === "automatic" ? "bg-[#eeeaff] text-[#5b43f1]" : "bg-[#fff3d6] text-[#9b6a00]"}`}>
          {t(trade.decision_source === "automatic" ? "exec.filter.automatic" : "exec.filter.manual")}
        </span>
      </div>
      <h2 className="mt-5 line-clamp-2 text-lg font-black leading-6 tracking-[-0.02em]">{trade.market_title}</h2>
      <p className="mt-2 text-sm font-semibold text-[#8b8e98]">{relativeTime(trade.executed_at, locale)}</p>
      <div className="mt-5 grid grid-cols-3 gap-3 rounded-2xl bg-[#f7f5f0] p-4">
        <PlainValue label={t("exec.activity.choice")} value={t(trade.side === "yes" ? "exec.side.yes" : "exec.side.no")} />
        <PlainValue label={t("exec.activity.risk")} value={credits(Number(trade.maximum_loss), locale)} />
        <PlainValue
          label={t("exec.activity.result")}
          value={result === null ? t("exec.activity.inProgress") : signedCredits(result, locale)}
          positive={result !== null ? result >= 0 : undefined}
        />
      </div>
      <Link href={`/predictions/${encodeURIComponent(trade.prediction_run_id)}`} className="mt-5 inline-flex cursor-pointer items-center gap-2 text-sm font-black text-[#5b43f1] transition-all group-hover:gap-3">
        {t("exec.activity.understand")} <ChevronRight className="size-4" />
      </Link>
    </article>
  );
}

function MarketRow({ market }: Readonly<{ market: Market }>) {
  const { t } = useI18n();
  return (
    <Link
      href={`/markets/${encodeURIComponent(market.market_id)}`}
      className="group grid cursor-pointer items-center gap-4 border-b border-[#182033]/7 px-5 py-5 transition duration-300 last:border-0 hover:bg-[#f8f6ff] sm:grid-cols-[1fr_auto_auto] sm:px-7"
    >
      <div className="min-w-0">
        <h2 className="line-clamp-2 font-black leading-6 transition-colors group-hover:text-[#5b43f1]">{market.title}</h2>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-bold text-[#8b8e98]">
          <StatusChip status={market.status} compact />
          {market.category && <span>{market.category}</span>}
        </div>
      </div>
      <div className="flex items-center justify-between gap-5 sm:justify-end">
        <div className="text-right">
          <p className="text-xs font-bold text-[#8b8e98]">{t("exec.metric.probability")}</p>
          <p className="mt-1 text-xl font-black">{probability(market.latest_observation?.probability ?? null)}</p>
        </div>
        <span className={`text-sm font-black ${Number(market.probability_change ?? 0) >= 0 ? "text-[#16845f]" : "text-[#d95034]"}`}>
          {market.probability_change ? signedPoints(market.probability_change) : "—"}
        </span>
      </div>
      <ChevronRight className="hidden size-5 text-[#b3b4bb] transition-transform group-hover:translate-x-1 sm:block" />
    </Link>
  );
}

function ExecutiveMetric({ icon: Icon, color, label, value, help }: Readonly<{ icon: LucideIcon; color: "violet" | "orange" | "green" | "blue"; label: string; value: string; help: string }>) {
  const colors = {
    violet: "bg-[#eeeaff] text-[#5b43f1]",
    orange: "bg-[#fff0ec] text-[#e45c3f]",
    green: "bg-[#e9fff4] text-[#16845f]",
    blue: "bg-[#e8f5ff] text-[#2077a8]",
  };
  return (
    <article className="executive-card rounded-[1.6rem] border border-[#182033]/8 bg-white p-5 shadow-sm sm:p-6">
      <span className={`grid size-11 place-items-center rounded-2xl ${colors[color]}`}><Icon className="size-5" /></span>
      <p className="mt-5 text-sm font-bold text-[#777b87]">{label}</p>
      <p className="mt-1 text-3xl font-black tracking-[-0.04em]">{value}</p>
      <p className="mt-2 text-xs font-medium leading-5 text-[#a0a2aa]">{help}</p>
    </article>
  );
}

function SimpleStep({ number, icon: Icon, title, text }: Readonly<{ number: string; icon: LucideIcon; title: string; text: string }>) {
  return (
    <article className="relative overflow-hidden rounded-3xl bg-[#f7f5f0] p-5">
      <span className="absolute right-4 top-2 text-5xl font-black text-[#182033]/5">{number}</span>
      <span className="grid size-11 place-items-center rounded-2xl bg-white text-[#5b43f1] shadow-sm"><Icon className="size-5" /></span>
      <h3 className="mt-5 font-black">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-[#777b87]">{text}</p>
    </article>
  );
}

function PlainValue({ label, value, positive }: Readonly<{ label: string; value: string; positive?: boolean }>) {
  return (
    <div className="min-w-0">
      <p className="truncate text-[10px] font-black uppercase tracking-[0.1em] text-[#9a9ca5]">{label}</p>
      <p className={`mt-1 truncate text-sm font-black ${positive === undefined ? "text-[#182033]" : positive ? "text-[#16845f]" : "text-[#d95034]"}`}>{value}</p>
    </div>
  );
}

function SectionHeading({ eyebrow, title, description }: Readonly<{ eyebrow: string; title: string; description: string }>) {
  return (
    <div className="max-w-3xl">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-[#5b43f1]">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-black tracking-[-0.04em] sm:text-4xl">{title}</h1>
      <p className="mt-3 text-base leading-7 text-[#777b87]">{description}</p>
    </div>
  );
}

function SystemPill({ sources, latestRun, compact = false }: Readonly<{ sources: SourceHealth[]; latestRun: SyncRun | null; compact?: boolean }>) {
  const { t } = useI18n();
  const healthy = systemHealthy(sources, latestRun);
  return (
    <span
      className={`items-center gap-2 rounded-full font-black ${
        compact
          ? "hidden border border-[#182033]/8 bg-white px-3 py-2 text-xs text-[#626777] sm:inline-flex"
          : "inline-flex border border-white/15 bg-white/8 px-3 py-1.5 text-xs text-white"
      }`}
      aria-label={healthy ? t("exec.status.healthy") : t("exec.status.attention")}
    >
      <span className={`relative size-2 rounded-full ${healthy ? "bg-[#37c98b]" : "bg-[#ff8a70]"}`}>
        <span className={`absolute inset-0 animate-ping rounded-full opacity-50 ${healthy ? "bg-[#37c98b]" : "bg-[#ff8a70]"}`} />
      </span>
      {healthy ? t("exec.status.healthy") : t("exec.status.attention")}
    </span>
  );
}

function StatusChip({ status, compact = false }: Readonly<{ status: Market["status"]; compact?: boolean }>) {
  const { t } = useI18n();
  const label = t(
    status === "open"
      ? "exec.market.open"
      : status === "resolved"
        ? "exec.market.resolved"
        : status === "cancelled"
          ? "exec.market.cancelled"
          : "exec.market.closed",
  );
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-black ${compact ? "px-2 py-1 text-[10px]" : "bg-white/10 px-3 py-1.5 text-xs text-white"} ${compact ? (status === "open" ? "bg-[#e9fff4] text-[#16845f]" : "bg-[#f0f0f2] text-[#777b87]") : ""}`}>
      <span className={`size-1.5 rounded-full ${status === "open" ? "bg-[#37c98b]" : "bg-current"}`} /> {label}
    </span>
  );
}

function ProbabilityDisplay({ value, dark = false }: Readonly<{ value: string | null; dark?: boolean }>) {
  const { t } = useI18n();
  return (
    <div className={`min-w-40 rounded-3xl p-5 text-center ${dark ? "border border-white/12 bg-white/8" : "bg-[#f7f5f0]"}`}>
      <p className={`text-xs font-black uppercase tracking-[0.12em] ${dark ? "text-white/50" : "text-[#8b8e98]"}`}>{t("exec.metric.probability")}</p>
      <p className="mt-2 text-4xl font-black">{probability(value)}</p>
    </div>
  );
}

function EmptyPanel({ icon: Icon, title, text }: Readonly<{ icon: LucideIcon; title: string; text: string }>) {
  return (
    <div className="grid min-h-72 place-items-center rounded-[2rem] border border-dashed border-[#182033]/15 bg-white/60 p-8 text-center">
      <div>
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#eeeaff] text-[#5b43f1]"><Icon className="size-6" /></span>
        <h2 className="mt-5 text-xl font-black">{title}</h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#777b87]">{text}</p>
      </div>
    </div>
  );
}

function ExecutiveLoading({ compact = false }: Readonly<{ compact?: boolean }>) {
  const { t } = useI18n();
  return (
    <div className={`grid place-items-center ${compact ? "min-h-56" : "min-h-[65vh]"}`} aria-label={t("loading.label")}>
      <div className="text-center">
        <span className="mx-auto grid size-14 animate-pulse place-items-center rounded-2xl bg-[#eeeaff] text-[#5b43f1]"><Radar className="size-6 animate-spin-slow" /></span>
        <p className="mt-4 text-sm font-black text-[#777b87]">{t("exec.loading")}</p>
      </div>
    </div>
  );
}

function ExecutiveError() {
  const { t } = useI18n();
  return (
    <div className="grid min-h-[65vh] place-items-center">
      <div className="max-w-lg rounded-[2rem] border border-[#ff7759]/20 bg-white p-8 text-center shadow-xl">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#fff0ec] text-[#d95034]"><AlertTriangle className="size-6" /></span>
        <h1 className="mt-5 text-2xl font-black">{t("exec.error.title")}</h1>
        <p className="mt-3 leading-7 text-[#777b87]">{t("exec.error.description")}</p>
        <button type="button" className="interactive-button mt-6 cursor-pointer rounded-2xl bg-[#182033] px-5 py-3 text-sm font-black text-white" onClick={() => window.location.reload()}>{t("error.retry")}</button>
      </div>
    </div>
  );
}

function TopNavigationItem({ item, active }: Readonly<{ item: (typeof navigation)[number]; active: boolean }>) {
  const { t } = useI18n();
  const Icon = item.icon;
  return (
    <Link href={item.href} className={`interactive-button flex cursor-pointer items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-black ${active ? "bg-[#182033] text-white shadow-lg" : "text-[#777b87] hover:bg-white hover:text-[#182033]"}`}>
      <Icon className="size-4" /> {t(item.label)}
    </Link>
  );
}

function MobileNavigationItem({ item, active, onClick }: Readonly<{ item: (typeof navigation)[number]; active: boolean; onClick: () => void }>) {
  const { t } = useI18n();
  const Icon = item.icon;
  return (
    <Link href={item.href} onClick={onClick} className={`interactive-button flex cursor-pointer items-center gap-3 rounded-2xl p-4 text-sm font-black ${active ? "bg-[#182033] text-white" : "bg-white text-[#626777]"}`}>
      <Icon className="size-5" /> {t(item.label)}
    </Link>
  );
}

function PointerAura() {
  const aura = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const move = (event: PointerEvent) => {
      aura.current?.style.setProperty("--pointer-x", `${event.clientX}px`);
      aura.current?.style.setProperty("--pointer-y", `${event.clientY}px`);
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, []);
  return <div ref={aura} className="pointer-aura" aria-hidden="true" />;
}

function preferredPortfolio(portfolios: PaperPortfolio[]): PaperPortfolio | null {
  return (
    portfolios.find((item) => item.name.toLowerCase().includes("autonomous manifold")) ??
    portfolios.find((item) => item.status === "active" && !item.name.toLowerCase().includes("manual") && !item.name.toLowerCase().includes("experimental")) ??
    portfolios[0] ??
    null
  );
}

function executiveSection(value: string | undefined): ExecutiveSection {
  if (value === "predictions" || value === "trades" || value === "markets") return value;
  return "overview";
}

function systemHealthy(sources: SourceHealth[], latestRun: SyncRun | null): boolean {
  return sources.length > 0 && sources.every((item) => item.status === "healthy") && latestRun?.status === "completed";
}

function probability(value: string | null): string {
  if (value === null) return "—";
  return `${(Number(value) * 100).toFixed(0)}%`;
}

function signedPoints(value: string): string {
  const points = Number(value) * 100;
  return `${points >= 0 ? "+" : ""}${points.toFixed(1)} pp`;
}

function credits(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}

function signedCredits(value: number, locale: string): string {
  return `${value >= 0 ? "+" : ""}${credits(value, locale)}`;
}

function relativeTime(value: string, locale: string): string {
  const milliseconds = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(milliseconds / 60_000));
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (minutes < 60) return formatter.format(-minutes, "minute");
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return formatter.format(-hours, "hour");
  return formatter.format(-Math.floor(hours / 24), "day");
}
