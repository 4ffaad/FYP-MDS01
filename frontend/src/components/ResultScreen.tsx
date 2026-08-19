"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getResult, getSession } from "@/lib/api";
import { formatPercent, formatSubmittedAt } from "@/lib/format";
import type { AnalysisResult, PredictionLabel, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { RecordingNavigator } from "./RecordingNavigator";
import { SignalScoreChart } from "./SignalScoreChart";

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

  const prediction = predictionCopy(result.prediction, result.referenceAnnotation);
  const gridClass = session ? "xl:grid-cols-[224px_minmax(0,1fr)]" : "xl:grid-cols-1";

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" href={`/sessions/${encodeURIComponent(result.sessionId)}`}><Icon name="back" className="size-4" />Back to session</Link>

        <section className="mt-5 panel overflow-hidden" aria-labelledby="result-heading">
          <div className="flex flex-col justify-between gap-7 px-5 py-6 sm:px-8 sm:py-8 lg:flex-row lg:items-center">
            <div className="flex items-start gap-4">
              <div className={`mt-1 grid size-11 shrink-0 place-items-center rounded-full ${prediction.tone === "teal" ? "bg-teal-soft text-teal-dark" : "bg-amber-soft text-amber"}`}><Icon name={prediction.icon} className="size-5" /></div>
              <div>
                <p className="eyebrow">Development model alert</p>
                <h1 id="result-heading" className="mt-2 max-w-2xl text-[clamp(1.9rem,4vw,3.35rem)] font-semibold leading-[1.05] tracking-tighter text-ink">{prediction.title}</h1>
                <p className="mt-3 text-sm text-ink-muted">{result.recordingLabel}<span className="mx-2 text-rule-strong">·</span><span className="font-mono">{result.recordId}</span><span className="mx-2 text-rule-strong">·</span><Link className="font-mono text-teal-dark underline underline-offset-4" href={`/sessions/${encodeURIComponent(result.sessionId)}`}>Session {result.sessionId}</Link></p>
                <ReferenceStatus annotation={result.referenceAnnotation} />
                <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">{prediction.note}</p>
              </div>
            </div>
            <div className="border-t border-rule pt-5 sm:pl-16 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0 lg:text-right"><p className="font-mono text-[clamp(2.5rem,6vw,4rem)] font-semibold leading-none tracking-[-0.07em] text-teal-dark tabular-nums">{formatPercent(result.peakWindowScore)}</p><p className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-ink-muted">Peak window score</p><p className="mt-1 text-xs text-ink-faint">{result.flaggedWindowCount} of {result.windowCount} windows flagged</p><p className="mt-1 text-[0.68rem] text-ink-faint">Not whole-recording confidence</p></div>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule bg-surface-soft px-5 py-3.5 text-xs text-ink-muted sm:px-8"><span className="inline-flex items-center gap-1.5 font-semibold text-ink"><span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Result available</span><span className="text-rule-strong">|</span><span>{result.modelName} · non-clinical</span></div>
        </section>

        <div className={`mt-6 grid items-start gap-6 ${gridClass}`}>
          {session && <div className="order-2 xl:order-none xl:row-span-2 xl:sticky xl:top-5"><RecordingNavigator session={session} activeRecordId={result.recordId} /></div>}

          <section className="order-1 panel overflow-hidden xl:order-none" aria-labelledby="evidence-heading">
            <div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="evidence-heading" className="text-base font-bold tracking-[-0.015em]">EEG recording viewer</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-ink-muted">Inspect a bounded, de-identified 10-second window across the 18 channels used by the model contract. Dataset annotations and development scores remain separate.</p></div>
            <div className="px-5 py-5 sm:px-7 sm:py-7">
              <ReferenceSummary annotation={result.referenceAnnotation} />
              <div className="mt-5">{result.signalPreview ? <SignalScoreChart key={result.recordId} recordId={result.recordId} recordingDurationSeconds={result.recordingDurationSeconds} initialSignal={result.signalPreview} predictions={result.predictionWindows} referenceAnnotation={result.referenceAnnotation} /> : <p className="rounded-md bg-surface-soft px-4 py-4 text-sm leading-6 text-ink-muted">Signal preview is unavailable for this run. Enable it in both environments, rebuild the backend, and upload the ZIP again because previous temporary EDFs were securely removed.</p>}</div>
              <p className="mt-4 text-xs leading-5 text-ink-muted">{result.explanationSummary}</p>
            </div>
          </section>

          <aside className="order-3 grid gap-4 sm:grid-cols-2 xl:order-none xl:col-start-2">
            <section className="panel px-5 py-5" aria-labelledby="run-details-heading"><h2 id="run-details-heading" className="text-xs font-bold uppercase tracking-[0.12em] text-ink-faint">Run details</h2><dl className="mt-4 divide-y divide-rule"><Detail label="Requested configuration" value={result.privacyMethod.label} /><Detail label="Submitted" value={formatSubmittedAt(result.submittedAt)} /><Detail label="Model" value={result.modelName} mono /><Detail label="Version" value={result.modelVersion} mono /><Detail label="Window coverage" value={`${result.flaggedWindowCount} of ${result.windowCount} flagged (${Math.round(result.flaggedWindowFraction * 100)}%)`} /></dl></section>
            <section className="rounded-lg border border-amber/30 bg-amber-soft px-5 py-5" role="note"><div className="flex items-center gap-2 text-sm font-bold text-amber"><Icon name="info" className="size-4" />Non-clinical output</div><p className="mt-3 text-sm leading-6 text-amber">The color band represents the development stub’s numerical score per prediction window. It is not attention, causal reasoning, or a clinical explanation.</p></section>
          </aside>
        </div>
      </div>
    </div>
  );
}

/** Keep research-dataset truth visibly separate from model output. */
function ReferenceSummary({ annotation }: { annotation: AnalysisResult["referenceAnnotation"] }) {
  if (!annotation) return <div className="rounded-md border border-rule bg-surface-soft px-4 py-4"><p className="text-sm font-bold text-ink">Dataset annotation unavailable</p><p className="mt-1 text-xs leading-5 text-ink-muted">This recording was not matched to a CHB-MIT summary or seizure sidecar.</p></div>;
  if (annotation.intervals.length === 0) return <div className="rounded-md border border-rule bg-surface-soft px-4 py-4"><p className="text-sm font-bold text-ink">Dataset annotation: no seizure</p><p className="mt-1 text-xs leading-5 text-ink-muted">The supplied CHB-MIT reference marks this recording as containing no seizure interval.</p></div>;
  return <div className="rounded-md border border-amber/30 bg-amber-soft px-4 py-4"><p className="text-sm font-bold text-amber">Dataset annotation: seizure recorded</p><p className="mt-1 text-xs leading-5 text-amber">{annotation.intervals.length} reference {annotation.intervals.length === 1 ? "interval" : "intervals"}: {annotation.intervals.map((interval) => `${formatOffset(interval.startSeconds)}–${formatOffset(interval.endSeconds)}`).join(", ")}</p></div>;
}

/** Put the supplied dataset label beside the result headline before model detail. */
function ReferenceStatus({ annotation }: { annotation: AnalysisResult["referenceAnnotation"] }) {
  if (!annotation) return <p className="mt-3 inline-flex items-center gap-2 rounded-md border border-rule bg-surface-soft px-3 py-2 text-xs font-semibold text-ink-muted"><Icon name="info" className="size-3.5" />Dataset reference unavailable</p>;
  const hasSeizure = annotation.intervals.length > 0;
  return <p className={`mt-3 inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold ${hasSeizure ? "border-amber/30 bg-amber-soft text-amber" : "border-rule bg-surface-soft text-ink-muted"}`}><Icon name={hasSeizure ? "alert" : "check"} className="size-3.5" />{hasSeizure ? `Dataset reference: seizure annotation · ${annotation.intervals.length} ${annotation.intervals.length === 1 ? "interval" : "intervals"}` : "Dataset reference: no seizure annotation"}</p>;
}

/** Format one relative recording offset for annotation summaries. */
function formatOffset(seconds: number): string {
  const wholeSeconds = Math.round(seconds);
  return `${Math.floor(wholeSeconds / 60)}:${String(wholeSeconds % 60).padStart(2, "0")}`;
}

/** Render an honest headline that distinguishes a model alert from dataset truth. */
function predictionCopy(prediction: PredictionLabel, annotation: AnalysisResult["referenceAnnotation"]): { title: string; note: string; icon: "check" | "alert"; tone: "teal" | "amber" | "red" } {
  const hasReferenceSeizure = (annotation?.intervals.length ?? 0) > 0;
  if (prediction === "seizure") return {
    title: "Development activity flagged",
    note: annotation ? hasReferenceSeizure ? "The deterministic development score flagged a window in a recording with a supplied dataset seizure annotation. This is not a seizure diagnosis." : "The deterministic development score flagged a window, but the supplied dataset reference has no seizure annotation. This is not a seizure diagnosis." : "The deterministic development score flagged a window; no dataset reference was available. This is not a seizure diagnosis.",
    icon: "alert",
    tone: "amber",
  };
  if (prediction === "no-seizure") return {
    title: "No development window flagged",
    note: annotation ? hasReferenceSeizure ? "The deterministic development score did not flag a window in a recording with a supplied dataset seizure annotation." : "The deterministic development score did not flag a window, and the supplied dataset reference has no seizure annotation." : "The deterministic development score did not flag a window; no dataset reference was available.",
    icon: "check",
    tone: "teal",
  };
  return { title: "Development result needs review", note: "The development output could not be interpreted as a completed alert.", icon: "alert", tone: "amber" };
}

/** Render one labelled technical detail in the result side panel. */
function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return <div className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0"><dt className="text-[0.68rem] uppercase tracking-widest text-ink-faint">{label}</dt><dd className={`text-sm text-ink ${mono ? "font-mono" : "font-semibold"}`}>{value}</dd></div>;
}

/** Render a recoverable result-loading error. */
function ResultError({ message }: { message: string }) {
  return <div className="page-frame"><div className="max-w-xl rounded-lg border border-red/30 bg-red-soft px-5 py-6" role="alert"><Icon name="alert" className="size-5 text-red" /><h1 className="mt-4 text-xl font-bold text-ink">Result unavailable</h1><p className="mt-2 text-sm leading-6 text-red">{message}</p><Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4" href="/dashboard">Return to dashboard <Icon name="arrow" className="size-4" /></Link></div></div>;
}
