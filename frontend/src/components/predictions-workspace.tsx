"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowLeft,
  BrainCircuit,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Eye,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  Target,
  X,
  Zap,
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
  PredictionRun,
} from "@/lib/api-types";

type OpportunityFilter = "all" | "actionable" | "not_actionable";

export function PredictionsWorkspace({
  predictionId,
}: Readonly<{ predictionId: string | null }>) {
  if (predictionId) return <PredictionDetail predictionId={predictionId} />;
  return <PredictionList />;
}

function PredictionList() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const page = positiveInt(searchParams.get("page"), 1);
  const filter = opportunityFilter(searchParams.get("view"));
  const query = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "25",
      sort: "predicted_at",
      direction: "desc",
    });
    if (filter !== "all") params.set("commercial_label", filter);
    return params.toString();
  }, [filter, page]);
  const predictions = useQuery({
    queryKey: ["prediction-list", query],
    queryFn: () => api.predictions(query),
    placeholderData: keepPreviousData,
  });
  const [manualTrade, setManualTrade] = useState<PredictionListItem | null>(null);

  const changeFilter = (next: OpportunityFilter) => {
    const params = new URLSearchParams();
    if (next !== "all") params.set("view", next);
    router.push(`/predictions${params.size ? `?${params.toString()}` : ""}`);
  };
  const changePage = (next: number) => {
    const params = new URLSearchParams();
    if (filter !== "all") params.set("view", filter);
    params.set("page", String(next));
    router.push(`/predictions?${params.toString()}`);
  };

  return (
    <div className="space-y-7 animate-page-in">
      <header className="max-w-3xl">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-[#5b43f1]">
          {t("opp.eyebrow")}
        </p>
        <h1 className="mt-2 text-3xl font-black tracking-[-0.04em] sm:text-4xl">
          {t("opp.title")}
        </h1>
        <p className="mt-3 text-base leading-7 text-[#777b87]">
          {t("opp.description")}
        </p>
      </header>

      <section className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-[#182033]/8 bg-white p-3 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {(["all", "actionable", "not_actionable"] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={`interactive-button cursor-pointer rounded-2xl px-4 py-2.5 text-sm font-black ${
                filter === value
                  ? "bg-[#182033] text-white shadow-lg"
                  : "text-[#777b87] hover:bg-[#f5f2ea]"
              }`}
              onClick={() => changeFilter(value)}
            >
              {t(
                value === "all"
                  ? "opp.filter.all"
                  : value === "actionable"
                    ? "opp.filter.opportunities"
                    : "opp.filter.discarded",
              )}
            </button>
          ))}
        </div>
        <span className="px-3 text-xs font-bold text-[#9a9ca5]">
          {t("opp.autoNote")}
        </span>
      </section>

      {predictions.isLoading ? (
        <PredictionLoading />
      ) : predictions.isError ? (
        <PredictionError onRetry={() => void predictions.refetch()} />
      ) : !predictions.data?.items.length ? (
        <PredictionEmpty />
      ) : (
        <div className="space-y-4">
          {predictions.data.items.map((prediction) => (
            <OpportunityCard
              key={prediction.prediction_run_id}
              prediction={prediction}
              onManualTrade={() => setManualTrade(prediction)}
            />
          ))}
        </div>
      )}

      {predictions.data && predictions.data.total_pages > 1 && (
        <nav className="flex items-center justify-center gap-3" aria-label={t("opp.pagination")}>
          <button
            type="button"
            className="interactive-button inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-[#182033]/10 bg-white px-4 py-3 text-sm font-black disabled:cursor-not-allowed disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => changePage(page - 1)}
          >
            <ChevronLeft className="size-4" /> {t("opp.previous")}
          </button>
          <span className="text-sm font-black text-[#777b87]">
            {t("opp.page", { current: page, total: predictions.data.total_pages })}
          </span>
          <button
            type="button"
            className="interactive-button inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-[#182033]/10 bg-white px-4 py-3 text-sm font-black disabled:cursor-not-allowed disabled:opacity-40"
            disabled={page >= predictions.data.total_pages}
            onClick={() => changePage(page + 1)}
          >
            {t("opp.next")} <ChevronRight className="size-4" />
          </button>
        </nav>
      )}

      {manualTrade && (
        <ManualTradeModal prediction={manualTrade} onClose={() => setManualTrade(null)} />
      )}
    </div>
  );
}

function OpportunityCard({
  prediction,
  onManualTrade,
}: Readonly<{ prediction: PredictionListItem; onManualTrade: () => void }>) {
  const { locale, t } = useI18n();
  const actionable = prediction.is_actionable;
  return (
    <article className="executive-card overflow-hidden rounded-[1.75rem] border border-[#182033]/8 bg-white shadow-sm">
      <div className="grid gap-5 p-5 sm:p-7 lg:grid-cols-[1fr_auto] lg:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <OpportunityBadge label={prediction.commercial_label} />
            <span className="text-xs font-bold text-[#9a9ca5]">
              {new Date(prediction.predicted_at).toLocaleString(locale, {
                day: "numeric",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
          <h2 className="mt-4 max-w-3xl text-lg font-black leading-7 tracking-[-0.02em] sm:text-xl">
            {prediction.market_title}
          </h2>
          <div className="mt-5 grid max-w-2xl grid-cols-3 gap-3">
            <DecisionMetric
              label={t("opp.marketThinks")}
              value={probability(prediction.market_probability)}
            />
            <DecisionMetric
              label={t("opp.systemThinks")}
              value={probability(prediction.consensus_probability)}
              highlighted
            />
            <DecisionMetric
              label={t("opp.confidence")}
              value={probability(prediction.consensus_confidence)}
            />
          </div>
          <p className="mt-4 flex items-center gap-2 text-sm font-bold text-[#626777]">
            <BrainCircuit className="size-4 text-[#5b43f1]" />
            {prediction.estimated_outcome
              ? t("opp.systemConclusion", {
                  outcome: t(
                    prediction.estimated_outcome === "yes"
                      ? "opp.outcome.yes"
                      : "opp.outcome.no",
                  ),
                })
              : t("opp.noConclusion")}
          </p>
        </div>

        <div className="flex flex-wrap gap-2 lg:max-w-52 lg:flex-col">
          <Link
            href={`/predictions/${encodeURIComponent(prediction.prediction_run_id)}`}
            className="interactive-button inline-flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-2xl bg-[#182033] px-4 py-3 text-sm font-black text-white"
          >
            <Eye className="size-4" /> {t("opp.understand")}
          </Link>
          <button
            type="button"
            className="interactive-button inline-flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-2xl border border-[#182033]/10 bg-white px-4 py-3 text-sm font-black text-[#626777]"
            onClick={onManualTrade}
          >
            <CircleDollarSign className="size-4" /> {t("opp.manual")}
          </button>
          {actionable && (
            <span className="flex items-center justify-center gap-2 px-2 py-1 text-center text-xs font-bold leading-5 text-[#16845f]">
              <Zap className="size-3.5" /> {t("opp.automaticHandles")}
            </span>
          )}
        </div>
      </div>
    </article>
  );
}

function PredictionDetail({ predictionId }: Readonly<{ predictionId: string }>) {
  const { locale, t } = useI18n();
  const prediction = useQuery({
    queryKey: ["prediction-detail", predictionId],
    queryFn: () => api.prediction(predictionId),
  });
  const [manualTrade, setManualTrade] = useState<PredictionListItem | null>(null);
  if (prediction.isLoading) return <PredictionLoading />;
  if (prediction.isError || !prediction.data) {
    return <PredictionError onRetry={() => void prediction.refetch()} />;
  }
  const value = prediction.data;
  const actionable = value.commercial_evaluation?.is_actionable ?? false;
  const reasons = value.commercial_evaluation?.reasons ?? [];
  const listItem = detailToListItem(value);
  return (
    <div className="space-y-7 animate-page-in">
      <Link
        href="/predictions"
        className="inline-flex cursor-pointer items-center gap-2 text-sm font-black text-[#5b43f1] transition hover:gap-3"
      >
        <ArrowLeft className="size-4" /> {t("opp.detail.back")}
      </Link>

      <section className="relative overflow-hidden rounded-[2rem] bg-[#182033] p-7 text-white shadow-xl sm:p-10">
        <div className="pointer-events-none absolute -right-16 -top-20 size-72 rounded-full bg-[#5b43f1]/35 blur-3xl" />
        <div className="relative">
          <OpportunityBadge
            label={value.commercial_evaluation?.commercial_label ?? "not_evaluable"}
            dark
          />
          <h1 className="mt-5 max-w-4xl text-3xl font-black leading-tight tracking-[-0.04em] sm:text-4xl">
            {value.market_title}
          </h1>
          <p className="mt-4 text-sm font-semibold text-white/50">
            {new Date(value.predicted_at).toLocaleString(locale)}
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <DetailMetric label={t("opp.marketThinks")} value={probability(value.market_probability)} />
            <DetailMetric label={t("opp.systemThinks")} value={probability(value.consensus_probability)} featured />
            <DetailMetric label={t("opp.confidence")} value={probability(value.consensus_confidence)} />
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_.75fr]">
        <section className="rounded-[2rem] border border-[#182033]/8 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex items-start gap-4">
            <span className={`grid size-12 shrink-0 place-items-center rounded-2xl ${actionable ? "bg-[#e9fff4] text-[#16845f]" : "bg-[#fff3d6] text-[#9b6a00]"}`}>
              {actionable ? <Zap className="size-5" /> : <ShieldCheck className="size-5" />}
            </span>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.15em] text-[#8b8e98]">
                {t("opp.detail.inPlainWords")}
              </p>
              <h2 className="mt-2 text-2xl font-black tracking-[-0.03em]">
                {actionable ? t("opp.detail.actionable") : t("opp.detail.notActionable")}
              </h2>
              <p className="mt-3 leading-7 text-[#777b87]">
                {actionable
                  ? t("opp.detail.actionableText")
                  : t("opp.detail.notActionableText")}
              </p>
            </div>
          </div>
          {reasons.length > 0 && (
            <ul className="mt-6 space-y-2">
              {reasons.slice(0, 4).map((reason) => (
                <li key={reason} className="flex items-start gap-2 rounded-2xl bg-[#f7f5f0] px-4 py-3 text-sm font-semibold text-[#626777]">
                  <Check className="mt-0.5 size-4 shrink-0 text-[#5b43f1]" />
                  {humanReason(reason, t)}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-[2rem] border border-[#182033]/8 bg-[#eeeaff] p-6 sm:p-8">
          <span className="grid size-12 place-items-center rounded-2xl bg-white text-[#5b43f1] shadow-sm">
            <Sparkles className="size-5" />
          </span>
          <h2 className="mt-5 text-xl font-black">{t("opp.detail.yourChoice")}</h2>
          <p className="mt-3 text-sm leading-6 text-[#626777]">
            {t("opp.detail.manualText")}
          </p>
          <button
            type="button"
            className="interactive-button mt-5 inline-flex cursor-pointer items-center gap-2 rounded-2xl bg-[#5b43f1] px-5 py-3 text-sm font-black text-white shadow-lg"
            onClick={() => setManualTrade(listItem)}
          >
            <CircleDollarSign className="size-4" /> {t("opp.manual")}
          </button>
        </section>
      </div>

      <section className="rounded-3xl border border-[#182033]/8 bg-white/60 p-5 text-sm font-semibold leading-6 text-[#777b87]">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-[#5b43f1]" />
          <p>{t("opp.detail.auditSaved")}</p>
        </div>
      </section>

      {manualTrade && (
        <ManualTradeModal prediction={manualTrade} onClose={() => setManualTrade(null)} />
      )}
    </div>
  );
}

function ManualTradeModal({
  prediction,
  onClose,
}: Readonly<{ prediction: PredictionListItem; onClose: () => void }>) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [side, setSide] = useState<PositionSide>(
    prediction.estimated_outcome === "no" ? "no" : "yes",
  );
  const [stake, setStake] = useState("1.00");
  const [reason, setReason] = useState("");
  const [result, setResult] = useState<ManualPaperTradeResponse | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      api.manualPaperTrade({
        prediction_run_id: prediction.prediction_run_id,
        side,
        requested_stake: stake,
        override_reason: reason,
        idempotency_key: crypto.randomUUID(),
      }),
    onSuccess: async (response) => {
      setResult(response);
      await queryClient.invalidateQueries({ queryKey: ["paper-trades"] });
      await queryClient.invalidateQueries({ queryKey: ["all-paper-trades"] });
    },
  });
  const canSubmit = reason.trim().length >= 5 && Number(stake) > 0;
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-[#182033]/55 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="manual-trade-title"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="animate-page-in w-full max-w-xl rounded-[2rem] bg-[#fdfcf9] p-6 shadow-2xl sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-[#fff3d6] px-3 py-1.5 text-xs font-black text-[#9b6a00]">
              <CircleDollarSign className="size-3.5" /> {t("opp.modal.simulated")}
            </span>
            <h2 id="manual-trade-title" className="mt-4 text-2xl font-black tracking-[-0.03em]">
              {t("opp.modal.title")}
            </h2>
          </div>
          <button
            type="button"
            className="interactive-button grid size-10 cursor-pointer place-items-center rounded-full bg-[#f2efe8] text-[#626777]"
            onClick={onClose}
            aria-label={t("opp.modal.close")}
          >
            <X className="size-5" />
          </button>
        </div>
        <p className="mt-3 line-clamp-2 text-sm font-bold leading-6 text-[#626777]">
          {prediction.market_title}
        </p>
        <div className="mt-6 rounded-2xl border border-[#ff7759]/15 bg-[#fff0ec] p-4 text-sm leading-6 text-[#8a4939]">
          {t("opp.modal.warning")}
        </div>

        {result ? (
          <div className="mt-6 rounded-2xl bg-[#e9fff4] p-5 text-[#146b50]">
            <p className="font-black">
              {t(
                result.status === "filled"
                  ? "opp.modal.filled"
                  : result.status === "duplicate"
                    ? "opp.modal.duplicate"
                    : "opp.modal.rejected",
              )}
            </p>
            <button type="button" className="interactive-button mt-5 cursor-pointer rounded-xl bg-[#182033] px-4 py-2.5 text-sm font-black text-white" onClick={onClose}>
              {t("opp.modal.done")}
            </button>
          </div>
        ) : (
          <form
            className="mt-6 space-y-5"
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            <fieldset>
              <legend className="text-sm font-black">{t("opp.modal.choose")}</legend>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {(["yes", "no"] as const).map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={`interactive-button cursor-pointer rounded-2xl border px-4 py-3 text-sm font-black ${
                      side === value
                        ? "border-[#5b43f1] bg-[#eeeaff] text-[#5b43f1]"
                        : "border-[#182033]/10 bg-white text-[#777b87]"
                    }`}
                    onClick={() => setSide(value)}
                  >
                    {t(value === "yes" ? "opp.outcome.yes" : "opp.outcome.no")}
                  </button>
                ))}
              </div>
            </fieldset>
            <label className="block text-sm font-black">
              {t("opp.modal.amount")}
              <input
                className="mt-2 w-full rounded-2xl border border-[#182033]/10 bg-white px-4 py-3 outline-none focus:border-[#5b43f1]/50 focus:ring-4 focus:ring-[#5b43f1]/10"
                type="number"
                min="0.01"
                step="0.01"
                value={stake}
                onChange={(event) => setStake(event.target.value)}
              />
            </label>
            <label className="block text-sm font-black">
              {t("opp.modal.reason")}
              <textarea
                className="mt-2 min-h-24 w-full resize-none rounded-2xl border border-[#182033]/10 bg-white px-4 py-3 outline-none focus:border-[#5b43f1]/50 focus:ring-4 focus:ring-[#5b43f1]/10"
                value={reason}
                placeholder={t("opp.modal.reasonPlaceholder")}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            {mutation.isError && (
              <p className="rounded-2xl bg-[#fff0ec] p-4 text-sm font-bold text-[#b84630]">
                {t("opp.modal.error")}
              </p>
            )}
            <div className="flex flex-wrap justify-end gap-2">
              <button type="button" className="interactive-button cursor-pointer rounded-2xl px-5 py-3 text-sm font-black text-[#777b87]" onClick={onClose}>
                {t("opp.modal.cancel")}
              </button>
              <button
                type="submit"
                disabled={!canSubmit || mutation.isPending}
                className="interactive-button inline-flex cursor-pointer items-center gap-2 rounded-2xl bg-[#ff7759] px-5 py-3 text-sm font-black text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-45"
              >
                {mutation.isPending && <LoaderCircle className="size-4 animate-spin" />}
                {t("opp.modal.confirm")}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function OpportunityBadge({ label, dark = false }: Readonly<{ label: CommercialLabel; dark?: boolean }>) {
  const { t } = useI18n();
  const actionable = label === "actionable";
  const text = t(
    actionable
      ? "opp.badge.opportunity"
      : label === "not_actionable"
        ? "opp.badge.noAction"
        : "opp.badge.waiting",
  );
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-black ${dark ? (actionable ? "bg-[#72e0b1]/15 text-[#72e0b1]" : "bg-white/10 text-white/65") : actionable ? "bg-[#e9fff4] text-[#16845f]" : "bg-[#f0f0f2] text-[#777b87]"}`}>
      {actionable ? <Zap className="size-3.5" /> : <ShieldCheck className="size-3.5" />}
      {text}
    </span>
  );
}

function DecisionMetric({ label, value, highlighted = false }: Readonly<{ label: string; value: string; highlighted?: boolean }>) {
  return (
    <div className={`rounded-2xl p-3 sm:p-4 ${highlighted ? "bg-[#eeeaff]" : "bg-[#f7f5f0]"}`}>
      <p className="text-[10px] font-black uppercase tracking-[0.08em] text-[#92949d]">{label}</p>
      <p className={`mt-1 text-xl font-black ${highlighted ? "text-[#5b43f1]" : "text-[#182033]"}`}>{value}</p>
    </div>
  );
}

function DetailMetric({ label, value, featured = false }: Readonly<{ label: string; value: string; featured?: boolean }>) {
  return (
    <div className={`rounded-3xl border p-5 ${featured ? "border-[#8d7cff]/40 bg-[#5b43f1]/35" : "border-white/10 bg-white/7"}`}>
      <p className="text-xs font-black uppercase tracking-[0.12em] text-white/50">{label}</p>
      <p className="mt-2 text-3xl font-black">{value}</p>
    </div>
  );
}

function PredictionLoading() {
  const { t } = useI18n();
  return (
    <div className="grid min-h-80 place-items-center" aria-label={t("loading.label")}>
      <div className="text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#eeeaff] text-[#5b43f1]"><Target className="size-6 animate-pulse" /></span>
        <p className="mt-4 text-sm font-black text-[#777b87]">{t("opp.loading")}</p>
      </div>
    </div>
  );
}

function PredictionError({ onRetry }: Readonly<{ onRetry: () => void }>) {
  const { t } = useI18n();
  return (
    <div className="rounded-[2rem] border border-[#ff7759]/20 bg-white p-8 text-center">
      <h2 className="text-xl font-black">{t("opp.error")}</h2>
      <button type="button" className="interactive-button mt-5 cursor-pointer rounded-2xl bg-[#182033] px-5 py-3 text-sm font-black text-white" onClick={onRetry}>{t("error.retry")}</button>
    </div>
  );
}

function PredictionEmpty() {
  const { t } = useI18n();
  return (
    <div className="grid min-h-72 place-items-center rounded-[2rem] border border-dashed border-[#182033]/15 bg-white/60 p-8 text-center">
      <div>
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#eeeaff] text-[#5b43f1]"><Target className="size-6" /></span>
        <h2 className="mt-5 text-xl font-black">{t("opp.empty")}</h2>
        <p className="mt-2 text-sm text-[#777b87]">{t("opp.emptyText")}</p>
      </div>
    </div>
  );
}

function detailToListItem(value: PredictionRun): PredictionListItem {
  const evaluation = value.commercial_evaluation;
  return {
    prediction_run_id: value.prediction_run_id,
    market_id: value.market_id,
    market_title: value.market_title,
    provider_code: value.provider_code ?? "unknown",
    category: value.category,
    predicted_at: value.predicted_at,
    market_probability: value.market_probability,
    consensus_probability: value.consensus_probability,
    consensus_confidence: value.consensus_confidence,
    estimated_outcome: value.estimated_outcome,
    commercial_label: evaluation?.commercial_label ?? "not_evaluable",
    potential_side: evaluation?.potential_side ?? "none",
    gross_edge: evaluation?.gross_edge ?? null,
    net_edge: evaluation?.net_edge ?? null,
    is_actionable: evaluation?.is_actionable ?? false,
    primary_reason: evaluation?.reasons[0] ?? "not_evaluable",
    portfolio_has_open_position: evaluation?.portfolio_has_open_position ?? false,
    data_freshness_status: evaluation?.data_freshness_status ?? "unavailable",
    campaign_id: evaluation?.campaign_id ?? null,
    portfolio_id: evaluation?.portfolio_id ?? null,
  };
}

function humanReason(value: string, t: ReturnType<typeof useI18n>["t"]): string {
  const normalized = value.toLowerCase();
  if (normalized.includes("confidence")) return t("opp.reason.confidence");
  if (normalized.includes("edge")) return t("opp.reason.edge");
  if (normalized.includes("fresh") || normalized.includes("stale")) return t("opp.reason.freshness");
  if (normalized.includes("position")) return t("opp.reason.position");
  if (normalized.includes("risk") || normalized.includes("exposure")) return t("opp.reason.risk");
  return t("opp.reason.policy");
}

function probability(value: string | null): string {
  return value === null ? "—" : `${(Number(value) * 100).toFixed(0)}%`;
}

function positiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function opportunityFilter(value: string | null): OpportunityFilter {
  return value === "actionable" || value === "not_actionable" ? value : "all";
}
