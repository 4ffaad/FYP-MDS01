"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ENABLE_FULL_SIGNAL_PREVIEW,
  ENABLE_SIGNAL_PREVIEW,
  getSignalPreview,
} from "@/lib/api";
import type { PredictionWindow, SignalPreview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";

const CONTEXT_BEFORE_SECONDS = 600;
const DEFAULT_VIEWPORT_SECONDS = 10;
const VIEWPORT_OPTIONS = [5, 10, 20, 60, 110];
const VIEWPORT_POINTS = 10_000;
const CHANNEL_ROW_HEIGHT = 52;
const PLOT_LEFT = 72;
const PLOT_RIGHT = 14;
const CHANNEL_DISPLAY_ORDER = [
  "FP2-F8",
  "F8-T8",
  "T8-P8",
  "P8-O2",
  "FP1-F7",
  "F7-T7",
  "T7-P7",
  "P7-O1",
  "FP2-F4",
  "F4-C4",
  "C4-P4",
  "P4-O2",
  "FP1-F3",
  "F3-C3",
  "C3-P3",
  "P3-O1",
  "FZ-CZ",
  "CZ-PZ",
];

export type SignalSeekRequest = {
  timeSeconds: number;
  requestId: number;
};

/** Fetch and render one readable window from the retained EEG preview. */
export function SignalViewer({
  recordId,
  predictionWindows,
  recordingDurationSeconds,
  selectedEegTime = null,
  selectionRequest = null,
  onEegTimeSelect,
  embedded = false,
}: {
  recordId: string;
  predictionWindows: PredictionWindow[];
  recordingDurationSeconds: number;
  selectedEegTime?: number | null;
  selectionRequest?: SignalSeekRequest | null;
  onEegTimeSelect?: (seconds: number) => void;
  embedded?: boolean;
}) {
  const [viewportSeconds, setViewportSeconds] = useState(
    DEFAULT_VIEWPORT_SECONDS,
  );
  const [traceGain, setTraceGain] = useState(0.5);
  const alertWindows = useMemo(
    () => predictionWindows.filter((window) => window.seizureDetected),
    [predictionWindows],
  );
  const firstAlert = alertWindows[0];
  const retainedRanges = useMemo(
    () => mergeRetainedRanges(alertWindows, recordingDurationSeconds),
    [alertWindows, recordingDurationSeconds],
  );
  const browseStart = ENABLE_FULL_SIGNAL_PREVIEW
    ? 0
    : (retainedRanges[0]?.[0] ?? 0);
  const browseEnd = ENABLE_FULL_SIGNAL_PREVIEW
    ? Math.max(recordingDurationSeconds, DEFAULT_VIEWPORT_SECONDS)
    : Math.max(
        retainedRanges.at(-1)?.[1] ??
          firstAlert?.endSeconds ??
          DEFAULT_VIEWPORT_SECONDS,
        browseStart + 4,
      );
  const viewportDuration = Math.min(
    viewportSeconds,
    Math.max(4, browseEnd - browseStart),
  );
  const maxStart = Math.max(browseStart, browseEnd - viewportDuration);
  const requestedTime =
    selectionRequest?.timeSeconds ??
    selectedEegTime ??
    ((firstAlert?.startSeconds ?? browseStart) +
      (firstAlert?.endSeconds ?? browseStart)) /
      2;
  const requestId = selectionRequest?.requestId ?? 0;
  const requestedStart = clamp(
    requestedTime - viewportDuration / 2,
    browseStart,
    maxStart,
  );
  const requestInsideRetainedRange = ENABLE_FULL_SIGNAL_PREVIEW
    ? requestedTime <= recordingDurationSeconds
    : retainedRanges.some(
        ([start, end]) => requestedTime >= start && requestedTime <= end,
      );
  const initialStart = clamp(
    (firstAlert?.startSeconds ?? browseStart) - viewportDuration / 2,
    browseStart,
    maxStart,
  );
  const [previewState, setPreviewState] = useState<{
    requestId: number;
    preview: SignalPreview | null;
    error: string | null;
  } | null>(null);
  const preview = previewState?.preview ?? null;
  const selectedInsidePreview = preview?.segments.some(
    (segment) =>
      requestedTime >= segment.sourceStartSeconds &&
      requestedTime <= segment.sourceEndSeconds,
  );
  const requestError =
    previewState?.requestId === requestId ? previewState.error : null;
  const loading =
    ENABLE_SIGNAL_PREVIEW &&
    (ENABLE_FULL_SIGNAL_PREVIEW || Boolean(firstAlert)) &&
    requestInsideRetainedRange &&
    !selectedInsidePreview &&
    previewState?.requestId !== requestId;
  const unavailable = !requestInsideRetainedRange
    ? "No EEG signal is retained at this time."
    : requestError;

  useEffect(() => {
    if (
      !ENABLE_SIGNAL_PREVIEW ||
      (!ENABLE_FULL_SIGNAL_PREVIEW && !firstAlert) ||
      !requestInsideRetainedRange ||
      selectedInsidePreview ||
      previewState?.requestId === requestId
    )
      return;
    const controller = new AbortController();
    void getSignalPreview(
      recordId,
      requestedStart,
      viewportDuration,
      VIEWPORT_POINTS,
      controller.signal,
    )
      .then((nextPreview) => {
        if (!controller.signal.aborted)
          setPreviewState({
            requestId,
            preview: nextPreview,
            error: null,
          });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setPreviewState({
          requestId,
          preview: null,
          error:
            error instanceof Error
              ? error.message
              : "The retained EEG view is unavailable.",
        });
      });
    return () => controller.abort();
  }, [
    firstAlert,
    previewState?.requestId,
    recordId,
    requestId,
    requestInsideRetainedRange,
    requestedStart,
    selectedInsidePreview,
    viewportDuration,
  ]);

  if (!firstAlert)
    return (
      <div
        className={embedded ? "px-4 py-4 sm:px-6" : "panel px-5 py-5 sm:px-7"}
      >
        <h3 className="text-sm font-semibold text-ink">EEG waveform</h3>
        <p className="mt-2 text-sm text-ink-muted">
          No EEG waveform is retained for this recording.
        </p>
      </div>
    );
  if (!ENABLE_SIGNAL_PREVIEW)
    return (
      <SignalNotice embedded={embedded}>
        EEG waveform preview is disabled.
      </SignalNotice>
    );

  const moveTo = (nextStart: number) => {
    const bounded = clamp(nextStart, browseStart, maxStart);
    onEegTimeSelect?.(Math.min(browseEnd, bounded + viewportDuration / 2));
  };
  const viewingStart = requestedStart;
  const currentEnd = Math.min(browseEnd, viewingStart + viewportDuration);
  return (
    <section
      className={embedded ? "min-w-0 overflow-hidden" : "panel overflow-hidden"}
      aria-labelledby="signal-heading"
    >
      <SignalHeader preview={preview} />

      <div className="flex min-h-10 flex-wrap items-center justify-between gap-3 border-b border-rule bg-surface-soft px-4 py-1.5 sm:px-6">
        <p className="font-mono text-xs tabular-nums text-ink-muted">
          {formatTime(viewingStart)}–{formatTime(currentEnd)}
        </p>
        <div className="flex shrink-0 gap-1.5">
          <select
            aria-label="EEG trace gain"
            className="h-8 rounded-lg border border-rule-strong bg-surface px-2 text-xs font-medium text-ink"
            value={traceGain}
            onChange={(event) =>
              setTraceGain(Number(event.currentTarget.value))
            }
          >
            <option value={0.25}>0.25×</option>
            <option value={0.5}>0.5×</option>
            <option value={1}>1×</option>
            <option value={2}>2×</option>
          </select>
          <select
            aria-label="EEG time window"
            className="h-8 rounded-lg border border-rule-strong bg-surface px-2 text-xs font-medium text-ink"
            value={viewportSeconds}
            onChange={(event) => {
              setViewportSeconds(Number(event.currentTarget.value));
              setPreviewState(null);
            }}
          >
            {VIEWPORT_OPTIONS.map((seconds) => (
              <option key={seconds} value={seconds}>
                {seconds} s
              </option>
            ))}
          </select>
          <Button
            variant="outline"
            size="sm"
            className="h-8 border-rule-strong bg-surface px-2.5"
            disabled={viewingStart <= browseStart || loading}
            onClick={() => moveTo(viewingStart - viewportDuration)}
            aria-label="Previous EEG window"
          >
            <Icon name="back" className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 border-rule-strong bg-surface px-2.5"
            disabled={viewingStart >= maxStart || loading}
            onClick={() => moveTo(viewingStart + viewportDuration)}
            aria-label="Next EEG window"
          >
            <Icon name="arrow" className="size-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="h-8 px-2.5"
            disabled={loading}
            onClick={() => moveTo(initialStart)}
          >
            First
          </Button>
        </div>
      </div>

      <div className="px-2 pb-2 pt-1.5 sm:px-3">
        {loading ? (
          <div
            className="grid h-[44rem] place-items-center bg-[#fffef6]"
            role="status"
            aria-label="Loading EEG review window"
          >
            <span className="inline-flex items-center gap-2 text-sm text-ink-muted">
              <Icon name="spinner" className="size-4 animate-spin" />
              Loading EEG window…
            </span>
          </div>
        ) : unavailable ? (
          <div
            className="rounded-lg border border-amber/30 bg-amber-soft px-4 py-4 text-sm text-amber"
            role="status"
          >
            {unavailable}
          </div>
        ) : preview ? (
          <SignalCanvas
            preview={preview}
            traceGain={traceGain}
            selectedEegTime={selectedEegTime ?? null}
            onEegTimeSelect={onEegTimeSelect}
          />
        ) : null}
      </div>
    </section>
  );
}

function SignalHeader({ preview }: { preview: SignalPreview | null }) {
  return (
    <div className="flex min-h-10 items-center justify-between border-b border-rule px-4 py-2 sm:px-6">
      <h2 id="signal-heading" className="text-sm font-bold tracking-[-0.01em]">
        EEG Viewer
      </h2>
      <span className="text-xs font-medium text-ink-muted">
        {preview?.channels.length ?? 18} channels
        {preview?.displayFilter ? ` · ${preview.displayFilter}` : ""}
      </span>
    </div>
  );
}

function SignalNotice({
  children,
  embedded,
}: {
  children: string;
  embedded: boolean;
}) {
  return (
    <section
      className={
        embedded
          ? "px-4 py-5 sm:px-6"
          : "rounded-lg border border-rule bg-surface-soft px-5 py-5 sm:px-7"
      }
      aria-label="Signal preview notice"
    >
      <div className="flex items-start gap-3">
        <Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" />
        <p className="text-sm leading-6 text-ink-muted">{children}</p>
      </div>
    </section>
  );
}

function SignalCanvas({
  preview,
  traceGain,
  selectedEegTime,
  onEegTimeSelect,
}: {
  preview: SignalPreview;
  traceGain: number;
  selectedEegTime: number | null;
  onEegTimeSelect?: (seconds: number) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (
      !canvas ||
      preview.channels.length === 0 ||
      preview.timeSeconds.length === 0
    )
      return;
    const parent = canvas.parentElement;
    if (!parent) return;
    const draw = () => {
      const width = Math.max(320, parent.clientWidth);
      const height = Math.max(
        700,
        preview.channels.length * CHANNEL_ROW_HEIGHT + 60,
      );
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      canvas.style.height = `${height}px`;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, width, height);
      context.fillStyle = "#fffef6";
      context.fillRect(0, 0, width, height);
      const left = PLOT_LEFT;
      const right = width - PLOT_RIGHT;
      const top = 34;
      const bottom = height - 18;
      const channelByLabel = new Map(
        preview.channels.map((channel) => [
          channel.label.toUpperCase(),
          channel,
        ]),
      );
      const displayChannels = CHANNEL_DISPLAY_ORDER.map((label) =>
        channelByLabel.get(label),
      ).filter((channel) => channel !== undefined);
      const orderedLabels = new Set(
        displayChannels.map((channel) => channel.label.toUpperCase()),
      );
      const channels = [
        ...displayChannels,
        ...preview.channels.filter(
          (channel) => !orderedLabels.has(channel.label.toUpperCase()),
        ),
      ];
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
      const channelIndices = channels.map((channel) => {
        const channelTimes = channel.timeSeconds ?? times;
        return channel.samples
          .map((_sample, index) => index)
          .filter((index) => Number.isFinite(channelTimes[index]));
      });
      const channelStats = channels.map((channel, channelIndex) => {
        const indices = channelIndices[channelIndex];
        const mean =
          indices.reduce((sum, index) => sum + channel.samples[index], 0) /
          Math.max(1, indices.length);
        const variance =
          indices.reduce(
            (sum, index) => sum + (channel.samples[index] - mean) ** 2,
            0,
          ) / Math.max(1, indices.length);
        return { mean, standardDeviation: Math.sqrt(variance) };
      });
      const rowHeight = (bottom - top) / channels.length;
      const minTime = times[orderedIndices[0]];
      const maxTime =
        times[orderedIndices.at(-1) ?? orderedIndices[0]] || minTime + 1;
      const timeRange = Math.max(1, maxTime - minTime);
      const xFor = (time: number) =>
        left + ((time - minTime) / timeRange) * (right - left);

      channels.forEach((channel, channelIndex) => {
        const center = top + rowHeight * channelIndex + rowHeight / 2;
        context.fillStyle = "#fffef6";
        context.fillRect(
          left,
          top + rowHeight * channelIndex,
          right - left,
          rowHeight,
        );
        context.fillStyle = "#596271";
        context.font = "11px SFMono-Regular, Consolas, monospace";
        context.textBaseline = "middle";
        context.fillText(channel.label, 10, center);
      });

      preview.flaggedIntervals.forEach((interval) => {
        const start = Math.max(minTime, interval.startSeconds);
        const end = Math.min(maxTime, interval.endSeconds);
        if (end <= start) return;
        context.fillStyle = "rgba(208, 152, 49, 0.14)";
        context.fillRect(
          xFor(start),
          top,
          Math.max(3, xFor(end) - xFor(start)),
          bottom - top,
        );
      });

      const gridTimes = new Set([minTime, maxTime]);
      for (let time = Math.ceil(minTime / 2) * 2; time <= maxTime; time += 2) {
        gridTimes.add(time);
      }
      gridTimes.forEach((time) => {
        const x = xFor(time);
        const major = Math.round(time / 10) * 10 === time;
        context.strokeStyle = major ? "#d5cfbb" : "#eeeada";
        context.lineWidth = 1;
        context.beginPath();
        context.moveTo(x, top);
        context.lineTo(x, bottom);
        context.stroke();
      });
      channels.forEach((_, channelIndex) => {
        const rowTop = top + rowHeight * channelIndex;
        for (let division = 0; division <= 2; division += 1) {
          const y = rowTop + (rowHeight * division) / 2;
          context.strokeStyle =
            division === 0 || division === 2 ? "#d5cfbb" : "#eeeada";
          context.lineWidth = 1;
          context.beginPath();
          context.moveTo(left, y);
          context.lineTo(right, y);
          context.stroke();
        }
      });

      channels.forEach((channel, channelIndex) => {
        const center = top + rowHeight * channelIndex + rowHeight / 2;
        const channelTimes = channel.timeSeconds ?? times;
        const channelIndices = orderedIndices.filter(
          (index) => index < channel.samples.length,
        );
        const plottedIndices = channel.timeSeconds
          ? channel.samples.map((_sample, index) => index)
          : channelIndices;
        const { mean } = channelStats[channelIndex];
        const group = Math.floor(Math.min(channelIndex, 17) / 4);
        context.strokeStyle =
          group === 0 || group === 2
            ? "#bd2929"
            : group === 1 || group === 3
              ? "#214f9a"
              : "#343a40";
        context.lineWidth = 0.9;
        context.beginPath();
        plottedIndices.forEach((index, pointIndex) => {
          const sample = channel.samples[index];
          const time = channelTimes[index];
          const segmentIndex = preview.segments.findIndex(
            (segment) =>
              time >= segment.sourceStartSeconds &&
              time <= segment.sourceEndSeconds,
          );
          const normalized = Math.max(
            -3,
            Math.min(
              3,
              (sample - mean) /
                Math.max(0.0001, channelStats[channelIndex].standardDeviation),
            ),
          );
          const x = xFor(time);
          const y = center - normalized * (rowHeight / 16) * traceGain;
          if (
            pointIndex === 0 ||
            segmentIndex !==
              preview.segments.findIndex(
                (segment) =>
                  channelTimes[plottedIndices[pointIndex - 1]] >=
                    segment.sourceStartSeconds &&
                  channelTimes[plottedIndices[pointIndex - 1]] <=
                    segment.sourceEndSeconds,
              )
          )
            context.moveTo(x, y);
          else context.lineTo(x, y);
        });
        context.stroke();
      });

      if (
        selectedEegTime !== null &&
        selectedEegTime >= minTime &&
        selectedEegTime <= maxTime
      ) {
        const playheadX = xFor(selectedEegTime);
        context.save();
        context.strokeStyle = "#383b3f";
        context.lineWidth = 1.25;
        context.setLineDash([3, 3]);
        context.beginPath();
        context.moveTo(playheadX, top);
        context.lineTo(playheadX, bottom);
        context.stroke();
        context.restore();
      }

      context.fillStyle = "#4e4b42";
      context.font = "11px SFMono-Regular, Consolas, monospace";
      context.textBaseline = "top";
      const labelTimes = [minTime];
      for (
        let time = Math.ceil((minTime + 0.001) / 10) * 10;
        time < maxTime;
        time += 10
      ) {
        labelTimes.push(time);
      }
      if (maxTime > minTime) labelTimes.push(maxTime);
      const finalLabelLeft =
        right - context.measureText(formatTime(maxTime)).width;
      let previousLabelRight = left - 8;
      labelTimes.forEach((time, index) => {
        const x = xFor(time);
        const label = formatTime(time);
        const labelWidth = context.measureText(label).width;
        const isFirst = index === 0;
        const isLast = index === labelTimes.length - 1;
        const labelLeft = isFirst
          ? x
          : isLast
            ? x - labelWidth
            : x - labelWidth / 2;
        const labelRight = labelLeft + labelWidth;
        if (
          !isFirst &&
          !isLast &&
          (labelLeft < previousLabelRight + 8 ||
            labelRight > finalLabelLeft - 8)
        )
          return;
        context.textAlign = isFirst ? "left" : isLast ? "right" : "center";
        context.fillText(label, x, 8);
        previousLabelRight = labelRight;
      });
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(parent);
    return () => observer.disconnect();
  }, [preview, selectedEegTime, traceGain]);

  return (
    <div>
      <canvas
        ref={canvasRef}
        className="block w-full cursor-crosshair border border-[#d5cfbb] focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal"
        role="slider"
        tabIndex={0}
        aria-valuemin={preview.timeSeconds[0] ?? 0}
        aria-valuemax={preview.timeSeconds.at(-1) ?? 0}
        aria-valuenow={selectedEegTime ?? preview.timeSeconds[0] ?? 0}
        aria-valuetext={`EEG time ${formatTime(selectedEegTime ?? preview.timeSeconds[0] ?? 0)}`}
        aria-label={`${preview.channels.length}-channel EEG waveform; use arrow keys or click to select time`}
        onClick={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          const fraction = clamp(
            (event.clientX - bounds.left - PLOT_LEFT) /
              Math.max(1, bounds.width - PLOT_LEFT - PLOT_RIGHT),
            0,
            1,
          );
          const start = preview.timeSeconds[0] ?? 0;
          const end = preview.timeSeconds.at(-1) ?? start;
          onEegTimeSelect?.(start + fraction * (end - start));
        }}
        onKeyDown={(event) => {
          if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
          event.preventDefault();
          const start = preview.timeSeconds[0] ?? 0;
          const end = preview.timeSeconds.at(-1) ?? start;
          onEegTimeSelect?.(
            clamp(
              (selectedEegTime ?? start) +
                (event.key === "ArrowRight" ? 1 : -1),
              start,
              end,
            ),
          );
        }}
      />
    </div>
  );
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

/** Match backend retention: keep up to ten minutes before every alert window. */
function mergeRetainedRanges(
  alertWindows: PredictionWindow[],
  recordingDurationSeconds: number,
): Array<[number, number]> {
  const ranges = alertWindows
    .map(
      (window) =>
        [
          Math.max(0, window.startSeconds - CONTEXT_BEFORE_SECONDS),
          Math.min(recordingDurationSeconds, window.endSeconds),
        ] as [number, number],
    )
    .filter(([start, end]) => end > start)
    .sort(([left], [right]) => left - right);
  const merged: Array<[number, number]> = [];
  for (const [start, end] of ranges) {
    const previous = merged.at(-1);
    if (previous && start <= previous[1])
      previous[1] = Math.max(previous[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const remaining = whole % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`
    : `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}
