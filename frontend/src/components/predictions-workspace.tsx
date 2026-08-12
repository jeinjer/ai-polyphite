"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  Eye,
  Gauge,
  ShieldAlert,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";

import { api } from "@/lib/api";
import type {
  AgentPrediction,
  CommercialLabel,
  EstimatedOutcome,
  PredictionListItem,
} from "@/lib/api-types";

type DecisionFilter = "all" | CommercialLabel;
type OutcomeFilter = "all" | EstimatedOutcome;
const DISPLAY_TIME_ZONE = "Europe/Paris";
type SortFilter =
  | "newest"
  | "oldest"
  | "market_probability"
  | "consensus_probability"
  | "consensus_confidence";

export function PredictionsWorkspace({
  predictionId,
}: Readonly<{ predictionId: string | null }>) {
  return predictionId ? <PredictionDetail predictionId={predictionId} /> : <PredictionList />;
}

function PredictionList() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const page = positiveInteger(searchParams.get("page"), 1);
  const decision = decisionFilter(searchParams.get("decision"));
  const outcome = outcomeFilter(searchParams.get("outcome"));
  const sort = sortFilter(searchParams.get("sort"));
  const queryString = predictionQuery({ page, decision, outcome, sort });
  const query = useQuery({
    queryKey: ["prediction-list", queryString],
    queryFn: () => api.predictions(queryString),
    placeholderData: (previous) => previous,
  });

  const update = (values: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams.toString());
    Object.entries(values).forEach(([key, value]) => {
      if (!value || value === "all") next.delete(key);
      else next.set(key, value);
    });
    router.push(`/predictions${next.size ? `?${next.toString()}` : ""}`);
  };

  return (
    <div className="page-enter space-y-5">
      <PageTitle
        eyebrow="Decisiones automáticas"
        title="Predicciones"
        description="Qué estima el sistema, qué tan seguro está y si encontró una oportunidad operable."
      />

      <section className="panel flex flex-wrap items-center gap-3 p-3">
        <FilterGroup label="Conveniencia">
          <Select
            value={decision}
            onChange={(value) => update({ decision: value, page: null })}
            options={[
              ["all", "Todas"],
              ["actionable", "Conviene"],
              ["not_actionable", "No conviene"],
              ["not_evaluable", "Sin evaluar"],
            ]}
          />
        </FilterGroup>
        <FilterGroup label="Resultado estimado">
          <Select
            value={outcome}
            onChange={(value) => update({ outcome: value, page: null })}
            options={[
              ["all", "Todos"],
              ["yes", "Sí"],
              ["no", "No"],
            ]}
          />
        </FilterGroup>
        <FilterGroup label="Orden">
          <Select
            value={sort}
            onChange={(value) => update({ sort: value, page: null })}
            options={[
              ["newest", "Más recientes"],
              ["oldest", "Más antiguas"],
              ["market_probability", "Mayor prob. mercado"],
              ["consensus_probability", "Mayor prob. sistema"],
              ["consensus_confidence", "Mayor confianza"],
            ]}
          />
        </FilterGroup>
        <div className="ml-auto text-sm text-muted">
          {query.data ? `${query.data.total_items.toLocaleString("es-AR")} registros` : "Actualizando…"}
        </div>
      </section>

      {query.isLoading ? (
        <LoadingRows />
      ) : query.isError ? (
        <StatePanel icon={ShieldAlert} title="No pudimos cargar las predicciones" text="La API no respondió. El sistema volverá a intentarlo automáticamente." />
      ) : !query.data?.items.length ? (
        <StatePanel icon={Eye} title="No hay resultados para estos filtros" text="El sistema sigue escaneando mercados; probá una vista menos restrictiva." />
      ) : (
        <section className="panel overflow-hidden">
          <div className="hidden grid-cols-[minmax(260px,1fr)_110px_110px_100px_125px_44px] gap-3 border-b border-line px-4 py-2 text-[11px] font-bold uppercase tracking-[.12em] text-muted lg:grid">
            <span>Predicción</span>
            <Hint text="Probabilidad publicada por el mercado al momento de predecir.">Mercado</Hint>
            <Hint text="Probabilidad final calculada por el consenso del sistema.">Sistema</Hint>
            <Hint text="Consistencia y respaldo de la estimación, no garantía de acierto.">Confianza</Hint>
            <span>Decisión</span>
            <span />
          </div>
          {query.data.items.map((item) => <PredictionRow key={item.prediction_run_id} item={item} />)}
        </section>
      )}

      {query.data && query.data.total_pages > 1 && (
        <nav className="flex items-center justify-between" aria-label="Paginación">
          <button
            className="button-secondary"
            type="button"
            disabled={page <= 1}
            onClick={() => update({ page: String(page - 1) })}
          >
            <ChevronLeft className="size-4" /> Anterior
          </button>
          <span className="text-sm font-semibold text-muted">Página {page} de {query.data.total_pages}</span>
          <button
            className="button-secondary"
            type="button"
            disabled={page >= query.data.total_pages}
            onClick={() => update({ page: String(page + 1) })}
          >
            Siguiente <ChevronRight className="size-4" />
          </button>
        </nav>
      )}
    </div>
  );
}

function PredictionRow({ item }: Readonly<{ item: PredictionListItem }>) {
  return (
    <Link
      href={`/predictions/${encodeURIComponent(item.prediction_run_id)}`}
      className="group grid cursor-pointer gap-3 border-b border-line px-4 py-4 transition-colors last:border-0 hover:bg-hover lg:grid-cols-[minmax(260px,1fr)_110px_110px_100px_125px_44px] lg:items-center"
    >
      <div className="min-w-0">
        <div className="mb-1.5 flex items-center gap-2 text-xs text-muted">
          <Clock3 className="size-3.5" /> {dateTime(item.predicted_at)}
          {item.estimated_outcome && <Outcome outcome={item.estimated_outcome} />}
        </div>
        <h2 className="line-clamp-2 font-semibold leading-5 text-strong group-hover:text-accent">{item.market_title}</h2>
      </div>
      <Metric label="Mercado" value={percent(item.market_probability)} />
      <Metric label="Sistema" value={percent(item.consensus_probability)} strong />
      <Metric label="Confianza" value={percent(item.consensus_confidence)} />
      <Decision label={item.commercial_label} />
      <span className="grid size-9 place-items-center rounded-lg border border-line text-muted transition group-hover:translate-x-0.5 group-hover:border-accent group-hover:text-accent">
        <ChevronRight className="size-4" />
      </span>
    </Link>
  );
}

function PredictionDetail({ predictionId }: Readonly<{ predictionId: string }>) {
  const query = useQuery({
    queryKey: ["prediction-detail", predictionId],
    queryFn: () => api.prediction(predictionId),
  });
  if (query.isLoading) return <LoadingRows />;
  if (query.isError || !query.data) {
    return <StatePanel icon={ShieldAlert} title="Predicción no disponible" text="No pudimos recuperar este análisis." />;
  }
  const value = query.data;
  const evaluation = value.commercial_evaluation;
  const reasoning = value.agent_predictions.find((agent) => agent.agent_name === "reasoning");
  return (
    <div className="page-enter space-y-5">
      <Link href="/predictions" className="inline-flex items-center gap-2 text-sm font-semibold text-muted transition hover:text-accent">
        <ArrowLeft className="size-4" /> Volver a predicciones
      </Link>

      <section className="panel p-5 md:p-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="mb-3 flex flex-wrap gap-2">
              <Decision label={evaluation?.commercial_label ?? "not_evaluable"} />
              {value.estimated_outcome && <Outcome outcome={value.estimated_outcome} />}
            </div>
            <h1 className="text-2xl font-bold tracking-[-.03em] text-strong md:text-3xl">{value.market_title}</h1>
            <p className="mt-3 text-sm leading-6 text-muted">
              {reasoning?.rationale_summary ?? value.abstention_reason ?? "El análisis no publicó una explicación."}
            </p>
          </div>
          <div className="grid min-w-56 grid-cols-2 gap-3">
            <DetailMetric label="Mercado" value={percent(value.market_probability)} />
            <DetailMetric label="Sistema" value={percent(value.consensus_probability)} accent />
            <DetailMetric label="Confianza" value={percent(value.consensus_confidence)} />
            <DetailMetric label="Diferencia" value={points(value.edge)} />
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="panel p-5 md:p-6">
          <div className="mb-5 flex items-center gap-3">
            <BrainCircuit className="size-5 text-accent" />
            <div>
              <h2 className="font-bold text-strong">Debate de agentes</h2>
              <p className="text-sm text-muted">Primero opinan de forma independiente; después el escéptico cuestiona y el consenso agrega.</p>
            </div>
          </div>
          <div className="space-y-3">
            {value.agent_predictions.map((agent) => <AgentLine key={agent.agent_prediction_id} agent={agent} />)}
          </div>
        </div>
        <aside className="panel p-5">
          <h2 className="font-bold text-strong">Por qué se decidió esto</h2>
          <p className="mt-2 text-sm leading-6 text-muted">{reasonLabel(evaluation?.reasons[0] ?? value.abstention_reason)}</p>
          <dl className="mt-5 space-y-3 border-t border-line pt-4 text-sm">
            <DataRow label="Datos" value={evaluation?.data_freshness_status === "fresh" ? "Actualizados" : "Revisar frescura"} />
            <DataRow label="Costo estimado" value={evaluation ? points(evaluation.estimated_fees) : "—"} />
            <DataRow label="Ventaja neta" value={evaluation ? points(evaluation.net_edge) : "—"} />
            <DataRow label="Hora" value={dateTime(value.predicted_at)} />
          </dl>
        </aside>
      </section>
    </div>
  );
}

function AgentLine({ agent }: Readonly<{ agent: AgentPrediction }>) {
  const meta = agentMeta(agent.agent_name);
  const Icon = meta.icon;
  return (
    <details className="group rounded-xl border border-line bg-subtle open:bg-panel">
      <summary className="flex cursor-pointer list-none items-center gap-3 p-4">
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent"><Icon className="size-4" /></span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold text-strong">{meta.label}</span>
          <span className="block truncate text-xs text-muted">{meta.role}</span>
        </span>
        <span className="text-right">
          <span className="block font-mono text-sm font-bold text-strong">{percent(agent.predicted_probability)}</span>
          <span className="block text-[11px] text-muted">conf. {percent(agent.confidence)}</span>
        </span>
        <ChevronRight className="size-4 text-muted transition group-open:rotate-90" />
      </summary>
      <div className="border-t border-line px-4 py-4 text-sm leading-6 text-muted">
        <p>{agent.rationale_summary}</p>
        {agent.warnings.length > 0 && <p className="mt-3 text-warning">{agent.warnings[0]}</p>}
      </div>
    </details>
  );
}

function PageTitle({ eyebrow, title, description }: Readonly<{ eyebrow: string; title: string; description: string }>) {
  return <header><p className="eyebrow">{eyebrow}</p><h1 className="mt-1 text-3xl font-bold tracking-[-.04em] text-strong">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p></header>;
}

function FilterGroup({ label, children }: Readonly<{ label: string; children: ReactNode }>) {
  return <label className="flex items-center gap-2 text-xs font-semibold text-muted"><span>{label}</span>{children}</label>;
}

function Select({ value, onChange, options }: Readonly<{ value: string; onChange: (value: string) => void; options: [string, string][] }>) {
  return <select className="control" value={value} onChange={(event) => onChange(event.target.value)}>{options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>;
}

function Hint({ text, children }: Readonly<{ text: string; children: ReactNode }>) {
  return <span className="inline-flex items-center gap-1" title={text}>{children}<CircleHelp className="size-3" /></span>;
}

function Metric({ label, value, strong = false }: Readonly<{ label: string; value: string; strong?: boolean }>) {
  return <div><span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-muted lg:hidden">{label}</span><span className={`font-mono text-sm font-bold ${strong ? "text-accent" : "text-strong"}`}>{value}</span></div>;
}

function DetailMetric({ label, value, accent = false }: Readonly<{ label: string; value: string; accent?: boolean }>) {
  return <div className="rounded-lg bg-subtle p-3"><dt className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</dt><dd className={`mt-1 font-mono text-lg font-bold ${accent ? "text-accent" : "text-strong"}`}>{value}</dd></div>;
}

function Decision({ label }: Readonly<{ label: CommercialLabel }>) {
  const values = label === "actionable" ? ["Conviene", "good"] : label === "not_actionable" ? ["No conviene", "neutral"] : ["Sin evaluar", "warning"];
  return <span className={`status status-${values[1]}`}>{values[0]}</span>;
}

function Outcome({ outcome }: Readonly<{ outcome: EstimatedOutcome }>) {
  return <span className="rounded-md bg-subtle px-1.5 py-0.5 text-[10px] font-bold uppercase text-strong">Estima {outcome === "yes" ? "Sí" : "No"}</span>;
}

function agentMeta(name: string) {
  if (name === "reasoning") return { label: "Análisis semántico", role: "Valida contrato, bait y plausibilidad", icon: Sparkles };
  if (name === "market") return { label: "Señal de mercado", role: "Lee tendencia y volatilidad", icon: Gauge };
  if (name === "skeptic") return { label: "Revisión escéptica", role: "Ataca supuestos y exceso de confianza", icon: ShieldAlert };
  return { label: "Consenso", role: "Agrega probabilidades con reglas reproducibles", icon: CheckCircle2 };
}

function DataRow({ label, value }: Readonly<{ label: string; value: string }>) { return <div className="flex items-start justify-between gap-3"><dt className="text-muted">{label}</dt><dd className="text-right font-semibold text-strong">{value}</dd></div>; }

function StatePanel({ icon: Icon, title, text }: Readonly<{ icon: LucideIcon; title: string; text: string }>) { return <section className="panel grid min-h-52 place-items-center p-8 text-center"><div><Icon className="mx-auto size-7 text-muted" /><h2 className="mt-3 font-bold text-strong">{title}</h2><p className="mt-1 max-w-md text-sm text-muted">{text}</p></div></section>; }

function LoadingRows() { return <div className="panel space-y-1 p-2">{[1, 2, 3, 4, 5].map((item) => <div key={item} className="h-20 animate-pulse rounded-lg bg-subtle" />)}</div>; }

function predictionQuery({ page, decision, outcome, sort }: { page: number; decision: DecisionFilter; outcome: OutcomeFilter; sort: SortFilter }) { const oldest = sort === "oldest"; const field = sort === "newest" || oldest ? "predicted_at" : sort; const params = new URLSearchParams({ page: String(page), page_size: "25", sort: field, direction: oldest ? "asc" : "desc" }); if (decision !== "all") params.set("commercial_label", decision); if (outcome !== "all") params.set("estimated_outcome", outcome); return params.toString(); }
function decisionFilter(value: string | null): DecisionFilter { return value === "actionable" || value === "not_actionable" || value === "not_evaluable" ? value : "all"; }
function outcomeFilter(value: string | null): OutcomeFilter { return value === "yes" || value === "no" ? value : "all"; }
function sortFilter(value: string | null): SortFilter { return value === "oldest" || value === "market_probability" || value === "consensus_probability" || value === "consensus_confidence" ? value : "newest"; }
function positiveInteger(value: string | null, fallback: number) { const parsed = Number(value); return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback; }
function percent(value: string | null) { return value === null ? "—" : `${Math.round(Number(value) * 100)}%`; }
function points(value: string | null) { if (value === null) return "—"; const number = Number(value) * 100; return `${number > 0 ? "+" : ""}${number.toFixed(1)} pp`; }
function dateTime(value: string) { return new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: DISPLAY_TIME_ZONE }).format(new Date(value)); }
function reasonLabel(value: string | null | undefined) { if (!value) return "No existe una evaluación comercial asociada."; const labels: Record<string, string> = { opportunity_level_not_allowed: "La diferencia frente al mercado todavía es demasiado pequeña.", insufficient_net_edge: "La ventaja desaparece después de considerar costos simulados.", insufficient_confidence: "La estimación todavía no tiene respaldo suficiente.", category_concentration: "La cartera ya tiene demasiada exposición relacionada.", incompatible_existing_position: "Ya existe una posición abierta en este mercado.", no_commercial_edge: "No se detectó una diferencia aprovechable frente al mercado." }; return labels[value] ?? value.replaceAll("_", " "); }
