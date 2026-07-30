"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Eye,
  LoaderCircle,
  Play,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { useI18n } from "@/i18n/i18n-provider";
import { api } from "@/lib/api";
import type {
  CommercialLabel,
  ManualPaperTradeResponse,
  PositionSide,
  PredictionListItem,
} from "@/lib/api-types";
import { useUiStore } from "@/stores/ui-store";

type Copy = {
  title: string;
  description: string;
  market: string;
  marketProbability: string;
  estimatedProbability: string;
  confidence: string;
  estimatedOutcome: string;
  evaluation: string;
  actions: string;
  actionable: string;
  notActionable: string;
  notEvaluable: string;
  noPrediction: string;
  trade: string;
  tradeAnyway: string;
  detail: string;
  all: string;
  newest: string;
  oldest: string;
  yes: string;
  no: string;
  unavailable: string;
  highestMarket: string;
  highestEstimate: string;
  highestConfidence: string;
  highestNetEdge: string;
  previous: string;
  next: string;
  automaticDefault: string;
  simulationWarning: string;
  side: string;
  stake: string;
  reason: string;
  reasonPlaceholder: string;
  confirm: string;
  cancel: string;
  manualTitle: string;
  manualExplanation: string;
  resultFilled: string;
  resultRejected: string;
  resultDuplicate: string;
  loading: string;
  empty: string;
  back: string;
  costs: string;
  grossEdge: string;
  netEdge: string;
  freshness: string;
  reasons: string;
  warnings: string;
  agents: string;
  traceability: string;
};

const copies: Record<"es-ES" | "en-US", Copy> = {
  "es-ES": {
    title: "Predicciones",
    description:
      "Predicción, conveniencia comercial y ejecución simulada se muestran como decisiones separadas.",
    market: "Mercado",
    marketProbability: "Probabilidad del mercado",
    estimatedProbability: "Probabilidad estimada",
    confidence: "Confianza",
    estimatedOutcome: "Resultado estimado",
    evaluation: "Evaluación",
    actions: "Acciones",
    actionable: "Conviene",
    notActionable: "No conviene",
    notEvaluable: "No evaluable",
    noPrediction: "Sin predicción",
    trade: "Operar",
    tradeAnyway: "Operar igualmente",
    detail: "Ver detalle",
    all: "Todas",
    newest: "Más reciente",
    oldest: "Más antiguo",
    yes: "Resultado YES",
    no: "Resultado NO",
    unavailable: "Sin predicción",
    highestMarket: "Mayor probabilidad del mercado",
    highestEstimate: "Mayor probabilidad estimada",
    highestConfidence: "Mayor confianza",
    highestNetEdge: "Mayor edge neto",
    previous: "Anterior",
    next: "Siguiente",
    automaticDefault:
      "La operación automática sigue activa y prevalece por defecto. Este botón crea una excepción manual separada.",
    simulationWarning:
      "Esta operación es exclusivamente simulada. No utiliza dinero real.",
    side: "Lado simulado",
    stake: "Stake simulado",
    reason: "Motivo del override",
    reasonPlaceholder: "Explica por qué querés ignorar la decisión automática",
    confirm: "Confirmar operación simulada",
    cancel: "Cancelar",
    manualTitle: "Override manual de paper trading",
    manualExplanation:
      "Podés elegir YES o NO aunque los agentes se abstengan o indiquen que no conviene. Los límites contables y de riesgo siguen vigentes.",
    resultFilled: "La operación simulada fue creada.",
    resultRejected: "El backend rechazó la operación tras revalidar el mercado y el riesgo.",
    resultDuplicate: "Esta solicitud ya había sido procesada.",
    loading: "Cargando predicciones…",
    empty: "No hay predicciones para estos filtros.",
    back: "Volver a predicciones",
    costs: "Costes simulados",
    grossEdge: "Edge bruto",
    netEdge: "Edge neto",
    freshness: "Antigüedad de datos",
    reasons: "Motivos",
    warnings: "Advertencias",
    agents: "Salidas de agentes",
    traceability: "Trazabilidad",
  },
  "en-US": {
    title: "Predictions",
    description:
      "Prediction, commercial suitability, and simulated execution are shown as separate decisions.",
    market: "Market",
    marketProbability: "Market probability",
    estimatedProbability: "Estimated probability",
    confidence: "Confidence",
    estimatedOutcome: "Estimated outcome",
    evaluation: "Evaluation",
    actions: "Actions",
    actionable: "Worth trading",
    notActionable: "Not worth trading",
    notEvaluable: "Not evaluable",
    noPrediction: "No prediction",
    trade: "Trade",
    tradeAnyway: "Trade anyway",
    detail: "View details",
    all: "All",
    newest: "Newest",
    oldest: "Oldest",
    yes: "YES outcome",
    no: "NO outcome",
    unavailable: "No prediction",
    highestMarket: "Highest market probability",
    highestEstimate: "Highest estimated probability",
    highestConfidence: "Highest confidence",
    highestNetEdge: "Highest net edge",
    previous: "Previous",
    next: "Next",
    automaticDefault:
      "Automatic execution remains active and is the default. This button creates a separate manual exception.",
    simulationWarning:
      "This operation is exclusively simulated. It does not use real money.",
    side: "Simulated side",
    stake: "Simulated stake",
    reason: "Override reason",
    reasonPlaceholder: "Explain why you want to ignore the automatic decision",
    confirm: "Confirm simulated trade",
    cancel: "Cancel",
    manualTitle: "Manual paper-trading override",
    manualExplanation:
      "You can choose YES or NO even when agents abstain or mark it as not actionable. Accounting and risk limits still apply.",
    resultFilled: "The simulated trade was created.",
    resultRejected: "The backend rejected the trade after revalidating market and risk.",
    resultDuplicate: "This request had already been processed.",
    loading: "Loading predictions…",
    empty: "No predictions match these filters.",
    back: "Back to predictions",
    costs: "Simulated costs",
    grossEdge: "Gross edge",
    netEdge: "Net edge",
    freshness: "Data freshness",
    reasons: "Reasons",
    warnings: "Warnings",
    agents: "Agent outputs",
    traceability: "Traceability",
  },
};

export function PredictionsWorkspace({
  predictionId,
}: Readonly<{ predictionId: string | null }>) {
  const { locale } = useI18n();
  const copy = copies[locale];
  if (predictionId) {
    return <PredictionDetail predictionId={predictionId} copy={copy} />;
  }
  return <PredictionList copy={copy} />;
}

function PredictionList({ copy }: Readonly<{ copy: Copy }>) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const page = positiveInt(searchParams.get("page"), 1);
  const pageSize = searchParams.get("page_size") === "50" ? 50 : 25;
  const query = useMemo(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    return params.toString();
  }, [page, pageSize, searchParams]);
  const predictions = useQuery({
    queryKey: ["prediction-list", query],
    queryFn: () => api.predictions(query),
    placeholderData: keepPreviousData,
    refetchInterval: 60_000,
  });
  const [trade, setTrade] = useState<PredictionListItem | null>(null);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams.toString());
    if (!value || value === "all") next.delete(key);
    else next.set(key, value);
    next.set("page", "1");
    next.set("page_size", String(pageSize));
    router.push(`/predictions?${next.toString()}`);
  };
  const goToPage = (nextPage: number) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("page", String(nextPage));
    next.set("page_size", String(pageSize));
    router.push(`/predictions?${next.toString()}`);
  };

  return (
    <div className="space-y-6" data-testid="prediction-list">
      <header>
        <h2 className="text-xl font-semibold">{copy.title}</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-500">
          {copy.description}
        </p>
        <p className="mt-2 text-xs text-cyan-200/70">
          {copy.automaticDefault}
        </p>
      </header>

      <div className="grid gap-3 rounded-2xl border border-white/8 bg-white/[0.025] p-4 sm:grid-cols-2 xl:grid-cols-5">
        <Filter
          label={copy.evaluation}
          value={searchParams.get("commercial_label") ?? "all"}
          onChange={(value) => setFilter("commercial_label", value)}
          options={[
            ["all", copy.all],
            ["actionable", copy.actionable],
            ["not_actionable", copy.notActionable],
            ["not_evaluable", copy.notEvaluable],
          ]}
        />
        <Filter
          label={copy.estimatedOutcome}
          value={searchParams.get("estimated_outcome") ?? "all"}
          onChange={(value) => setFilter("estimated_outcome", value)}
          options={[
            ["all", copy.all],
            ["yes", copy.yes],
            ["no", copy.no],
            ["unavailable", copy.unavailable],
          ]}
        />
        <Filter
          label="Orden"
          value={`${searchParams.get("sort") ?? "predicted_at"}:${searchParams.get("direction") ?? "desc"}`}
          onChange={(value) => {
            const [sort, direction] = value.split(":");
            const next = new URLSearchParams(searchParams.toString());
            next.set("sort", sort);
            next.set("direction", direction);
            next.set("page", "1");
            router.push(`/predictions?${next.toString()}`);
          }}
          options={[
            ["predicted_at:desc", copy.newest],
            ["predicted_at:asc", copy.oldest],
            ["market_probability:desc", copy.highestMarket],
            ["consensus_probability:desc", copy.highestEstimate],
            ["consensus_confidence:desc", copy.highestConfidence],
            ["net_edge:desc", copy.highestNetEdge],
          ]}
        />
        <Filter
          label="Por página"
          value={String(pageSize)}
          onChange={(value) => setFilter("page_size", value)}
          options={[
            ["25", "25"],
            ["50", "50"],
          ]}
        />
      </div>

      {predictions.isLoading ? (
        <Loading copy={copy} />
      ) : predictions.isError ? (
        <ErrorPanel onRetry={() => void predictions.refetch()} />
      ) : !predictions.data?.items.length ? (
        <div className="rounded-2xl border border-white/8 p-10 text-center text-sm text-slate-500">
          {copy.empty}
        </div>
      ) : (
        <div
          className={`overflow-x-auto rounded-2xl border border-white/8 bg-white/[0.025] transition-opacity ${
            predictions.isFetching ? "opacity-60" : "opacity-100"
          }`}
        >
          <table className="min-w-[1080px] w-full text-left text-sm">
            <thead className="border-b border-white/8 text-xs uppercase tracking-wider text-slate-600">
              <tr>
                <th className="px-5 py-4">{copy.market}</th>
                <th className="px-3 py-4">{copy.marketProbability}</th>
                <th className="px-3 py-4">{copy.estimatedProbability}</th>
                <th className="px-3 py-4">{copy.confidence}</th>
                <th className="px-3 py-4">{copy.estimatedOutcome}</th>
                <th className="px-3 py-4">{copy.evaluation}</th>
                <th className="px-5 py-4">{copy.actions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/7">
              {predictions.data.items.map((item) => (
                <tr key={item.prediction_run_id}>
                  <td className="max-w-md px-5 py-4">
                    <p className="font-medium text-slate-200">
                      {item.market_title}
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      {new Date(item.predicted_at).toLocaleString()} ·{" "}
                      {item.provider_code}
                    </p>
                  </td>
                  <td className="px-3 py-4">
                    {probability(item.market_probability)}
                  </td>
                  <td className="px-3 py-4">
                    {probability(item.consensus_probability)}
                  </td>
                  <td className="px-3 py-4">
                    {probability(item.consensus_confidence)}
                  </td>
                  <td className="px-3 py-4 font-medium">
                    {item.estimated_outcome?.toUpperCase() ??
                      copy.noPrediction}
                  </td>
                  <td className="px-3 py-4">
                    <CommercialBadge label={item.commercial_label} copy={copy} />
                    <p
                      className="mt-2 max-w-48 text-xs text-slate-600"
                      title={humanReason(item.primary_reason)}
                    >
                      {item.net_edge === null
                        ? humanReason(item.primary_reason)
                        : `${copy.netEdge}: ${signedPoints(item.net_edge)}`}
                    </p>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setTrade(item)}
                        title={copy.automaticDefault}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-300/12 px-3 py-2 text-xs font-medium text-cyan-200 transition hover:bg-cyan-300/20"
                      >
                        <Play aria-hidden="true" className="size-3.5" />
                        {item.is_actionable
                          ? copy.trade
                          : copy.tradeAnyway}
                      </button>
                      <Link
                        href={`/predictions/${item.prediction_run_id}`}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:border-white/20"
                      >
                        <Eye aria-hidden="true" className="size-3.5" />
                        {copy.detail}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {predictions.data && predictions.data.total_pages > 0 && (
        <nav
          className="flex items-center justify-between text-sm text-slate-500"
          aria-label="Pagination"
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => goToPage(page - 1)}
            className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 disabled:opacity-30"
          >
            <ChevronLeft className="size-4" /> {copy.previous}
          </button>
          <span>
            {page} / {predictions.data.total_pages}
          </span>
          <button
            type="button"
            disabled={page >= predictions.data.total_pages}
            onClick={() => goToPage(page + 1)}
            className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 disabled:opacity-30"
          >
            {copy.next} <ChevronRight className="size-4" />
          </button>
        </nav>
      )}

      {trade && (
        <ManualTradeModal
          prediction={trade}
          copy={copy}
          onClose={() => setTrade(null)}
        />
      )}
    </div>
  );
}

function PredictionDetail({
  predictionId,
  copy,
}: Readonly<{ predictionId: string; copy: Copy }>) {
  const mode = useUiStore((state) => state.mode);
  const prediction = useQuery({
    queryKey: ["prediction-detail", predictionId],
    queryFn: () => api.prediction(predictionId),
  });
  const [trade, setTrade] = useState<PredictionListItem | null>(null);
  if (prediction.isLoading) return <Loading copy={copy} />;
  if (prediction.isError || !prediction.data) {
    return <ErrorPanel onRetry={() => void prediction.refetch()} />;
  }
  const item = detailToListItem(prediction.data);
  const commercial = prediction.data.commercial_evaluation;
  return (
    <div className="space-y-6" data-testid="prediction-detail">
      <Link
        href="/predictions"
        className="inline-flex items-center gap-2 text-sm text-cyan-300"
      >
        <ArrowLeft className="size-4" /> {copy.back}
      </Link>
      <header className="rounded-2xl border border-white/8 bg-white/[0.025] p-6">
        <p className="text-xs uppercase tracking-wider text-slate-600">
          {prediction.data.provider_code}
        </p>
        <h2 className="mt-2 text-xl font-semibold">
          {prediction.data.market_title}
        </h2>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric
            label={copy.marketProbability}
            value={probability(prediction.data.market_probability)}
          />
          <Metric
            label={copy.estimatedProbability}
            value={probability(prediction.data.consensus_probability)}
          />
          <Metric
            label={copy.estimatedOutcome}
            value={
              prediction.data.estimated_outcome?.toUpperCase() ??
              copy.noPrediction
            }
          />
          <Metric
            label={copy.confidence}
            value={probability(prediction.data.consensus_confidence)}
          />
          <Metric
            label={copy.evaluation}
            value={commercialLabel(item.commercial_label, copy)}
          />
        </div>
        <button
          type="button"
          onClick={() => setTrade(item)}
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-cyan-300/12 px-4 py-2 text-sm font-medium text-cyan-200"
        >
          <Play className="size-4" />
          {item.is_actionable ? copy.trade : copy.tradeAnyway}
        </button>
        <p className="mt-3 text-xs text-cyan-200/70">
          {copy.automaticDefault}
        </p>
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card title={copy.reasons}>
          <ul className="space-y-2 text-sm text-slate-400">
            {(commercial?.reasons ?? [
              prediction.data.abstention_reason ?? item.primary_reason,
            ]).map((reason) => (
              <li key={reason}>• {humanReason(reason)}</li>
            ))}
          </ul>
        </Card>
        <Card title={copy.costs}>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Metric
              label={copy.grossEdge}
              value={signedPoints(commercial?.gross_edge ?? null)}
            />
            <Metric
              label={copy.netEdge}
              value={signedPoints(commercial?.net_edge ?? null)}
            />
            <Metric
              label="Fees"
              value={signedPoints(commercial?.estimated_fees ?? null)}
            />
            <Metric
              label="Slippage"
              value={signedPoints(commercial?.estimated_slippage ?? null)}
            />
          </dl>
        </Card>
      </section>

      {mode === "advanced" && (
        <>
          <Card title={copy.agents}>
            <div className="grid gap-3 lg:grid-cols-2">
              {prediction.data.agent_predictions.map((agent) => (
                <article
                  key={agent.agent_prediction_id}
                  className="rounded-xl border border-white/8 p-4"
                >
                  <div className="flex justify-between gap-3">
                    <h3 className="font-medium capitalize">
                      {agent.agent_name}
                    </h3>
                    <span className="text-xs text-slate-600">
                      v{agent.agent_version}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    {agent.rationale_summary}
                  </p>
                  <p className="mt-3 text-xs text-slate-600">
                    {probability(agent.predicted_probability)} ·{" "}
                    {probability(agent.confidence)}
                  </p>
                </article>
              ))}
            </div>
          </Card>
          <Card title={copy.traceability}>
            <dl className="grid gap-3 text-xs text-slate-500 lg:grid-cols-2">
              <code className="break-all">
                config: {prediction.data.agent_configuration_hash}
              </code>
              <code className="break-all">
                input: {prediction.data.input_hash}
              </code>
              <code className="break-all">
                result: {prediction.data.result_hash}
              </code>
              <code className="break-all">
                correlation: {prediction.data.correlation_id}
              </code>
            </dl>
          </Card>
          {prediction.data.related_executions.length > 0 && (
            <Card title="Paper trading relacionado">
              <div className="space-y-3 text-sm text-slate-400">
                {prediction.data.related_executions.map((execution) => (
                  <div
                    key={execution.decision_id}
                    className="rounded-xl border border-white/8 p-4"
                  >
                    <p className="font-medium text-slate-200">
                      {execution.portfolio_name}
                    </p>
                    <p className="mt-1">
                      {execution.decision_source} · {execution.decision}
                    </p>
                    {execution.override_reason && (
                      <p className="mt-2 text-xs text-slate-500">
                        {execution.override_reason}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
      {trade && (
        <ManualTradeModal
          prediction={trade}
          copy={copy}
          onClose={() => setTrade(null)}
        />
      )}
    </div>
  );
}

function ManualTradeModal({
  prediction,
  copy,
  onClose,
}: Readonly<{
  prediction: PredictionListItem;
  copy: Copy;
  onClose: () => void;
}>) {
  const queryClient = useQueryClient();
  const defaultSide: PositionSide =
    prediction.potential_side === "buy_no"
      ? "no"
      : prediction.potential_side === "buy_yes"
        ? "yes"
        : prediction.estimated_outcome ?? "yes";
  const [side, setSide] = useState<PositionSide>(defaultSide);
  const [stake, setStake] = useState("0.50");
  const [reason, setReason] = useState("");
  const [idempotencyKey] = useState(() => crypto.randomUUID());
  const [result, setResult] = useState<ManualPaperTradeResponse | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      api.manualPaperTrade({
        prediction_run_id: prediction.prediction_run_id,
        side,
        requested_stake: stake,
        override_reason: reason,
        idempotency_key: idempotencyKey,
      }),
    onSuccess: (value) => {
      setResult(value);
      void queryClient.invalidateQueries({ queryKey: ["prediction-list"] });
      void queryClient.invalidateQueries({ queryKey: ["paper-portfolios"] });
    },
  });
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="manual-trade-title"
    >
      <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-white/10 bg-[#0b111b] p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="manual-trade-title" className="text-lg font-semibold">
              {copy.manualTitle}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              {copy.manualExplanation}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={copy.cancel}
            className="rounded-lg p-2 text-slate-500 hover:bg-white/5"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="mt-5 rounded-xl border border-amber-300/15 bg-amber-300/5 p-4 text-sm text-amber-100">
          {copy.simulationWarning}
        </div>
        <p className="mt-5 font-medium">{prediction.market_title}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-slate-400">
            {copy.side}
            <select
              value={side}
              onChange={(event) =>
                setSide(event.target.value as PositionSide)
              }
              className="mt-2 w-full rounded-lg border border-white/10 bg-[#080d15] px-3 py-2 text-slate-200"
            >
              <option value="yes">Comprar YES</option>
              <option value="no">Comprar NO</option>
            </select>
          </label>
          <label className="text-sm text-slate-400">
            {copy.stake}
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={stake}
              onChange={(event) => setStake(event.target.value)}
              className="mt-2 w-full rounded-lg border border-white/10 bg-[#080d15] px-3 py-2 text-slate-200"
            />
          </label>
        </div>
        <label className="mt-4 block text-sm text-slate-400">
          {copy.reason}
          <textarea
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={copy.reasonPlaceholder}
            className="mt-2 min-h-24 w-full rounded-lg border border-white/10 bg-[#080d15] px-3 py-2 text-slate-200"
          />
        </label>
        {mutation.isError && (
          <p className="mt-4 text-sm text-rose-300">
            El backend no pudo procesar la operación.
          </p>
        )}
        {result && (
          <p
            className={`mt-4 rounded-lg p-3 text-sm ${
              result.status === "filled"
                ? "bg-emerald-300/8 text-emerald-200"
                : "bg-amber-300/8 text-amber-200"
            }`}
          >
            {result.status === "filled"
              ? copy.resultFilled
              : result.status === "duplicate"
                ? copy.resultDuplicate
                : `${copy.resultRejected} ${result.rejection_reasons
                    .map(humanReason)
                    .join(", ")}`}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-300"
          >
            {copy.cancel}
          </button>
          <button
            type="button"
            disabled={
              mutation.isPending ||
              reason.trim().length === 0 ||
              Number(stake) <= 0 ||
              result !== null
            }
            onClick={() => mutation.mutate()}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-300/15 px-4 py-2 text-sm font-medium text-cyan-100 disabled:opacity-40"
          >
            {mutation.isPending && (
              <LoaderCircle className="size-4 animate-spin" />
            )}
            {copy.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}

function Filter({
  label,
  value,
  options,
  onChange,
}: Readonly<{
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}>) {
  return (
    <label className="text-xs text-slate-500">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 w-full rounded-lg border border-white/10 bg-[#080d15] px-3 py-2 text-sm text-slate-200"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

function CommercialBadge({
  label,
  copy,
}: Readonly<{ label: CommercialLabel; copy: Copy }>) {
  const styles =
    label === "actionable"
      ? "border-emerald-300/20 bg-emerald-300/8 text-emerald-200"
      : label === "not_actionable"
        ? "border-amber-300/20 bg-amber-300/8 text-amber-200"
        : "border-slate-400/20 bg-slate-400/8 text-slate-300";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs ${styles}`}
      aria-label={commercialLabel(label, copy)}
    >
      <CircleHelp aria-hidden="true" className="size-3" />
      {commercialLabel(label, copy)}
    </span>
  );
}

function Card({
  title,
  children,
}: Readonly<{ title: string; children: React.ReactNode }>) {
  return (
    <section className="rounded-2xl border border-white/8 bg-white/[0.025] p-5">
      <h2 className="mb-4 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Metric({
  label,
  value,
}: Readonly<{ label: string; value: string }>) {
  return (
    <div className="rounded-xl border border-white/7 bg-black/10 p-3">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className="mt-1 font-medium text-slate-200">{value}</dd>
    </div>
  );
}

function Loading({ copy }: Readonly<{ copy: Copy }>) {
  return (
    <div className="grid min-h-60 place-items-center text-sm text-slate-500">
      <span className="inline-flex items-center gap-2">
        <LoaderCircle className="size-4 animate-spin" /> {copy.loading}
      </span>
    </div>
  );
}

function ErrorPanel({ onRetry }: Readonly<{ onRetry: () => void }>) {
  return (
    <div className="rounded-2xl border border-rose-300/15 bg-rose-300/5 p-6 text-sm text-rose-200">
      No se pudo cargar esta información.
      <button
        type="button"
        onClick={onRetry}
        className="ml-3 underline"
      >
        Reintentar
      </button>
    </div>
  );
}

function detailToListItem(
  prediction: Awaited<ReturnType<typeof api.prediction>>,
): PredictionListItem {
  const evaluation = prediction.commercial_evaluation;
  return {
    prediction_run_id: prediction.prediction_run_id,
    market_id: prediction.market_id,
    market_title: prediction.market_title,
    provider_code: prediction.provider_code ?? "unknown",
    category: prediction.category,
    predicted_at: prediction.predicted_at,
    market_probability: prediction.market_probability,
    consensus_probability: prediction.consensus_probability,
    consensus_confidence: prediction.consensus_confidence,
    estimated_outcome: prediction.estimated_outcome,
    commercial_label: evaluation?.commercial_label ?? "not_evaluable",
    potential_side: evaluation?.potential_side ?? "none",
    gross_edge: evaluation?.gross_edge ?? null,
    net_edge: evaluation?.net_edge ?? null,
    is_actionable: evaluation?.is_actionable ?? false,
    primary_reason:
      evaluation?.reasons[0] ??
      prediction.abstention_reason ??
      "commercial_evaluation_unavailable",
    portfolio_has_open_position:
      evaluation?.portfolio_has_open_position ?? false,
    data_freshness_status:
      evaluation?.data_freshness_status ?? "unavailable",
    campaign_id: evaluation?.campaign_id ?? null,
    portfolio_id: evaluation?.portfolio_id ?? null,
  };
}

function commercialLabel(label: CommercialLabel, copy: Copy): string {
  if (label === "actionable") return copy.actionable;
  if (label === "not_actionable") return copy.notActionable;
  return copy.notEvaluable;
}

function probability(value: string | null): string {
  if (value === null) return "—";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function signedPoints(value: string | null): string {
  if (value === null) return "—";
  const points = Number(value) * 100;
  return `${points > 0 ? "+" : ""}${points.toFixed(2)} pp`;
}

function positiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function humanReason(value: string): string {
  return value.replaceAll("_", " ");
}
