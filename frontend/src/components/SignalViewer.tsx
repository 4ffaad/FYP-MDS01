"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ENABLE_FULL_SIGNAL_PREVIEW, ENABLE_SIGNAL_PREVIEW, getSignalPreview } from "@/lib/api";
import type { PredictionWindow, SignalPreview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Icon } from "./Icon";

const CONTEXT_BEFORE_SECONDS = 600;
const VIEWPORT_SECONDS = 10;
const VIEWPORT_POINTS = 1800;

/** Fetch and render one readable time window from a retained EEG representation. */
export function SignalViewer({ recordId, predictionWindows, recordingDurationSeconds }: { recordId: string; predictionWindows: PredictionWindow[]; recordingDurationSeconds: number }) {
  const alertWindows = useMemo(
    () => predictionWindows.filter((window) => window.seizureDetected),
    [predictionWindows],
  );
  const firstAlert = alertWindows[0];
  const retainedRanges = useMemo(() => mergeRetainedRanges(alertWindows, recordingDurationSeconds), [alertWindows, recordingDurationSeconds]);
  const browseStart = ENABLE_FULL_SIGNAL_PREVIEW ? 0 : retainedRanges[0]?.[0] ?? 0;
  const browseEnd = ENABLE_FULL_SIGNAL_PREVIEW
    ? Math.max(recordingDurationSeconds, VIEWPORT_SECONDS)
    : Math.max(retainedRanges.at(-1)?.[1] ?? firstAlert?.endSeconds ?? VIEWPORT_SECONDS, browseStart + 4);
  const viewportDuration = Math.min(VIEWPORT_SECONDS, Math.max(4, browseEnd - browseStart));
  const maxStart = Math.max(browseStart, browseEnd - viewportDuration);
  const initialStart = clamp((firstAlert?.startSeconds ?? browseStart) - 2, browseStart, maxStart);
  const [sliderStart, setSliderStart] = useState(initialStart);
  const [requestStart, setRequestStart] = useState(initialStart);
  const [preview, setPreview] = useState<SignalPreview | null>(null);
  const [loading, setLoading] = useState(ENABLE_SIGNAL_PREVIEW && Boolean(firstAlert));
  const [unavailable, setUnavailable] = useState<string | null>(null);

  useEffect(() => {
    if (!ENABLE_SIGNAL_PREVIEW || !firstAlert) return;
    const controller = new AbortController();
    void getSignalPreview(recordId, requestStart, viewportDuration, VIEWPORT_POINTS, controller.signal)
      .then(setPreview)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setUnavailable(error instanceof Error ? error.message : "The retained EEG view is unavailable.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [firstAlert, recordId, requestStart, viewportDuration]);

  if (!firstAlert) return null;
  if (!ENABLE_SIGNAL_PREVIEW) return <SignalNotice>EEG viewing is disabled because the signal can remain biometrically sensitive.</SignalNotice>;

  const moveTo = (nextStart: number) => {
    const bounded = clamp(nextStart, browseStart, maxStart);
    setSliderStart(bounded);
    if (bounded !== requestStart) {
      setLoading(true);
      setUnavailable(null);
      setRequestStart(bounded);
    }
  };
  const currentEnd = Math.min(browseEnd, sliderStart + viewportDuration);
  const representation = preview?.representation === "signal-obfuscated" ? "Signal obfuscated" : "Metadata scrubbed";

  return (
    <section className="panel overflow-hidden" aria-labelledby="signal-heading">
      <SignalHeader fullPreview={ENABLE_FULL_SIGNAL_PREVIEW} representation={representation} />

      <div className="border-b border-rule bg-surface-soft px-5 py-4 sm:px-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-sm font-semibold text-ink">Viewing {formatTime(sliderStart)}–{formatTime(currentEnd)}</p>
              <p className="font-mono text-xs tabular-nums text-ink-muted">{formatTime(browseStart)} <span aria-hidden="true">—</span> {formatTime(browseEnd)}</p>
            </div>
            <div className="relative mt-4 px-1">
              {alertWindows.filter((window) => window.endSeconds > browseStart && window.startSeconds < browseEnd).map((window, index) => {
                const range = Math.max(1, browseEnd - browseStart);
                const left = ((window.startSeconds - browseStart) / range) * 100;
                return <span key={`${window.startSeconds}-${index}`} className="pointer-events-none absolute top-1/2 z-10 h-3 w-0.5 -translate-y-1/2 bg-amber" style={{ left: `${clamp(left, 0, 100)}%` }} aria-hidden="true" />;
              })}
              <Slider
                min={browseStart}
                max={maxStart}
                step={1}
                disabled={maxStart <= browseStart}
                value={[sliderStart]}
                onValueChange={([value]) => setSliderStart(value ?? browseStart)}
                onValueCommit={([value]) => moveTo(value ?? browseStart)}
                aria-label="EEG review window start time"
                aria-valuetext={`Showing ${formatTime(sliderStart)} to ${formatTime(currentEnd)} of the retained EEG`}
                className="[&_[data-slot=slider-track]]:h-2 [&_[data-slot=slider-track]]:bg-rule [&_[data-slot=slider-range]]:bg-teal [&_[data-slot=slider-thumb]]:size-5 [&_[data-slot=slider-thumb]]:border-2 [&_[data-slot=slider-thumb]]:border-teal [&_[data-slot=slider-thumb]]:bg-white"
              />
            </div>
            <p className="mt-2 text-xs text-ink-muted">Drag to move through the recording. Amber ticks mark windows that crossed the model threshold.</p>
          </div>

          <div className="flex shrink-0 flex-wrap gap-2">
            <Button variant="outline" size="lg" className="border-rule-strong bg-surface" disabled={sliderStart <= browseStart || loading} onClick={() => moveTo(sliderStart - viewportDuration)}>
              <Icon name="back" className="size-4" /> Previous
            </Button>
            <Button variant="outline" size="lg" className="border-rule-strong bg-surface" disabled={sliderStart >= maxStart || loading} onClick={() => moveTo(sliderStart + viewportDuration)}>
              Next <Icon name="arrow" className="size-4" />
            </Button>
            <Button variant="secondary" size="lg" disabled={loading} onClick={() => moveTo(initialStart)}>First flag</Button>
          </div>
        </div>
      </div>

      <div className="px-4 py-5 sm:px-7 sm:py-7">
        {loading && !preview ? (
          <div className="h-[39rem] animate-pulse rounded-lg bg-surface-soft" aria-label="Loading EEG review window" />
        ) : unavailable ? (
          <div className="rounded-lg border border-amber/30 bg-amber-soft px-4 py-4 text-sm text-amber" role="status">{unavailable}</div>
        ) : preview ? (
          <SignalCanvas preview={preview} />
        ) : null}
        {loading && preview && <p className="mt-3 inline-flex items-center gap-2 text-xs text-ink-muted" role="status"><Icon name="spinner" className="size-3.5 animate-spin" />Loading the selected window…</p>}

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-muted">
          <span className="inline-flex items-center gap-2"><span className="h-0.5 w-4 bg-[#315f93]" aria-hidden="true" />Display-normalized EEG</span>
          <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm bg-amber/70" aria-hidden="true" />Threshold crossing</span>
          <span>{representation} representation</span>
        </div>
        <p className="mt-3 text-xs leading-5 text-ink-muted">Each channel is normalized for display only. The stored signal and model input are not changed by this viewer.</p>
      </div>
    </section>
  );
}

function SignalHeader({ fullPreview, representation }: { fullPreview: boolean; representation: string }) {
  return (
    <div className="flex flex-col gap-3 px-5 py-5 sm:flex-row sm:items-start sm:justify-between sm:px-7">
      <div>
        <h2 id="signal-heading" className="text-lg font-bold tracking-[-0.02em]">EEG waveform review</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-ink-muted">Ten seconds are shown at a time so the 18 channels remain readable. {fullPreview ? "The complete retained recording is available in this local-development view." : "Only retained context around the first flagged window is available."}</p>
      </div>
      <span className="w-fit rounded-full border border-rule bg-surface-soft px-3 py-1 text-xs font-semibold text-ink-muted">{representation}</span>
    </div>
  );
}

function SignalNotice({ children }: { children: string }) {
  return <section className="rounded-lg border border-rule bg-surface-soft px-5 py-5 sm:px-7" aria-label="Signal preview notice"><div className="flex items-start gap-3"><Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" /><p className="text-sm leading-6 text-ink-muted">{children}</p></div></section>;
}

function SignalCanvas({ preview }: { preview: SignalPreview }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || preview.channels.length === 0 || preview.timeSeconds.length === 0) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    const draw = () => {
      const width = Math.max(320, parent.clientWidth);
      const height = Math.max(520, preview.channels.length * 32 + 58);
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      canvas.style.height = `${height}px`;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, width, height);
      context.fillStyle = "#fbfcfe";
      context.fillRect(0, 0, width, height);
      const left = 78;
      const right = width - 14;
      const top = 18;
      const bottom = height - 38;
      const rowHeight = (bottom - top) / preview.channels.length;
      const times = preview.timeSeconds;
      const orderedIndices: number[] = [];
      let latestTime = Number.NEGATIVE_INFINITY;
      times.forEach((time, index) => {
        if (Number.isFinite(time) && time > latestTime) {
          orderedIndices.push(index);
          latestTime = time;
        }
      });
      if (orderedIndices.length === 0) return;
      const minTime = times[orderedIndices[0]];
      const maxTime = times[orderedIndices.at(-1) ?? orderedIndices[0]] || minTime + 1;
      const timeRange = Math.max(1, maxTime - minTime);
      const xFor = (time: number) => left + ((time - minTime) / timeRange) * (right - left);

      context.strokeStyle = "#e6e9ee";
      context.lineWidth = 1;
      [0, 0.25, 0.5, 0.75, 1].forEach((fraction) => {
        const x = left + fraction * (right - left);
        context.beginPath();
        context.moveTo(x, top);
        context.lineTo(x, bottom);
        context.stroke();
      });

      preview.flaggedIntervals.forEach((interval) => {
        const start = Math.max(minTime, interval.startSeconds);
        const end = Math.min(maxTime, interval.endSeconds);
        if (end <= start) return;
        context.fillStyle = "rgba(245, 158, 11, 0.20)";
        context.fillRect(xFor(start), top, Math.max(3, xFor(end) - xFor(start)), bottom - top);
      });

      context.font = "11px SFMono-Regular, Consolas, monospace";
      context.textBaseline = "middle";
      preview.channels.forEach((channel, channelIndex) => {
        const center = top + rowHeight * channelIndex + rowHeight / 2;
        context.strokeStyle = "#e1e5ea";
        context.lineWidth = 1;
        context.beginPath();
        context.moveTo(left, center);
        context.lineTo(right, center);
        context.stroke();
        context.fillStyle = "#5d6673";
        context.fillText(channel.label, 10, center);
        const channelIndices = orderedIndices.filter((index) => index < channel.samples.length);
        const mean = channelIndices.reduce((sum, index) => sum + channel.samples[index], 0) / Math.max(1, channelIndices.length);
        const variance = channelIndices.reduce((sum, index) => sum + (channel.samples[index] - mean) ** 2, 0) / Math.max(1, channelIndices.length);
        const scale = Math.max(0.0001, Math.sqrt(variance));
        context.strokeStyle = "#315f93";
        context.lineWidth = 1.15;
        context.beginPath();
        channelIndices.forEach((index, pointIndex) => {
          const sample = channel.samples[index];
          const time = times[index];
          const normalized = Math.max(-3, Math.min(3, (sample - mean) / scale));
          const x = xFor(time);
          const y = center - normalized * Math.min(10, rowHeight * 0.32);
          if (pointIndex === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        });
        context.stroke();
      });

      context.fillStyle = "#667085";
      context.font = "11px SFMono-Regular, Consolas, monospace";
      context.textBaseline = "top";
      [0, 0.5, 1].forEach((fraction) => {
        const time = minTime + fraction * timeRange;
        const x = xFor(time);
        context.textAlign = fraction === 0 ? "left" : fraction === 1 ? "right" : "center";
        context.fillText(formatTime(time), x, bottom + 12);
      });
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(parent);
    return () => observer.disconnect();
  }, [preview]);

  const intervalText = preview.flaggedIntervals.map((interval) => `${formatTime(interval.startSeconds)}–${formatTime(interval.endSeconds)}`).join(", ");
  return (
    <div>
      <canvas ref={canvasRef} className="block w-full rounded-lg border border-rule" role="img" aria-label={`Display-normalized 18-channel EEG from ${formatTime(preview.timeSeconds[0] ?? 0)} to ${formatTime(preview.timeSeconds.at(-1) ?? 0)} with model threshold overlays`} />
      <p className="mt-3 text-xs text-ink-muted">Threshold crossings in this view: <span className="font-mono font-semibold text-amber">{intervalText || "none"}</span></p>
    </div>
  );
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

/** Match backend retention: keep up to ten minutes before every alert window. */
function mergeRetainedRanges(alertWindows: PredictionWindow[], recordingDurationSeconds: number): Array<[number, number]> {
  const ranges = alertWindows
    .map((window) => [
      Math.max(0, window.startSeconds - CONTEXT_BEFORE_SECONDS),
      Math.min(recordingDurationSeconds, window.endSeconds),
    ] as [number, number])
    .filter(([start, end]) => end > start)
    .sort(([left], [right]) => left - right);
  const merged: Array<[number, number]> = [];
  for (const [start, end] of ranges) {
    const previous = merged.at(-1);
    if (previous && start <= previous[1]) previous[1] = Math.max(previous[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const remaining = whole % 60;
  return hours > 0 ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}` : `${minutes}:${String(remaining).padStart(2, "0")}`;
}
