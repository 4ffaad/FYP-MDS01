"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getResult } from "@/lib/api";
import { formatPercent, formatSubmittedAt } from "@/lib/format";
import type { AnalysisResult, PredictionLabel } from "@/lib/types";
import { AttentionHeatmap } from "./AttentionHeatmap";
import { Icon } from "./Icon";

/** Render the result headline first, followed by evidence and run metadata. */
export function ResultScreen({ jobId }: { jobId: string }) {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getResult(jobId, controller.signal).then(setResult).catch((loadError: unknown) => {
      if (loadError instanceof DOMException && loadError.name === "AbortError") return;
      setError(loadError instanceof Error ? loadError.message : "The result could not be loaded.");
    });
    return () => controller.abort();
  }, [jobId]);

  if (error) return <ResultError message={error} />;
  if (!result) return <div className="page-frame"><div className="h-56 animate-pulse rounded-lg border border-rule bg-surface" aria-label="Loading result" /></div>;

  const prediction = predictionCopy(result.prediction);
  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" href="/dashboard"><Icon name="back" className="size-4" />Back to dashboard</Link>

        <section className="mt-5 panel overflow-hidden" aria-labelledby="result-heading">
          <div className="flex flex-col justify-between gap-7 px-5 py-6 sm:px-8 sm:py-8 lg:flex-row lg:items-center">
            <div className="flex items-start gap-4">
              <div className={`mt-1 grid size-11 shrink-0 place-items-center rounded-full ${prediction.tone === "teal" ? "bg-teal-soft text-teal-dark" : prediction.tone === "amber" ? "bg-amber-soft text-amber" : "bg-red-soft text-red"}`}><Icon name={prediction.icon} className="size-5" /></div>
              <div>
                <p className="eyebrow">Analysis result</p>
                <h1 id="result-heading" className="mt-2 max-w-2xl text-[clamp(1.9rem,4vw,3.35rem)] font-semibold leading-[1.05] tracking-tighter text-ink">{prediction.title}</h1>
                <p className="mt-3 text-sm text-ink-muted">{result.recordingLabel}<span className="mx-2 text-rule-strong">·</span><span className="font-mono">{result.jobId}</span></p>
              </div>
            </div>
            <div className="border-t border-rule pt-5 sm:pl-16 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0 lg:text-right"><p className="font-mono text-[clamp(2.5rem,6vw,4rem)] font-semibold leading-none tracking-[-0.07em] text-teal-dark tabular-nums">{formatPercent(result.confidence)}</p><p className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-ink-muted">Model confidence</p></div>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule bg-surface-soft px-5 py-3.5 text-xs text-ink-muted sm:px-8"><span className="inline-flex items-center gap-1.5 font-semibold text-ink"><span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Ready for review</span><span className="text-rule-strong">|</span><span>Development stub · non-clinical</span></div>
        </section>

        <div className="mt-6 grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <section className="panel overflow-hidden" aria-labelledby="evidence-heading">
            <div className="border-b border-rule px-5 py-5 sm:px-7"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><h2 id="evidence-heading" className="text-base font-bold tracking-[-0.015em]">Evidence window</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-ink-muted">{result.signalPreviewAvailable ? "The waveform is paired with the model’s relative attention across this time window." : "Model explanation details remain available without exposing waveform data."}</p></div>{result.signalPreviewAvailable && <div className="flex items-center gap-3 text-[0.68rem] text-ink-muted"><span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-cyan-soft" />Lower</span><span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-amber" />Higher</span></div>}</div></div>
            <div className="px-5 py-5 sm:px-7 sm:py-7">{result.signalPreviewAvailable ? <AttentionHeatmap timeSeries={result.timeSeries} attentionWeights={result.attentionWeights} /> : <p className="rounded-md bg-surface-soft px-4 py-4 text-sm leading-6 text-ink-muted">Signal preview is disabled outside local development because waveform data can remain biometrically sensitive.</p>}<p className="mt-4 text-xs leading-5 text-ink-muted">{result.explanationSummary}</p></div>
          </section>

          <aside className="space-y-4">
            <section className="panel px-5 py-5" aria-labelledby="run-details-heading"><h2 id="run-details-heading" className="text-xs font-bold uppercase tracking-[0.12em] text-ink-faint">Run details</h2><dl className="mt-4 divide-y divide-rule"><Detail label="Requested configuration" value={result.privacyMethod.label} /><Detail label="Submitted" value={formatSubmittedAt(result.submittedAt)} /><Detail label="Model" value={result.modelName} mono /><Detail label="Version" value={result.modelVersion} mono /></dl></section>
            <section className="rounded-lg border border-amber/30 bg-amber-soft px-5 py-5" role="note"><div className="flex items-center gap-2 text-sm font-bold text-amber"><Icon name="info" className="size-4" />Non-clinical output</div><p className="mt-3 text-sm leading-6 text-amber">This result is produced by a deterministic development stub. The attention overlay is an inspection aid, not an automatic clinical explanation.</p></section>
          </aside>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) { return <div className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0"><dt className="text-[0.68rem] uppercase tracking-widest text-ink-faint">{label}</dt><dd className={`text-sm text-ink ${mono ? "font-mono" : "font-semibold"}`}>{value}</dd></div>; }

function predictionCopy(prediction: PredictionLabel): { title: string; icon: "check" | "alert"; tone: "teal" | "amber" | "red" } {
  if (prediction === "seizure") return { title: "Seizure pattern indicated", icon: "alert", tone: "red" };
  if (prediction === "no-seizure") return { title: "No seizure pattern indicated", icon: "check", tone: "teal" };
  return { title: "Review required", icon: "alert", tone: "amber" };
}

function ResultError({ message }: { message: string }) { return <div className="page-frame"><div className="max-w-xl rounded-lg border border-red/30 bg-red-soft px-5 py-6" role="alert"><Icon name="alert" className="size-5 text-red" /><h1 className="mt-4 text-xl font-bold text-ink">Result unavailable</h1><p className="mt-2 text-sm leading-6 text-red">{message}</p><Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4" href="/dashboard">Return to dashboard <Icon name="arrow" className="size-4" /></Link></div></div>; }
