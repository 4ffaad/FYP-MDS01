"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getResult, getSession } from "@/lib/api";
import { formatSubmittedAt } from "@/lib/format";
import type { AnalysisResult, PredictionLabel, ResearchAttribution, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { RecordingNavigator } from "./RecordingNavigator";
import { PredictionTimeline } from "./PredictionTimeline";
import { SignalViewer } from "./SignalViewer";

/** Render one recording result within its session-scoped navigation context. */
export function ResultScreen({ recordId }: { recordId: string }) {
  return <ResultContent key={recordId} recordId={recordId} />;
}

/** Load and render a fresh result whenever the selected recording changes. */
function ResultContent({ recordId }: { recordId: string }) {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      try {
        const nextResult = await getResult(recordId, controller.signal);
        if (controller.signal.aborted) return;
        setResult(nextResult);
        try {
          const nextSession = await getSession(nextResult.sessionId, controller.signal);
          if (!controller.signal.aborted) setSession(nextSession);
        } catch (sessionError) {
          if (sessionError instanceof DOMException && sessionError.name === "AbortError") return;
        }
      } catch (loadError: unknown) {
        if (loadError instanceof DOMException && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "The result could not be loaded.");
      }
    };
    void load();
    return () => controller.abort();
  }, [recordId]);

  if (error) return <ResultError message={error} />;
  if (!result) return <div className="page-frame"><div className="h-56 animate-pulse rounded-lg border border-rule bg-surface" aria-label="Loading result" /></div>;

  const copy = predictionCopy(result.prediction, result.scoreType);
  const hasAlerts = result.flaggedWindowCount > 0;
  const firstAlert = result.alertIntervals[0] ?? null;
  const flaggedSummary = hasAlerts ? `${result.flaggedWindowCount} flagged windows` : "No flagged windows";

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" href={`/sessions/${encodeURIComponent(result.sessionId)}`}><Icon name="back" className="size-4" />Back to session</Link>

        <section className="mt-5 panel overflow-hidden" aria-labelledby="result-heading">
          <div className="flex flex-col justify-between gap-6 px-5 py-6 sm:px-8 sm:py-8 lg:flex-row lg:items-center">
            <div className="flex items-start gap-4">
              <div className={`mt-1 grid size-11 shrink-0 place-items-center rounded-full ${copy.tone === "red" ? "bg-red-soft text-red" : copy.tone === "amber" ? "bg-amber-soft text-amber" : "bg-teal-soft text-teal-dark"}`}><Icon name={copy.icon} className="size-5" /></div>
              <div>
                <h1 id="result-heading" className="max-w-2xl text-[clamp(1.9rem,4vw,2.75rem)] font-semibold leading-[1.08] tracking-[-0.035em] text-ink">{copy.title}</h1>
                <p className="mt-3 text-sm text-ink-muted">{result.recordingLabel}<span className="mx-2 text-rule-strong">·</span><Link className="font-semibold text-teal-dark underline underline-offset-4" href={`/sessions/${encodeURIComponent(result.sessionId)}`}>View session</Link></p>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">{copy.note}</p>
              </div>
            </div>
            <div className="border-t border-rule pt-5 lg:min-w-64 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
              <p className={`text-xl font-semibold tracking-[-0.025em] ${copy.tone === "red" ? "text-red" : copy.tone === "amber" ? "text-amber" : "text-teal-dark"}`}>{flaggedSummary}</p>
              <p className="mt-1 text-xs text-ink-muted">{result.flaggedWindowCount} of {result.windowCount} scored windows</p>
              {firstAlert && <p className="mt-3 font-mono text-sm font-semibold tabular-nums text-ink">{formatOffset(firstAlert.startSeconds)}–{formatOffset(firstAlert.endSeconds)} <span className="font-sans font-normal text-ink-muted">first flagged interval</span></p>}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule bg-surface-soft px-5 py-3.5 text-xs text-ink-muted sm:px-8"><span className="inline-flex items-center gap-1.5 font-semibold text-ink"><span className={`size-1.5 rounded-full ${copy.tone === "red" ? "bg-red" : copy.tone === "amber" ? "bg-amber" : "bg-teal"}`} aria-hidden="true" />Result available</span><span className="text-rule-strong">|</span><span>{result.modelName} · {result.nonClinical ? "non-clinical" : "reviewed runtime"}</span></div>
        </section>

        <div className="mt-6 space-y-6">
          {session && <RecordingNavigator session={session} activeRecordId={result.recordId} />}

          <section className="flex items-start gap-3 rounded-xl bg-surface-soft px-5 py-4 sm:px-7" aria-labelledby="explanation-heading">
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-teal-soft text-teal-dark" aria-hidden="true"><Icon name="info" className="size-4" /></span>
            <div>
              <h2 id="explanation-heading" className="text-sm font-bold">How to read this output</h2>
              <p className="mt-1 max-w-4xl text-sm leading-6 text-ink-muted">{result.explanationSummary}</p>
              {result.nonClinical && <p className="mt-1 text-sm leading-6 text-amber"><span className="font-semibold">Development output only.</span> This processing result is not a clinical prediction.</p>}
            </div>
          </section>

          {hasAlerts && <SignalViewer recordId={result.recordId} predictionWindows={result.predictionWindows} recordingDurationSeconds={result.recordingDurationSeconds} />}

          {result.researchAttributions.length > 0 && <ResearchEvidence attributions={result.researchAttributions} />}

          <section className="panel overflow-hidden" aria-labelledby="timeline-heading">
            <div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="timeline-heading" className="text-base font-bold tracking-[-0.015em]">Prediction score timeline</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-ink-muted">Full-recording overview. Highlighted windows crossed the configured threshold; select a point for its exact time.</p></div>
            <div className="px-5 py-5 sm:px-7 sm:py-7"><PredictionTimeline predictions={result.predictionWindows} durationSeconds={result.recordingDurationSeconds} threshold={result.threshold} /></div>
          </section>

          <section className="panel overflow-hidden" aria-labelledby="details-heading">
            <details>
              <summary id="details-heading" className="cursor-pointer px-5 py-5 text-base font-bold sm:px-7">Technical details</summary>
              <div className="border-t border-rule px-5 py-2 sm:px-7"><dl className="grid gap-x-8 sm:grid-cols-2"><Detail label="Privacy treatment" value={result.privacyMethods.map((method) => method.label).join(" + ")} /><Detail label="Submitted" value={formatSubmittedAt(result.submittedAt)} /><Detail label="Recording ID" value={result.recordId} mono /><Detail label="Session ID" value={result.sessionId} mono /><Detail label="Model" value={result.modelName} mono /><Detail label="Version" value={result.modelVersion} mono /><Detail label="Score semantics" value={formatScoreType(result.scoreType)} /><Detail label="Alert threshold" value={result.threshold.toFixed(2)} mono /><Detail label={result.scoreType === "calibrated_probability" ? "Peak calibrated probability" : "Peak model score"} value={`${result.peakWindowScore.toFixed(3)} — ${result.scoreType === "calibrated_probability" ? "calibrated" : "uncalibrated"}`} mono /><Detail label="Calibration" value={result.calibrationMethod ?? "Not calibrated"} /><Detail label="Window coverage" value={`${result.flaggedWindowCount} of ${result.windowCount} flagged (${Math.round(result.flaggedWindowFraction * 100)}%)`} /></dl></div>
            </details>
          </section>
        </div>
      </div>
    </div>
  );
}

/** Render bounded SHAP sensitivity summaries without presenting clinical causation. */
function ResearchEvidence({ attributions }: { attributions: ResearchAttribution[] }) {
  const strongest = attributions[0];
  const maxChannelScore = Math.max(...strongest.channelScores.map((item) => item.meanAbsoluteAttribution), 1e-9);
  const maxTimeScore = Math.max(...strongest.timeBins.map((bin) => Math.max(...bin.channelScores)), 1e-9);
  return (
    <section className="panel overflow-hidden" aria-labelledby="evidence-heading">
      <div className="border-b border-rule px-5 py-5 sm:px-7">
        <h2 id="evidence-heading" className="text-base font-bold">Model evidence</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-ink-muted">Research attribution for the highest flagged window. It shows which input regions influenced the score most; it does not explain why a seizure occurred.</p>
      </div>
      <div className="grid gap-6 px-5 py-5 sm:px-7 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">Highest flagged window</p>
          <p className="mt-1 font-mono text-sm font-semibold tabular-nums text-ink">{formatOffset(strongest.windowStartSeconds)}–{formatOffset(strongest.windowEndSeconds)} · score {strongest.score.toFixed(3)}</p>
          <div className="mt-5 space-y-2" aria-label="Top contributing channels">
            {strongest.channelScores.slice().sort((left, right) => right.meanAbsoluteAttribution - left.meanAbsoluteAttribution).slice(0, 5).map((channel) => (
              <div key={channel.label} className="grid grid-cols-[4.5rem_minmax(0,1fr)_3.5rem] items-center gap-3 text-xs">
                <span className="font-mono text-ink-muted">{channel.label}</span>
                <span className="h-2 rounded-full bg-surface-muted"><span className="block h-full rounded-full bg-teal" style={{ width: `${Math.max(4, (channel.meanAbsoluteAttribution / maxChannelScore) * 100)}%` }} /></span>
                <span className="font-mono text-right tabular-nums text-ink-muted">{channel.meanAbsoluteAttribution.toFixed(3)}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">Relative sensitivity over 4 seconds</p>
          <div className="mt-4 flex h-20 items-end gap-1" aria-label="Relative SHAP sensitivity across the flagged window">
            {strongest.timeBins.map((bin) => {
              const score = Math.max(...bin.channelScores);
              return <span key={`${bin.startSeconds}-${bin.endSeconds}`} className="min-w-0 flex-1 rounded-t-sm bg-teal" style={{ height: `${Math.max(4, (score / maxTimeScore) * 100)}%` }} title={`${bin.startSeconds.toFixed(2)}–${bin.endSeconds.toFixed(2)} seconds`} />;
            })}
          </div>
          <div className="mt-2 flex justify-between font-mono text-[0.68rem] text-ink-faint"><span>0:00</span><span>0:04</span></div>
          <p className="mt-4 rounded-md bg-amber-soft px-3 py-2 text-xs leading-5 text-amber">Research attribution only. This is model sensitivity, not a clinical explanation.</p>
        </div>
      </div>
    </section>
  );
}

/** Format one relative recording offset for a model score interval. */
function formatOffset(seconds: number): string {
  const wholeSeconds = Math.max(0, Math.round(seconds));
  return `${Math.floor(wholeSeconds / 60)}:${String(wholeSeconds % 60).padStart(2, "0")}`;
}

/** Render a concise headline that distinguishes development and reviewed output. */
function predictionCopy(prediction: PredictionLabel, scoreType: string): { title: string; note: string; icon: "check" | "alert"; tone: "teal" | "amber" | "red" } {
  const development = scoreType === "development_score";
  const calibrated = scoreType === "calibrated_probability";
  if (prediction === "seizure") return {
    title: development ? "Development flag" : calibrated ? "Model alert" : "Research threshold flag",
    note: development ? "Threshold-crossing windows were found in the development pipeline. Review the highlighted times below." : calibrated ? "The model crossed its configured threshold in one or more windows. Review the highlighted times below." : "The uncalibrated research model crossed its configured threshold. Review the highlighted times below.",
    icon: "alert",
    tone: calibrated ? "red" : "amber",
  };
  if (prediction === "no-seizure") return {
    title: "No flagged windows",
    note: development ? "No development window crossed the configured threshold." : "No model window crossed the configured threshold.",
    icon: "check",
    tone: "teal",
  };
  return { title: "Result needs review", note: "The analysis did not produce a complete interpretable result.", icon: "alert", tone: "amber" };
}

/** Turn stored score semantics into a readable result-detail label. */
function formatScoreType(scoreType: string): string {
  if (scoreType === "calibrated_probability") return "Calibrated probability";
  if (scoreType === "development_score") return "Development score";
  return scoreType.replaceAll("_", " ");
}

/** Render one labelled technical detail in the collapsed result panel. */
function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return <div className="flex flex-col gap-1 border-b border-rule py-3 last:border-b-0"><dt className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">{label}</dt><dd className={`text-sm text-ink ${mono ? "font-mono" : "font-semibold"}`}>{value}</dd></div>;
}

/** Render a recoverable result-loading error. */
function ResultError({ message }: { message: string }) {
  return <div className="page-frame"><div className="max-w-xl rounded-lg border border-red/30 bg-red-soft px-5 py-6" role="alert"><Icon name="alert" className="size-5 text-red" /><h1 className="mt-4 text-xl font-bold text-ink">Result unavailable</h1><p className="mt-2 text-sm leading-6 text-red">{message}</p><Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4" href="/dashboard">Return to dashboard <Icon name="arrow" className="size-4" /></Link></div></div>;
}
