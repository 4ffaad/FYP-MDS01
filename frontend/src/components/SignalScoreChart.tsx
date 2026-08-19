"use client";

import { useEffect, useRef, useState } from "react";
import { getSignalPreview } from "@/lib/api";
import type { PredictionWindow, ReferenceAnnotation, SignalPreview } from "@/lib/types";
import { Icon } from "./Icon";

type SignalScoreChartProps = {
  recordId: string;
  recordingDurationSeconds: number;
  initialSignal: SignalPreview;
  predictions: PredictionWindow[];
  referenceAnnotation: ReferenceAnnotation | null;
};

const VIEW_SECONDS = 10;

/** Browse bounded 18-channel EEG windows with separate score and dataset layers. */
export function SignalScoreChart({ recordId, recordingDurationSeconds, initialSignal, predictions, referenceAnnotation }: SignalScoreChartProps) {
  const maxStart = Math.max(0, recordingDurationSeconds - VIEW_SECONDS);
  const [startSeconds, setStartSeconds] = useState(Math.min(initialSignal.startSeconds, maxStart));
  const [signal, setSignal] = useState(initialSignal);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstLoad = useRef(true);

  useEffect(() => {
    if (firstLoad.current) {
      firstLoad.current = false;
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void getSignalPreview(recordId, startSeconds, controller.signal)
      .then((nextSignal) => {
        if (nextSignal) setSignal(nextSignal);
        else setError("This recording no longer has a local signal preview.");
      })
      .catch((loadError: unknown) => {
        if (loadError instanceof DOMException && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "The EEG window could not be loaded.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [recordId, startSeconds]);

  const move = (seconds: number) => setStartSeconds((current) => Math.min(maxStart, Math.max(0, current + seconds)));
  const firstSeizure = referenceAnnotation?.intervals[0];

  return (
    <div>
      <div className="flex flex-col gap-3 border-b border-rule pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <button className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-rule-strong bg-surface px-3 text-xs font-bold text-ink disabled:opacity-40" type="button" onClick={() => move(-VIEW_SECONDS)} disabled={startSeconds <= 0 || loading}><Icon name="back" className="size-4" />Previous</button>
          <button className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-rule-strong bg-surface px-3 text-xs font-bold text-ink disabled:opacity-40" type="button" onClick={() => move(VIEW_SECONDS)} disabled={startSeconds >= maxStart || loading}>Next<Icon name="arrow" className="size-4" /></button>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-ink-muted">
          <span className="font-mono tabular-nums">{formatTime(signal.startSeconds)}–{formatTime(signal.startSeconds + signal.durationSeconds)} of {formatTime(recordingDurationSeconds)}</span>
          {firstSeizure && <button className="font-bold text-amber underline decoration-amber/40 underline-offset-4" type="button" onClick={() => setStartSeconds(Math.min(maxStart, Math.max(0, firstSeizure.startSeconds - 3)))}>Jump to dataset seizure</button>}
        </div>
      </div>

      <label className="mt-4 block text-xs font-semibold text-ink-muted" htmlFor={`signal-time-${recordId}`}>Recording timeline</label>
      <input id={`signal-time-${recordId}`} className="mt-2 w-full accent-teal" type="range" min="0" max={maxStart} step={VIEW_SECONDS} value={Math.min(startSeconds, maxStart)} onChange={(event) => setStartSeconds(Number(event.target.value))} disabled={maxStart === 0 || loading} />

      {error && <p className="mt-4 rounded-md border border-red/30 bg-red-soft px-4 py-3 text-sm text-red" role="alert">{error}</p>}
      <div className={`mt-4 transition-opacity ${loading ? "opacity-45" : "opacity-100"}`} aria-busy={loading}>
        <StackedSignal signal={signal} predictions={predictions} referenceAnnotation={referenceAnnotation} />
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[0.68rem] text-ink-muted">
        <span><span className="mr-1.5 inline-block size-2.5 rounded-sm bg-red-soft ring-1 ring-red/30" />Dataset seizure annotation</span>
        <span><span className="mr-1.5 inline-block size-2.5 rounded-sm bg-amber-soft ring-1 ring-amber/30" />Development-stub score</span>
        <span>{Math.min(18, signal.samples.length)} model channels · {signal.samplingRate} Hz · independently scaled</span>
      </div>
    </div>
  );
}

/** Draw stacked signal channels and two explicitly separated evidence layers. */
function StackedSignal({ signal, predictions, referenceAnnotation }: { signal: SignalPreview; predictions: PredictionWindow[]; referenceAnnotation: ReferenceAnnotation | null }) {
  const channels = signal.samples.slice(0, 18);
  const labels = signal.channelLabels.slice(0, channels.length);
  const width = 1120;
  const labelWidth = 92;
  const plotWidth = width - labelWidth - 12;
  const scoreTop = 18;
  const scoreHeight = 20;
  const channelTop = 58;
  const rowHeight = 38;
  const height = channelTop + channels.length * rowHeight + 30;
  const windowStart = signal.startSeconds;
  const windowEnd = signal.startSeconds + signal.durationSeconds;
  const x = (seconds: number) => labelWidth + ((seconds - windowStart) / signal.durationSeconds) * plotWidth;
  const visibleAnnotations = (referenceAnnotation?.intervals ?? []).filter((interval) => interval.endSeconds > windowStart && interval.startSeconds < windowEnd);
  const visiblePredictions = predictions.filter((prediction) => prediction.endSeconds > windowStart && prediction.startSeconds < windowEnd);

  return (
    <div className="overflow-x-auto rounded-md border border-rule bg-surface-soft" role="img" aria-label={`${channels.length}-channel de-identified EEG viewer from ${formatTime(windowStart)} to ${formatTime(windowEnd)}`}>
      <svg className="block h-auto min-w-[760px] w-full" viewBox={`0 0 ${width} ${height}`}>
        <title>De-identified multi-channel EEG window</title>
        <desc>Stacked EEG traces with a development-stub score strip and separate CHB-MIT dataset seizure shading.</desc>
        <text x="12" y="32" fill="var(--color-ink-faint)" fontSize="11">Stub score</text>
        <rect x={labelWidth} y={scoreTop} width={plotWidth} height={scoreHeight} fill="var(--color-surface-muted)" rx="3" />
        {visiblePredictions.map((prediction) => {
          const left = x(Math.max(windowStart, prediction.startSeconds));
          const right = x(Math.min(windowEnd, prediction.endSeconds));
          return <rect key={`${prediction.startSeconds}-${prediction.endSeconds}`} x={left} y={scoreTop} width={Math.max(1, right - left)} height={scoreHeight} fill={`hsl(${185 - prediction.probability * 145} 70% ${88 - prediction.probability * 22}%)`} />;
        })}
        {visibleAnnotations.map((interval) => {
          const left = x(Math.max(windowStart, interval.startSeconds));
          const right = x(Math.min(windowEnd, interval.endSeconds));
          return <rect key={`${interval.startSeconds}-${interval.endSeconds}`} x={left} y={channelTop - 8} width={Math.max(2, right - left)} height={channels.length * rowHeight + 8} fill="var(--color-red-soft)" stroke="var(--color-red)" strokeOpacity="0.35" />;
        })}
        {Array.from({ length: Math.floor(signal.durationSeconds / 2) + 1 }, (_, index) => windowStart + index * 2).map((second) => <line key={second} x1={x(second)} y1={channelTop - 8} x2={x(second)} y2={channelTop + channels.length * rowHeight} stroke="var(--color-rule)" strokeWidth="1" />)}
        {channels.map((samples, channelIndex) => {
          const baseline = channelTop + channelIndex * rowHeight + rowHeight / 2;
          const peak = Math.max(0.000001, ...samples.map((value) => Math.abs(value)));
          const step = samples.length > 1 ? plotWidth / (samples.length - 1) : plotWidth;
          const points = samples.map((value, sampleIndex) => `${(labelWidth + sampleIndex * step).toFixed(2)},${(baseline - (value / peak) * rowHeight * 0.36).toFixed(2)}`).join(" ");
          return <g key={`${labels[channelIndex] ?? "channel"}-${channelIndex}`}><text x="12" y={baseline + 4} fill="var(--color-ink-muted)" fontFamily="var(--font-mono)" fontSize="10">{labels[channelIndex] ?? `CH ${channelIndex + 1}`}</text><line x1={labelWidth} y1={baseline} x2={labelWidth + plotWidth} y2={baseline} stroke="var(--color-rule)" strokeWidth="1" /><polyline points={points} fill="none" stroke="var(--color-teal-dark)" strokeWidth="1.25" vectorEffect="non-scaling-stroke" /></g>;
        })}
        <text x={labelWidth} y={height - 10} fill="var(--color-ink-faint)" fontFamily="var(--font-mono)" fontSize="10">{formatTime(windowStart)}</text>
        <text x={labelWidth + plotWidth / 2} y={height - 10} textAnchor="middle" fill="var(--color-ink-faint)" fontFamily="var(--font-mono)" fontSize="10">{formatTime(windowStart + signal.durationSeconds / 2)}</text>
        <text x={labelWidth + plotWidth} y={height - 10} textAnchor="end" fill="var(--color-ink-faint)" fontFamily="var(--font-mono)" fontSize="10">{formatTime(windowEnd)}</text>
      </svg>
    </div>
  );
}

/** Format a recording offset as hours, minutes, and seconds when needed. */
function formatTime(seconds: number): string {
  const wholeSeconds = Math.max(0, Math.round(seconds));
  const hours = Math.floor(wholeSeconds / 3600);
  const minutes = Math.floor((wholeSeconds % 3600) / 60);
  const remainder = wholeSeconds % 60;
  return hours > 0 ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}` : `${minutes}:${String(remainder).padStart(2, "0")}`;
}
