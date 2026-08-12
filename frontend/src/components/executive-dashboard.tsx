"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  Bot,
  BriefcaseBusiness,
  CalendarDays,
  ChartNoAxesCombined,
  CircleHelp,
  DatabaseZap,
  FlaskConical,
  Gauge,
  Info,
  Moon,
  Pause,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Sun,
  Target,
  TrendingDown,
  TrendingUp,
  WalletCards,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PredictionsWorkspace } from "@/components/predictions-workspace";
import { api } from "@/lib/api";
import type {
  AutomationState,
  EquityCurvePoint,
  PaperPerformance,
  PaperPortfolio,
  PaperPosition,
  PaperTrade,
  PredictionListItem,
  PredictionEvaluation,
  SourceHealth,
  SyncRun,
} from "@/lib/api-types";

type Section = "overview" | "predictions" | "activity";
const DISPLAY_TIME_ZONE = "Europe/Paris";

const navigation: { section: Section; href: string; label: string; icon: LucideIcon }[] = [
  { section: "overview", href: "/", label: "Resumen", icon: Gauge },
  { section: "predictions", href: "/predictions", label: "Predicciones", icon: Target },
  { section: "activity", href: "/trades", label: "Actividad", icon: Activity },
];

export function ExecutiveDashboard() {
  const pathname = usePathname();
  const parts = pathname.split("/").filter(Boolean);
  const section = currentSection(parts[0]);
  const predictionId = section === "predictions" ? parts[1] ?? null : null;
  const [dark, setDark] = useState(false);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const stored = localStorage.getItem("ai-polyphite-theme");
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const frame = window.requestAnimationFrame(() => {
      setDark(stored ? stored === "dark" : preferred);
    });
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("ai-polyphite-theme", dark ? "dark" : "light");
  }, [dark]);

  const sources = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const runs = useQuery({ queryKey: ["sync-runs"], queryFn: api.syncRuns });
  const portfolios = useQuery({ queryKey: ["paper-portfolios"], queryFn: api.paperPortfolios });
  const portfolio = useMemo(() => preferredPortfolio(portfolios.data?.items ?? []), [portfolios.data?.items]);
  const performance = useQuery({ queryKey: ["paper-performance", portfolio?.portfolio_id], queryFn: () => api.paperPerformance(portfolio?.portfolio_id ?? ""), enabled: portfolio !== null });
  const trades = useQuery({ queryKey: ["paper-trades", portfolio?.portfolio_id], queryFn: () => api.paperTrades(portfolio?.portfolio_id ?? ""), enabled: portfolio !== null });
  const positions = useQuery({ queryKey: ["paper-positions", portfolio?.portfolio_id], queryFn: () => api.paperPositions(portfolio?.portfolio_id ?? ""), enabled: portfolio !== null });
  const equity = useQuery({ queryKey: ["paper-equity", portfolio?.portfolio_id], queryFn: () => api.paperEquityCurve(portfolio?.portfolio_id ?? ""), enabled: portfolio !== null });
  const latestPredictions = useQuery({ queryKey: ["latest-predictions"], queryFn: () => api.predictions("page=1&page_size=25&sort=predicted_at&direction=desc") });
  const todayPredictions = useQuery({ queryKey: ["today-predictions", dayKey(now)], queryFn: () => api.predictions(`page=1&page_size=25&sort=predicted_at&direction=desc&date_from=${encodeURIComponent(startOfDay(now))}`) });
  const actionableToday = useQuery({ queryKey: ["actionable-today", dayKey(now)], queryFn: () => api.predictions(`page=1&page_size=25&sort=predicted_at&direction=desc&commercial_label=actionable&date_from=${encodeURIComponent(startOfDay(now))}`) });
  const automation = useQuery({ queryKey: ["automation"], queryFn: api.automation });
  const evaluation = useQuery({
    queryKey: ["prediction-evaluation"],
    queryFn: api.predictionEvaluation,
  });

  const loading = sources.isLoading || runs.isLoading || portfolios.isLoading;
  const error = sources.isError || runs.isError || portfolios.isError;
  const latestCompletedRun = runs.data?.items.find((run) => run.status === "completed") ?? null;
  const latestRun = runs.data?.items[0] ?? null;
  const lastPrediction = latestPredictions.data?.items[0]?.predicted_at ?? null;

  return (
    <div className="app-shell min-h-screen bg-app text-default">
      <Sidebar section={section} automation={automation.data ?? null} />
      <div className="min-w-0 lg:pl-[224px]">
        <TopBar
          portfolio={portfolio}
          now={now}
          latestData={latestCompletedRun?.finished_at ?? latestCompletedRun?.started_at ?? null}
          latestPrediction={lastPrediction}
          dark={dark}
          onTheme={() => setDark((value) => !value)}
        />
        <main className="mx-auto min-h-[calc(100vh-72px)] max-w-[1320px] px-4 py-6 sm:px-6 lg:px-8">
          {section === "predictions" ? (
            <PredictionsWorkspace predictionId={predictionId} />
          ) : loading ? (
            <Loading />
          ) : error ? (
            <StatePanel title="No se pudo cargar el tablero" text="El backend no respondió. El refresco automático seguirá intentando." />
          ) : section === "activity" ? (
            <ActivityView trades={trades.data?.items ?? []} positions={positions.data?.items ?? []} />
          ) : (
            <Overview
              sources={sources.data ?? []}
              latestRun={latestRun}
              latestCompletedRun={latestCompletedRun}
              portfolio={portfolio}
              performance={performance.data ?? null}
              predictions={latestPredictions.data?.items ?? []}
              predictionsToday={todayPredictions.data?.total_items ?? 0}
              actionableToday={actionableToday.data?.total_items ?? 0}
              trades={trades.data?.items ?? []}
              positions={positions.data?.items ?? []}
              equity={equity.data ?? []}
              automation={automation.data ?? null}
              evaluation={evaluation.data ?? null}
            />
          )}
        </main>
      </div>
      <MobileNavigation section={section} />
    </div>
  );
}

function Sidebar({ section, automation }: Readonly<{ section: Section; automation: AutomationState | null }>) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[224px] flex-col border-r border-sidebar-line bg-sidebar text-sidebar lg:flex">
      <Link href="/" className="flex h-[72px] items-center gap-3 border-b border-sidebar-line px-5">
        <span className="grid size-9 place-items-center rounded-lg bg-accent text-white"><Sparkles className="size-4" /></span>
        <span><strong className="block text-sm tracking-[-.02em]">AI-Polyphite</strong><small className="block text-[10px] uppercase tracking-[.14em] text-sidebar-muted">Paper research</small></span>
      </Link>
      <nav className="space-y-1 p-3">
        {navigation.map((item) => <NavigationItem key={item.section} item={item} active={section === item.section} />)}
      </nav>
      <div className="mt-auto p-4">
        <div className="rounded-xl border border-sidebar-line bg-sidebar-soft p-3 text-xs leading-5 text-sidebar-muted">
          <div className="mb-1.5 flex items-center gap-2 font-semibold text-sidebar"><FlaskConical className="size-3.5 text-accent" /> 100% simulado</div>
          No hay dinero real, wallets ni ejecución externa.
        </div>
        <div className={`mt-3 flex items-center gap-2 text-xs font-semibold ${automation?.paused ? "text-warning" : "text-positive"}`}>
          <span className={`size-2 rounded-full ${automation?.paused ? "bg-warning" : "animate-pulse bg-positive"}`} />
          {automation?.paused ? "Automatización pausada" : "Automatización activa"}
        </div>
      </div>
    </aside>
  );
}

function NavigationItem({ item, active }: Readonly<{ item: (typeof navigation)[number]; active: boolean }>) {
  const Icon = item.icon;
  return <Link href={item.href} className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition ${active ? "bg-sidebar-active text-white" : "text-sidebar-muted hover:bg-sidebar-soft hover:text-white"}`}><Icon className="size-4" />{item.label}</Link>;
}

function MobileNavigation({ section }: Readonly<{ section: Section }>) {
  return <nav className="fixed inset-x-3 bottom-3 z-50 flex justify-around rounded-2xl border border-line bg-panel/95 p-1.5 shadow-2xl backdrop-blur lg:hidden">{navigation.map((item) => { const Icon = item.icon; const active = item.section === section; return <Link key={item.section} href={item.href} className={`flex min-w-20 flex-col items-center gap-1 rounded-xl px-3 py-2 text-[10px] font-semibold ${active ? "bg-accent text-white" : "text-muted"}`}><Icon className="size-4" />{item.label}</Link>; })}</nav>;
}

function TopBar({ portfolio, now, latestData, latestPrediction, dark, onTheme }: Readonly<{ portfolio: PaperPortfolio | null; now: Date; latestData: string | null; latestPrediction: string | null; dark: boolean; onTheme: () => void }>) {
  const invested = Number(portfolio?.reserved_balance ?? 0);
  const reserve = Number(portfolio?.cash_balance ?? 0);
  const delta = Number(portfolio?.equity ?? 0) - Number(portfolio?.initial_balance ?? 0);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-panel/92 backdrop-blur-xl">
      <div className="flex min-h-[72px] items-center gap-3 overflow-x-auto px-4 sm:px-6 lg:px-8">
        <Link href="/" className="mr-2 flex shrink-0 items-center gap-2 lg:hidden"><span className="grid size-8 place-items-center rounded-lg bg-accent text-white"><Sparkles className="size-4" /></span><strong className="text-sm">AI-Polyphite</strong></Link>
        <MoneyPill icon={BriefcaseBusiness} label="Invertido" value={money(invested)} tone="neutral" help="Capital virtual actualmente comprometido en posiciones abiertas." />
        <MoneyPill icon={WalletCards} label="Reserva" value={money(reserve)} tone="neutral" help="Capital virtual disponible para futuras operaciones." />
        <MoneyPill icon={delta >= 0 ? TrendingUp : TrendingDown} label="Diferencia" value={signedMoney(delta)} tone={delta > 0 ? "positive" : delta < 0 ? "negative" : "neutral"} help="Diferencia entre el capital virtual actual y el inicial." />
        <div className="ml-auto flex shrink-0 items-center gap-4 border-l border-line pl-4 text-[11px] text-muted">
          <TimeLabel icon={CalendarDays} label="Ahora" value={fullDate(now)} />
          <TimeLabel icon={DatabaseZap} label="Últimos datos" value={shortDate(latestData)} />
          <TimeLabel icon={Bot} label="Última predicción" value={shortDate(latestPrediction)} />
          <button type="button" className="icon-button" onClick={onTheme} aria-label="Cambiar tema" title="Cambiar entre tema claro y oscuro">{dark ? <Sun className="size-4" /> : <Moon className="size-4" />}</button>
        </div>
      </div>
    </header>
  );
}

function Overview({ sources, latestRun, latestCompletedRun, portfolio, performance, predictions, predictionsToday, actionableToday, trades, positions, equity, automation, evaluation }: Readonly<{ sources: SourceHealth[]; latestRun: SyncRun | null; latestCompletedRun: SyncRun | null; portfolio: PaperPortfolio | null; performance: PaperPerformance | null; predictions: PredictionListItem[]; predictionsToday: number; actionableToday: number; trades: PaperTrade[]; positions: PaperPosition[]; equity: EquityCurvePoint[]; automation: AutomationState | null; evaluation: PredictionEvaluation | null }>) {
  const status = operationalStatus(sources, latestRun, latestCompletedRun, automation);
  const openPositions = positions.filter((item) => item.status === "open");
  const automaticTrades = trades.filter((item) => item.decision_source === "automatic" && item.experiment_run_id === null);
  return (
    <div className="page-enter space-y-6">
      <section className="flex flex-col gap-4 border-b border-line pb-6 md:flex-row md:items-end md:justify-between">
        <div><p className="eyebrow">Estado general</p><h1 className="mt-1 text-3xl font-bold tracking-[-.04em] text-strong">{status.title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{status.description}</p></div>
        <AutomationControl state={automation} />
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi icon={ChartNoAxesCombined} label="Resultado" value={signedMoney(Number(portfolio?.equity ?? 0) - Number(portfolio?.initial_balance ?? 0))} help="Ganancia o pérdida virtual total, incluyendo posiciones abiertas." />
        <Kpi icon={BriefcaseBusiness} label="Posiciones abiertas" value={String(openPositions.length)} help="Operaciones automáticas esperando un resultado oficial." />
        <Kpi icon={Bot} label="Predicciones hoy" value={String(predictionsToday)} help="Análisis nuevos creados desde el inicio del día local." />
        <Kpi icon={Target} label="Oportunidades hoy" value={String(actionableToday)} help="Predicciones que superaron costos, confianza y reglas comerciales." />
      </div>

      <LearningStrip evaluation={evaluation} />

      <section className="panel p-5 md:p-6">
        <SectionTitle icon={RefreshCw} title="Qué está haciendo ahora" subtitle="Cada etapa muestra trabajo real del último ciclo, no actividad inventada." />
        <div className="mt-5 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-4">
          <FunnelStep number="1" label="Mercados leídos" value={latestCompletedRun?.markets_fetched ?? 0} detail="Última consulta pública" />
          <FunnelStep number="2" label="Datos nuevos" value={(latestCompletedRun?.markets_created ?? 0) + (latestCompletedRun?.markets_updated ?? 0)} detail="Creados o actualizados" />
          <FunnelStep number="3" label="Predichos hoy" value={predictionsToday} detail="Solo corto plazo" />
          <FunnelStep number="4" label="Operados" value={automaticTrades.length} detail="Campaña automática" />
        </div>
        {latestRun?.status === "failed" && <div className="mt-4 flex items-start gap-3 rounded-lg border border-warning/25 bg-warning-soft p-3 text-sm text-warning"><ShieldAlert className="mt-0.5 size-4 shrink-0" /><span>La última ingesta falló ({latestRun.safe_error_type ?? "error de proveedor"}). El worker seguirá reintentando.</span></div>}
      </section>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[1.1fr_.9fr]">
        <EquityPanel equity={equity} performance={performance} />
        <LatestPredictions items={predictions.slice(0, 5)} />
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <PlainStep icon={DatabaseZap} title="Observa" text="Lee probabilidades públicas y detecta cambios cada minuto." />
        <PlainStep icon={Bot} title="Razona y debate" text="Filtra bait y largo plazo; después compara análisis semántico, mercado y crítica." />
        <PlainStep icon={FlaskConical} title="Simula y aprende" text="Opera con reglas fijas y evalúa solo cuando aparece un resultado oficial." />
      </section>
    </div>
  );
}

function ActivityView({ trades, positions }: Readonly<{ trades: PaperTrade[]; positions: PaperPosition[] }>) {
  const liveTrades = trades.filter((item) => item.experiment_run_id === null && item.decision_source === "automatic");
  const positionByTrade = new Map(positions.map((item) => [item.trade_id, item]));
  return (
    <div className="page-enter space-y-5">
      <div><p className="eyebrow">Registro automático</p><h1 className="mt-1 text-3xl font-bold tracking-[-.04em] text-strong">Actividad</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted">Operaciones paper realizadas sin intervención manual. Las posiciones abiertas se actualizan hasta su resolución.</p></div>
      {liveTrades.length === 0 ? <StatePanel title="Todavía no hubo operaciones automáticas" text="El sistema sigue analizando. Solo operará si una predicción supera todos los controles." /> : <section className="panel overflow-hidden"><div className="hidden grid-cols-[minmax(240px,1fr)_90px_110px_110px_130px] gap-3 border-b border-line px-4 py-2 text-[11px] font-bold uppercase tracking-[.12em] text-muted md:grid"><span>Mercado</span><span>Lado</span><span>Invertido</span><span>Resultado</span><span>Estado</span></div>{liveTrades.map((trade) => <TradeRow key={trade.trade_id} trade={trade} position={positionByTrade.get(trade.trade_id) ?? null} />)}</section>}
    </div>
  );
}

function LearningStrip({ evaluation }: Readonly<{ evaluation: PredictionEvaluation | null }>) {
  const system = evaluation?.system;
  const market = evaluation?.market_baseline;
  const better = system && market ? Number(system.brier_score) < Number(market.brier_score) : false;
  return <section className="panel grid gap-px overflow-hidden bg-line md:grid-cols-[1fr_150px_150px_150px]"><div className="bg-panel p-4"><p className="eyebrow">Aprendizaje confirmado</p><h2 className="mt-1 font-bold text-strong">{evaluation && evaluation.resolved_count >= 100 && better ? "Señal favorable en observación" : "Todavía no hay evidencia suficiente"}</h2><p className="mt-1 text-xs leading-5 text-muted">Se usa una sola predicción por mercado resuelto. Menor Brier es mejor; actividad por minuto no cuenta como un nuevo caso.</p></div><LearningMetric label="Mercados resueltos" value={String(evaluation?.resolved_count ?? 0)} /><LearningMetric label="Brier sistema" value={system ? Number(system.brier_score).toFixed(3) : "—"} /><LearningMetric label="Brier mercado" value={market ? Number(market.brier_score).toFixed(3) : "—"} /></section>;
}

function LearningMetric({ label, value }: Readonly<{ label: string; value: string }>) { return <div className="bg-panel p-4 md:text-center"><strong className="block font-mono text-xl text-strong">{value}</strong><span className="mt-1 block text-[11px] font-semibold text-muted">{label}</span></div>; }

function AutomationControl({ state }: Readonly<{ state: AutomationState | null }>) {
  const client = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const mutation = useMutation({ mutationFn: state?.paused ? api.resumeAutomation : api.pauseAutomation, onSuccess: (value) => { client.setQueryData(["automation"], value); setConfirming(false); } });
  if (confirming && !state?.paused) return <div className="flex items-center gap-2 rounded-xl border border-negative/25 bg-negative-soft p-2"><span className="px-2 text-xs font-semibold text-negative">¿Pausar nuevas operaciones?</span><button className="button-danger" type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}><Pause className="size-4" /> Pausar</button><button className="icon-button" type="button" onClick={() => setConfirming(false)}><X className="size-4" /></button></div>;
  return <button type="button" className={state?.paused ? "button-primary" : "button-secondary"} onClick={() => state?.paused ? mutation.mutate() : setConfirming(true)} disabled={mutation.isPending}>{state?.paused ? <Play className="size-4" /> : <Pause className="size-4" />}{state?.paused ? "Reanudar automatización" : "Pausar automatización"}</button>;
}

function EquityPanel({ equity, performance }: Readonly<{ equity: EquityCurvePoint[]; performance: PaperPerformance | null }>) {
  const chart = equity.slice(-50).map((item) => ({ date: new Date(item.recorded_at).getTime(), value: Number(item.equity) }));
  const evidence = performance?.metrics.evidence_state ?? "insufficient_sample";
  return <section className="panel min-w-0 p-5"><SectionTitle icon={TrendingUp} title="Evolución del capital" subtitle="Capital virtual, costos y posiciones abiertas." /><div className="mt-4 h-56">{chart.length > 1 ? <ResponsiveContainer width="100%" height="100%"><LineChart data={chart} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}><CartesianGrid stroke="var(--line)" vertical={false} /><XAxis dataKey="date" type="number" domain={["dataMin", "dataMax"]} tickFormatter={(value) => new Date(value).toLocaleDateString("es-AR", { day: "2-digit", month: "short", timeZone: DISPLAY_TIME_ZONE })} tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--strong)" }} formatter={(value) => money(Number(value))} labelFormatter={(value) => shortDate(new Date(Number(value)).toISOString())} /><Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} /></LineChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-center text-sm text-muted"><div><ChartNoAxesCombined className="mx-auto mb-2 size-6" />El gráfico aparecerá después de registrar más de un punto.</div></div>}</div><div className="mt-3 flex items-center gap-2 border-t border-line pt-3 text-xs text-muted"><Info className="size-3.5" /><span>{evidenceLabel(evidence)}</span></div></section>;
}

function LatestPredictions({ items }: Readonly<{ items: PredictionListItem[] }>) {
  return <section className="panel p-5"><SectionTitle icon={Bot} title="Últimas predicciones" subtitle="Los análisis más recientes y su decisión comercial." /><div className="mt-3 divide-y divide-line">{items.length ? items.map((item) => <Link key={item.prediction_run_id} href={`/predictions/${item.prediction_run_id}`} className="group flex items-center gap-3 py-3"><span className={`size-2 shrink-0 rounded-full ${item.is_actionable ? "bg-positive" : "bg-neutral"}`} /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold text-strong group-hover:text-accent">{item.market_title}</span><span className="text-xs text-muted">Mercado {percent(item.market_probability)} · Sistema {percent(item.consensus_probability)}</span></span><ArrowRight className="size-4 text-muted transition group-hover:translate-x-0.5 group-hover:text-accent" /></Link>) : <p className="py-8 text-center text-sm text-muted">Esperando el próximo análisis de corto plazo.</p>}</div></section>;
}

function FunnelStep({ number, label, value, detail }: Readonly<{ number: string; label: string; value: number; detail: string }>) { return <div className="bg-panel p-4"><span className="text-[10px] font-bold text-accent">{number}</span><strong className="mt-2 block text-2xl text-strong">{value.toLocaleString("es-AR")}</strong><span className="mt-1 block text-sm font-semibold text-default">{label}</span><small className="text-xs text-muted">{detail}</small></div>; }
function Kpi({ icon: Icon, label, value, help }: Readonly<{ icon: LucideIcon; label: string; value: string; help: string }>) { return <article className="panel p-4"><div className="flex items-start justify-between"><span className="grid size-8 place-items-center rounded-lg bg-accent-soft text-accent"><Icon className="size-4" /></span><span title={help}><CircleHelp className="size-3.5 text-muted" /></span></div><strong className="mt-4 block text-2xl tracking-[-.03em] text-strong">{value}</strong><span className="mt-1 block text-xs font-semibold text-muted">{label}</span></article>; }
function SectionTitle({ icon: Icon, title, subtitle }: Readonly<{ icon: LucideIcon; title: string; subtitle: string }>) { return <div className="flex items-start gap-3"><Icon className="mt-0.5 size-4 text-accent" /><div><h2 className="font-bold text-strong">{title}</h2><p className="mt-0.5 text-xs leading-5 text-muted">{subtitle}</p></div></div>; }
function PlainStep({ icon: Icon, title, text }: Readonly<{ icon: LucideIcon; title: string; text: string }>) { return <article className="border-l-2 border-accent px-4 py-2"><Icon className="size-4 text-accent" /><h2 className="mt-3 font-bold text-strong">{title}</h2><p className="mt-1 text-sm leading-6 text-muted">{text}</p></article>; }
function MoneyPill({ icon: Icon, label, value, tone, help }: Readonly<{ icon: LucideIcon; label: string; value: string; tone: "positive" | "negative" | "neutral"; help: string }>) { const color = tone === "positive" ? "text-positive" : tone === "negative" ? "text-negative" : "text-neutral"; return <div className="flex shrink-0 items-center gap-2 rounded-lg border border-line bg-subtle px-2.5 py-2" title={help}><Icon className={`size-4 ${color}`} /><span><small className="block text-[9px] font-bold uppercase tracking-wider text-muted">{label}</small><strong className={`block font-mono text-xs ${color}`}>{value}</strong></span></div>; }
function TimeLabel({ icon: Icon, label, value }: Readonly<{ icon: LucideIcon; label: string; value: string }>) { return <div className="hidden items-center gap-2 xl:flex"><Icon className="size-3.5" /><span><small className="block text-[9px] font-bold uppercase tracking-wider">{label}</small><strong suppressHydrationWarning={label === "Ahora"} className="block whitespace-nowrap font-medium text-default">{value}</strong></span></div>; }
function TradeRow({ trade, position }: Readonly<{ trade: PaperTrade; position: PaperPosition | null }>) { const pnl = Number(position?.status === "settled" ? position.realized_pnl : position?.unrealized_pnl ?? 0); return <div className="grid gap-2 border-b border-line px-4 py-4 last:border-0 md:grid-cols-[minmax(240px,1fr)_90px_110px_110px_130px] md:items-center"><div><strong className="line-clamp-2 text-sm text-strong">{trade.market_title}</strong><small className="mt-1 block text-muted">{shortDate(trade.executed_at)}</small></div><span className="text-sm font-bold uppercase text-accent">{trade.side}</span><span className="font-mono text-sm text-strong">{money(Number(trade.net_cost))}</span><span className={`font-mono text-sm font-bold ${pnl > 0 ? "text-positive" : pnl < 0 ? "text-negative" : "text-neutral"}`}>{signedMoney(pnl)}</span><span className={`status ${position?.status === "settled" ? "status-good" : "status-neutral"}`}>{position?.status === "settled" ? "Finalizada" : "Esperando resultado"}</span></div>; }
function Loading() { return <div className="space-y-4">{[1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-xl bg-subtle" />)}</div>; }
function StatePanel({ title, text }: Readonly<{ title: string; text: string }>) { return <section className="panel grid min-h-64 place-items-center p-8 text-center"><div><ShieldAlert className="mx-auto size-7 text-muted" /><h1 className="mt-3 font-bold text-strong">{title}</h1><p className="mt-1 max-w-md text-sm text-muted">{text}</p></div></section>; }

function preferredPortfolio(items: PaperPortfolio[]) { return items.find((item) => item.experiment_run_id === null && item.name.toLowerCase().includes("autonomous")) ?? items.find((item) => item.experiment_run_id === null && !item.name.toLowerCase().includes("manual")) ?? null; }
function currentSection(value: string | undefined): Section { if (value === "predictions") return "predictions"; if (value === "trades" || value === "activity") return "activity"; return "overview"; }
function operationalStatus(sources: SourceHealth[], latest: SyncRun | null, completed: SyncRun | null, automation: AutomationState | null) { if (automation?.paused) return { title: "Automatización pausada", description: "La recolección puede continuar, pero no se crearán nuevas predicciones ni operaciones hasta reanudarla." }; const sourceOk = sources.length > 0 && sources.every((item) => item.status !== "unhealthy"); const fresh = completed?.finished_at ? Date.now() - new Date(completed.finished_at).getTime() < 5 * 60_000 : false; if (sourceOk && fresh && latest?.status !== "failed") return { title: "El sistema está trabajando", description: "Los datos están actuales y la campaña automática está buscando oportunidades de corto plazo." }; return { title: "El sistema necesita atención", description: "Los procesos siguen activos, pero los datos están atrasados o la última actualización falló. Se reintentará automáticamente." }; }
function evidenceLabel(value: string) { const labels: Record<string, string> = { insufficient_sample: "Muestra insuficiente: todavía no se puede afirmar que exista una ventaja.", preliminary_result: "Resultado preliminar: se necesitan más mercados resueltos.", under_observation: "Estrategia bajo observación; no cambiar parámetros durante la medición.", sufficient_to_expand_validation: "La muestra permite ampliar la validación, no usar dinero real." }; return labels[value] ?? labels.insufficient_sample; }
function money(value: number) { return `${value.toFixed(2)} M`; }
function signedMoney(value: number) { return `${value > 0 ? "+" : ""}${value.toFixed(2)} M`; }
function percent(value: string | null) { return value === null ? "—" : `${Math.round(Number(value) * 100)}%`; }
function shortDate(value: string | null) { return value ? new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: DISPLAY_TIME_ZONE }).format(new Date(value)) : "Sin datos"; }
function fullDate(value: Date) { return new Intl.DateTimeFormat("es-AR", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: DISPLAY_TIME_ZONE }).format(value); }
function dayKey(value: Date) { return `${value.getFullYear()}-${value.getMonth()}-${value.getDate()}`; }
function startOfDay(value: Date) { const result = new Date(value); result.setHours(0, 0, 0, 0); return result.toISOString(); }
