"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ENABLE_SIGNAL_PREVIEW, getSignalPreview } from "@/lib/api";
import type { PredictionWindow, SignalPreview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import {
  channelGroupLabel,
  clinicalMontageChannelCount,
  deriveClinicalLongitudinalMontage,
  displaySignalValue,
  hasRecordedLongitudinalBipolarMontage,
  orderSignalChannels,
  type SignalChannelGroup,
} from "./signal-rendering";

const VIEWPORT_SECONDS = 12;
const VIEWPORT_POINTS = 10_000;
const PLOT_LEFT = 24;
const PLOT_RIGHT = 12;
const PLOT_TOP = 26;
const PLOT_BOTTOM = 12;
const EDGE_BUFFER_MILLIMETERS = 20;
const CHANNEL_ROW_MILLIMETERS = 15;
const LABEL_GUTTER_WIDTH = 120;
const DEFAULT_PIXELS_PER_MM = 3;
const SENSITIVITY_UV_PER_MM = 10;
const RELATIVE_UNITS_PER_5_MM = 1;
const PAPER_SPEED_MM_PER_SECOND = 30;

export type SignalSeekRequest = {
  timeSeconds: number;
  requestId: number;
};

export type SignalPageMetadata = {
  recordingDurationSeconds: number;
  pageStartSeconds: number;
  pageEndSeconds: number;
  availableSegments: SignalPreview["segments"];
};

/** Fetch and render only the visible retained EEG page. */
export function SignalViewer({
  recordId,
  predictionWindows,
  recordingDurationSeconds,
  selectedEegTime = null,
  selectionRequest = null,
  onEegTimeSelect,
  onSignalPageMetadata,
  embedded = false,
}: {
  recordId: string;
  predictionWindows: PredictionWindow[];
  recordingDurationSeconds: number;
  selectedEegTime?: number | null;
  selectionRequest?: SignalSeekRequest | null;
  onEegTimeSelect?: (seconds: number) => void;
  onSignalPageMetadata?: (metadata: SignalPageMetadata) => void;
  embedded?: boolean;
}) {
  const alertWindows = useMemo(
    () => predictionWindows.filter((window) => window.seizureDetected),
    [predictionWindows],
  );
  const firstAlert = alertWindows[0];
  const browseStart = 0;
  const browseEnd = Math.max(0, recordingDurationSeconds);
  const browseDuration = Math.max(0.001, browseEnd - browseStart);
  const viewportDuration = Math.min(VIEWPORT_SECONDS, browseDuration);
  const maxStart = Math.max(browseStart, browseEnd - viewportDuration);
  const requestedTime = clamp(
    selectedEegTime ??
      selectionRequest?.timeSeconds ??
      (firstAlert
        ? (firstAlert.startSeconds + firstAlert.endSeconds) / 2
        : browseStart),
    browseStart,
    browseEnd,
  );
  const requestedStart = clamp(
    Math.floor(requestedTime / viewportDuration) * viewportDuration,
    browseStart,
    maxStart,
  );
  const requestedEnd = Math.min(browseEnd, requestedStart + viewportDuration);
  // The owner-scoped API decides whether an older page is still retained.
  const requestablePage = requestedEnd > requestedStart;
  const pageKey = `${recordId}:${requestedStart.toFixed(6)}:${viewportDuration.toFixed(6)}`;
  const [previewState, setPreviewState] = useState<{
    pageKey: string;
    preview: SignalPreview | null;
    error: string | null;
  } | null>(null);
  const pageStateIsCurrent = previewState?.pageKey === pageKey;
  const preview = pageStateIsCurrent ? previewState.preview : null;
  const clinicalMontage = useMemo(
    () =>
      preview
        ? deriveClinicalLongitudinalMontage(
            preview.channels,
            preview.samplingRate,
            preview.timeSeconds,
          )
        : null,
    [preview],
  );
  const availableMontageChannels = clinicalMontageChannelCount(
    clinicalMontage ?? [],
  );
  const recordedBipolarMontage = useMemo(
    () =>
      preview ? hasRecordedLongitudinalBipolarMontage(preview.channels) : false,
    [preview],
  );
  const displayedChannels = useMemo(() => {
    if (!preview) return [];
    if (availableMontageChannels > 0 && clinicalMontage) return clinicalMontage;
    return orderSignalChannels(preview.channels)
      .filter(({ group }) => group !== "other")
      .map(({ channel }) => channel);
  }, [availableMontageChannels, clinicalMontage, preview]);
  const montageLabel =
    availableMontageChannels === 18
      ? recordedBipolarMontage
        ? "longitudinal bipolar · as recorded"
        : "longitudinal bipolar · derived from source electrodes"
      : availableMontageChannels > 0
        ? `incomplete bipolar montage · ${availableMontageChannels}/18 derivations`
        : "as-recorded source channels · bipolar montage unavailable";
  const previewForCanvas = useMemo(
    () => (preview ? { ...preview, channels: displayedChannels } : null),
    [displayedChannels, preview],
  );
  const requestError = pageStateIsCurrent ? previewState.error : null;
  const relativeUnits = isRelativeRepresentation(preview?.representation);
  const loading =
    ENABLE_SIGNAL_PREVIEW && requestablePage && !pageStateIsCurrent;
  const unavailable = !ENABLE_SIGNAL_PREVIEW
    ? "EEG waveform preview is disabled."
    : !requestablePage
      ? "No EEG signal is retained in this time window."
      : requestError;
  const metadataCallbackRef = useRef(onSignalPageMetadata);

  useEffect(() => {
    metadataCallbackRef.current = onSignalPageMetadata;
  }, [onSignalPageMetadata]);

  useEffect(() => {
    if (!ENABLE_SIGNAL_PREVIEW || !requestablePage || pageStateIsCurrent)
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
            pageKey,
            preview: nextPreview,
            error: null,
          });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setPreviewState({
          pageKey,
          preview: null,
          error:
            error instanceof Error
              ? error.message
              : "The retained EEG view is unavailable.",
        });
      });
    return () => controller.abort();
  }, [
    pageKey,
    requestablePage,
    pageStateIsCurrent,
    recordId,
    requestedStart,
    viewportDuration,
  ]);

  useEffect(() => {
    metadataCallbackRef.current?.({
      recordingDurationSeconds: Math.max(0, recordingDurationSeconds),
      pageStartSeconds: requestedStart,
      pageEndSeconds: requestedEnd,
      availableSegments: preview?.segments ?? [],
    });
  }, [preview, recordingDurationSeconds, requestedEnd, requestedStart]);

  const moveTo = (nextStart: number) => {
    const bounded = clamp(nextStart, browseStart, maxStart);
    onEegTimeSelect?.(Math.min(browseEnd, bounded + viewportDuration / 2));
  };
  const currentTime =
    selectedEegTime ?? selectionRequest?.timeSeconds ?? requestedTime;
  const cursorOnSignal =
    currentTime === null ||
    preview?.segments.some(
      (segment) =>
        currentTime >= segment.sourceStartSeconds &&
        currentTime < segment.sourceEndSeconds,
    ) === true;

  return (
    <section
      className={embedded ? "min-w-0 overflow-hidden" : "panel overflow-hidden"}
      aria-labelledby="signal-heading"
    >
      <SignalHeader
        preview={preview}
        channelCount={displayedChannels.length}
        montageLabel={montageLabel}
      />

      <div className="flex min-h-10 flex-wrap items-center justify-between gap-3 border-b border-rule bg-surface-soft px-4 py-1.5 sm:px-6">
        <p className="font-mono text-xs tabular-nums text-ink-muted">
          {formatTime(requestedStart)}–{formatTime(requestedEnd)}
        </p>
        <div
          data-testid="eeg-viewer-controls"
          className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-2"
        >
          <span className="hidden text-[11px] tabular-nums text-ink-muted sm:inline">
            100 µV/cm · 30 mm/s ·{" "}
            {preview?.displayFilter ?? "filter unavailable"}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-8 border-rule-strong bg-surface px-2.5"
            disabled={requestedStart <= browseStart || loading}
            onClick={() => moveTo(requestedStart - viewportDuration)}
            aria-label="Previous EEG page"
          >
            <Icon name="back" className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 border-rule-strong bg-surface px-2.5"
            disabled={requestedStart >= maxStart || loading}
            onClick={() => moveTo(requestedStart + viewportDuration)}
            aria-label="Next EEG page"
          >
            <Icon name="arrow" className="size-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="h-8 px-2.5"
            disabled={loading || requestedStart <= browseStart}
            onClick={() => moveTo(browseStart)}
          >
            First page
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
              Loading EEG page…
            </span>
          </div>
        ) : unavailable ? (
          <div
            className="rounded-lg border border-amber/30 bg-amber-soft px-4 py-4 text-sm text-amber"
            role="status"
          >
            {unavailable}
          </div>
        ) : preview && previewForCanvas ? (
          preview.channels.length === 0 ? (
            <div
              className="rounded-lg border border-amber/30 bg-amber-soft px-4 py-4 text-sm text-amber"
              role="status"
            >
              No EEG samples were acquired in this 12-second interval. The
              recording timeline is preserved, and synchronized video may still
              be available if a verified clip covers this time.
            </div>
          ) : (
            <>
              <SignalCanvas
                preview={previewForCanvas}
                pageStartSeconds={requestedStart}
                pageEndSeconds={requestedEnd}
                sensitivity={
                  relativeUnits
                    ? RELATIVE_UNITS_PER_5_MM
                    : SENSITIVITY_UV_PER_MM
                }
                relativeUnits={relativeUnits}
                paperSpeedMmPerSecond={PAPER_SPEED_MM_PER_SECOND}
                selectedEegTime={currentTime}
                flaggedIntervals={alertWindows}
                onEegTimeSelect={onEegTimeSelect}
              />
              {!cursorOnSignal && (
                <p className="mt-2 text-xs text-amber" role="status">
                  The selected time is in an acquisition gap; no EEG samples are
                  available at the cursor.
                </p>
              )}
            </>
          )
        ) : null}
      </div>
    </section>
  );
}

function SignalHeader({
  preview,
  channelCount,
  montageLabel,
}: {
  preview: SignalPreview | null;
  channelCount: number;
  montageLabel: string;
}) {
  return (
    <div className="flex min-h-10 flex-wrap items-center justify-between gap-2 border-b border-rule px-4 py-2 sm:px-6">
      <div>
        <h2
          id="signal-heading"
          className="text-sm font-bold tracking-[-0.01em]"
        >
          EEG waveform · {montageLabel}
        </h2>
        <p className="mt-0.5 text-[11px] text-ink-muted">
          R red · L blue · midline black · auxiliary channels keep distinct
          colors · amber shading = model flags
        </p>
      </div>
      <span className="text-xs font-medium text-ink-muted">
        {preview ? `${channelCount} channels` : "Channels from recording"}
        {preview?.samplingRate ? ` · ${preview.samplingRate} Hz` : ""}
      </span>
    </div>
  );
}

function SignalCanvas({
  preview,
  pageStartSeconds,
  pageEndSeconds,
  sensitivity,
  relativeUnits,
  paperSpeedMmPerSecond,
  selectedEegTime,
  flaggedIntervals,
  onEegTimeSelect,
}: {
  preview: SignalPreview;
  pageStartSeconds: number;
  pageEndSeconds: number;
  sensitivity: number;
  relativeUnits: boolean;
  paperSpeedMmPerSecond: number;
  selectedEegTime: number | null;
  flaggedIntervals: PredictionWindow[];
  onEegTimeSelect?: (seconds: number) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const plotViewportRef = useRef<HTMLDivElement>(null);
  const [availablePlotWidth, setAvailablePlotWidth] = useState(0);
  const channels = useMemo(
    () => orderSignalChannels(preview.channels),
    [preview.channels],
  );
  const pageDuration = Math.max(0.001, pageEndSeconds - pageStartSeconds);
  const pixelsPerMm =
    availablePlotWidth > 0
      ? Math.max(
          0.25,
          (availablePlotWidth - PLOT_LEFT - PLOT_RIGHT) /
            (VIEWPORT_SECONDS * PAPER_SPEED_MM_PER_SECOND),
        )
      : DEFAULT_PIXELS_PER_MM;
  const channelRowHeight = CHANNEL_ROW_MILLIMETERS * pixelsPerMm;
  const edgeBuffer = EDGE_BUFFER_MILLIMETERS * pixelsPerMm;
  const traceWidthMm = pageDuration * paperSpeedMmPerSecond;
  const traceWidth = traceWidthMm * pixelsPerMm;
  const canvasWidth = PLOT_LEFT + traceWidth + PLOT_RIGHT;
  const canvasHeight =
    PLOT_TOP +
    edgeBuffer +
    channels.length * channelRowHeight +
    edgeBuffer +
    PLOT_BOTTOM;
  const selectedTimeIsVisible =
    selectedEegTime !== null &&
    selectedEegTime >= pageStartSeconds &&
    selectedEegTime <= pageEndSeconds;
  const cursorFraction = selectedTimeIsVisible
    ? clamp((selectedEegTime - pageStartSeconds) / pageDuration, 0, 1)
    : null;
  const playheadLeft =
    cursorFraction === null ? null : PLOT_LEFT + cursorFraction * traceWidth;

  useEffect(() => {
    const viewport = plotViewportRef.current;
    if (!viewport) return;
    const measure = () => {
      const width = viewport.clientWidth;
      setAvailablePlotWidth((previous) =>
        previous === width ? previous : width,
      );
    };
    const observer = new ResizeObserver(measure);
    observer.observe(viewport);
    measure();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || channels.length === 0) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(canvasWidth * ratio);
    canvas.height = Math.round(canvasHeight * ratio);
    canvas.style.width = `${canvasWidth}px`;
    canvas.style.height = `${canvasHeight}px`;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, canvasWidth, canvasHeight);
    context.fillStyle = "#fffef6";
    context.fillRect(0, 0, canvasWidth, canvasHeight);

    const plotRight = canvasWidth - PLOT_RIGHT;
    const plotBottom = canvasHeight - PLOT_BOTTOM;
    const xFor = (time: number) =>
      PLOT_LEFT +
      (time - pageStartSeconds) * paperSpeedMmPerSecond * pixelsPerMm;

    flaggedIntervals.forEach((interval) => {
      const start = Math.max(pageStartSeconds, interval.startSeconds);
      const end = Math.min(pageEndSeconds, interval.endSeconds);
      if (end <= start) return;
      context.fillStyle = "rgba(208, 152, 49, 0.13)";
      context.fillRect(
        xFor(start),
        PLOT_TOP,
        Math.max(1, xFor(end) - xFor(start)),
        plotBottom - PLOT_TOP,
      );
    });

    const verticalMillimeters = Math.ceil(traceWidthMm);
    for (
      let millimeter = 0;
      millimeter <= verticalMillimeters;
      millimeter += 1
    ) {
      const x = PLOT_LEFT + millimeter * pixelsPerMm;
      if (x > plotRight) break;
      const major = millimeter % 30 === 0;
      const medium = millimeter % 5 === 0;
      context.strokeStyle = major ? "#bdb39a" : medium ? "#ddd5c1" : "#f0ecdf";
      context.lineWidth = major ? 1.2 : 1;
      context.beginPath();
      context.moveTo(x, PLOT_TOP);
      context.lineTo(x, plotBottom);
      context.stroke();
    }

    const horizontalMillimeters = Math.floor(
      (plotBottom - PLOT_TOP) / pixelsPerMm,
    );
    for (
      let millimeter = 0;
      millimeter <= horizontalMillimeters;
      millimeter += 1
    ) {
      const y = PLOT_TOP + millimeter * pixelsPerMm;
      const major = millimeter % 5 === 0;
      context.strokeStyle = major ? "#ddd5c1" : "#f0ecdf";
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(PLOT_LEFT, y);
      context.lineTo(plotRight, y);
      context.stroke();
    }

    context.fillStyle = "#4e4b42";
    context.font = "10px SFMono-Regular, Consolas, monospace";
    context.textBaseline = "top";
    const fullSeconds = Math.floor(pageDuration);
    const labelStep = Math.max(
      2,
      Math.ceil(52 / (paperSpeedMmPerSecond * pixelsPerMm)),
    );
    for (let second = 0; second <= fullSeconds; second += labelStep) {
      const time = pageStartSeconds + second;
      const x = xFor(time);
      context.textAlign =
        second === 0 ? "left" : second === fullSeconds ? "right" : "center";
      context.fillText(formatTime(time), x, 7);
    }
    if (fullSeconds % labelStep !== 0 || pageDuration > fullSeconds + 0.01) {
      context.textAlign = "right";
      context.fillText(formatTime(pageEndSeconds), plotRight, 7);
    }

    const pixelsPerUnit = relativeUnits
      ? (5 * pixelsPerMm) / Math.max(0.000001, sensitivity)
      : pixelsPerMm / Math.max(0.000001, sensitivity);
    let visibleSamples = 0;
    let clippedSamples = 0;
    let minimumTraceY = Number.POSITIVE_INFINITY;
    let maximumTraceY = Number.NEGATIVE_INFINITY;
    channels.forEach(({ channel, group }, channelIndex) => {
      const channelTimes = channel.timeSeconds ?? preview.timeSeconds;
      const rowTop = PLOT_TOP + edgeBuffer + channelRowHeight * channelIndex;
      const center = rowTop + channelRowHeight / 2;
      let segmentIndex = 0;
      let priorSegment = -1;
      let clipped = false;
      let drewTrace = false;
      context.save();
      context.beginPath();
      context.rect(
        PLOT_LEFT,
        PLOT_TOP,
        plotRight - PLOT_LEFT,
        plotBottom - PLOT_TOP,
      );
      context.clip();
      context.strokeStyle = channelColor(group, channel.label);
      context.lineWidth = 1;
      context.beginPath();

      for (let index = 0; index < channel.samples.length; index += 1) {
        const time = channelTimes[index];
        const sample = channel.samples[index];
        if (!Number.isFinite(time) || !Number.isFinite(sample)) continue;
        if (time < pageStartSeconds || time > pageEndSeconds) continue;
        while (
          segmentIndex < preview.segments.length &&
          time >= preview.segments[segmentIndex].sourceEndSeconds
        ) {
          segmentIndex += 1;
        }
        const segment = preview.segments[segmentIndex];
        if (
          !segment ||
          time < segment.sourceStartSeconds ||
          time >= segment.sourceEndSeconds
        ) {
          priorSegment = -1;
          continue;
        }

        const value = displaySignalValue(sample, preview.representation);
        const y = center - value * pixelsPerUnit;
        minimumTraceY = Math.min(minimumTraceY, y);
        maximumTraceY = Math.max(maximumTraceY, y);
        visibleSamples += 1;
        if (y < PLOT_TOP || y > plotBottom) {
          clipped = true;
          clippedSamples += 1;
        }
        const x = xFor(time);
        if (priorSegment !== segmentIndex) context.moveTo(x, y);
        else context.lineTo(x, y);
        priorSegment = segmentIndex;
        drewTrace = true;
      }
      if (drewTrace) context.stroke();
      context.restore();

      if (clipped) {
        context.fillStyle = "#b42318";
        context.font = "bold 11px SFMono-Regular, Consolas, monospace";
        context.textAlign = "right";
        context.textBaseline = "middle";
        context.fillText("!", PLOT_LEFT - 8, center);
      }
    });
    canvas.dataset.visibleSamples = String(visibleSamples);
    canvas.dataset.clippedSamples = String(clippedSamples);
    canvas.dataset.clippedPercent = visibleSamples
      ? ((100 * clippedSamples) / visibleSamples).toFixed(4)
      : "0";
    canvas.dataset.minimumTraceY = Number.isFinite(minimumTraceY)
      ? minimumTraceY.toFixed(2)
      : "";
    canvas.dataset.maximumTraceY = Number.isFinite(maximumTraceY)
      ? maximumTraceY.toFixed(2)
      : "";
  }, [
    canvasHeight,
    canvasWidth,
    channelRowHeight,
    channels,
    edgeBuffer,
    flaggedIntervals,
    pageDuration,
    pageEndSeconds,
    pageStartSeconds,
    paperSpeedMmPerSecond,
    pixelsPerMm,
    preview,
    relativeUnits,
    sensitivity,
    traceWidth,
    traceWidthMm,
  ]);

  return (
    <>
      <div className="flex max-w-full overflow-hidden rounded border border-[#d5cfbb] bg-[#fffef6]">
        <div
          className="shrink-0 border-r border-[#d5cfbb] bg-[#fffef6]"
          style={{ width: LABEL_GUTTER_WIDTH }}
        >
          <div aria-hidden="true" style={{ height: PLOT_TOP }} />
          <div aria-hidden="true" style={{ height: edgeBuffer }} />
          <div role="list" aria-label="EEG channels">
            {channels.map(({ channel, group }, index) => (
              <div
                key={`${channel.label}-${index}`}
                role="listitem"
                title={channel.label}
                className="flex items-center gap-2 overflow-hidden border-t border-[#e6e0d2] px-2 font-mono text-[10px] leading-none"
                style={{ height: channelRowHeight }}
              >
                <span
                  aria-hidden="true"
                  className="w-4 shrink-0 text-center font-bold"
                  style={{ color: channelColor(group, channel.label) }}
                >
                  {channelGroupLabel(group)}
                </span>
                <span className="truncate text-[#303844]">{channel.label}</span>
              </div>
            ))}
          </div>
          <div aria-hidden="true" style={{ height: PLOT_BOTTOM }} />
        </div>
        <div
          ref={plotViewportRef}
          data-testid="eeg-waveform-scrollport"
          className="min-w-0 flex-1 overflow-x-auto"
        >
          <div
            className="relative"
            style={{ width: canvasWidth, height: canvasHeight }}
          >
            <canvas
              ref={canvasRef}
              data-testid="eeg-waveform-canvas"
              data-view-start={pageStartSeconds}
              data-view-end={pageEndSeconds}
              data-sampling-rate={preview.samplingRate}
              data-channel-count={channels.length}
              data-visible-samples="0"
              data-clipped-samples="0"
              data-clipped-percent="0"
              data-minimum-trace-y=""
              data-maximum-trace-y=""
              data-plot-top={PLOT_TOP}
              data-plot-bottom={canvasHeight - PLOT_BOTTOM}
              data-paper-speed-mm-per-second={paperSpeedMmPerSecond}
              data-sensitivity={sensitivity}
              data-pixels-per-mm={pixelsPerMm}
              data-trace-width={traceWidth}
              data-trace-width-mm={traceWidthMm}
              className="block cursor-crosshair focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal"
              role="slider"
              tabIndex={0}
              aria-valuemin={pageStartSeconds}
              aria-valuemax={pageEndSeconds}
              aria-valuenow={
                selectedEegTime ?? preview.timeSeconds[0] ?? pageStartSeconds
              }
              aria-valuetext={`EEG time ${formatTime(selectedEegTime ?? preview.timeSeconds[0] ?? pageStartSeconds)}`}
              aria-label={`${channels.length}-channel EEG waveform; use arrow keys or click to select time. Channels: ${channels.map(({ channel }) => channel.label).join(", ")}`}
              onClick={(event) => {
                const bounds = event.currentTarget.getBoundingClientRect();
                const fraction = clamp(
                  (event.clientX - bounds.left - PLOT_LEFT) /
                    Math.max(1, traceWidth),
                  0,
                  1,
                );
                onEegTimeSelect?.(pageStartSeconds + fraction * pageDuration);
              }}
              onKeyDown={(event) => {
                if (
                  event.key !== "ArrowLeft" &&
                  event.key !== "ArrowRight" &&
                  event.key !== "PageUp" &&
                  event.key !== "PageDown" &&
                  event.key !== "Home" &&
                  event.key !== "End"
                )
                  return;
                event.preventDefault();
                const current = selectedEegTime ?? pageStartSeconds;
                const next =
                  event.key === "Home"
                    ? pageStartSeconds
                    : event.key === "End"
                      ? pageEndSeconds
                      : event.key === "PageUp"
                        ? current - pageDuration
                        : event.key === "PageDown"
                          ? current + pageDuration
                          : current + (event.key === "ArrowRight" ? 1 : -1);
                onEegTimeSelect?.(
                  clamp(next, 0, pageEndSeconds + pageDuration),
                );
              }}
            />
            {playheadLeft !== null && (
              <div
                aria-hidden="true"
                className="pointer-events-none absolute border-l border-dashed border-[#282c32]"
                style={{
                  left: `${playheadLeft}px`,
                  top: PLOT_TOP,
                  bottom: PLOT_BOTTOM,
                }}
              />
            )}
          </div>
        </div>
      </div>
      {relativeUnits && (
        <p className="mt-1 text-[11px] text-amber">
          {preview.representation === "normalized-units"
            ? "Normalized model-input"
            : "Relative review"}{" "}
          values; vertical scale is uncalibrated. Fixed display gain: 1 relative
          unit/5 mm.
        </p>
      )}
    </>
  );
}

function channelColor(group: SignalChannelGroup, label: string): string {
  switch (group) {
    case "left":
      return "#1429b8";
    case "right":
      return "#cc2222";
    case "midline":
      return "#282828";
    case "auxiliary":
      if (/^(?:ECG|EKG)/i.test(label)) return "#24843c";
      if (/EOG.*LEFT/i.test(label)) return "#1429b8";
      if (/EOG.*RIGHT/i.test(label)) return "#cc2222";
      if (/CHIN/i.test(label)) return "#24843c";
      if (/PHOTIC/i.test(label)) return "#cc2222";
      return "#646b73";
    default:
      return "#6b4d96";
  }
}

function isRelativeRepresentation(
  representation: SignalPreview["representation"] | undefined,
): boolean {
  return (
    representation === "signal-obfuscated" ||
    representation === "normalized-units" ||
    representation === "relative-units"
  );
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
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
