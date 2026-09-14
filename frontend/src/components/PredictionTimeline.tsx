"use client";

import { useMemo, useState, type KeyboardEvent } from "react";
import type { PredictionWindow } from "@/lib/types";

const CHART_WIDTH = 920;
const CHART_HEIGHT = 230;
const PADDING = { top: 24, right: 28, bottom: 42, left: 64 };
const MAX_LINE_POINTS = 4000;

type IndexedPrediction = { prediction: PredictionWindow; windowIndex: number };

/** Render the complete prediction timeline with exact, inspectable alert windows. */
export function PredictionTimeline({
  predictions,
  durationSeconds,
  threshold = 0.5,
  scoreType = "development_score",
}: {
  predictions: PredictionWindow[];
  durationSeconds: number;
  threshold?: number;
  scoreType?: string;
}) {
  const [activeAlertIndex, setActiveAlertIndex] = useState(0);
  const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const recordingDuration = Math.max(
    durationSeconds,
    predictions.at(-1)?.endSeconds ?? 1,
    1,
  );
  const linePredictions = useMemo(
    () => linePoints(predictions, MAX_LINE_POINTS),
    [predictions],
  );
  const alertPredictions = useMemo<IndexedPrediction[]>(
    () =>
      predictions.flatMap((prediction, windowIndex) =>
        prediction.seizureDetected ? [{ prediction, windowIndex }] : [],
      ),
    [predictions],
  );
  const alertIndexByWindow = useMemo(
    () =>
      new Map(
        alertPredictions.map((item, alertIndex) => [
          item.windowIndex,
          alertIndex,
        ]),
      ),
    [alertPredictions],
  );
  const hoverPredictions = useMemo<IndexedPrediction[]>(() => {
    const stride = Math.max(1, Math.ceil(predictions.length / 260));
    return predictions.flatMap((prediction, windowIndex) =>
      prediction.seizureDetected ||
      windowIndex % stride === 0 ||
      windowIndex === predictions.length - 1
        ? [{ prediction, windowIndex }]
        : [],
    );
  }, [predictions]);
  const selectedAlertIndex = Math.min(
    activeAlertIndex,
    Math.max(0, alertPredictions.length - 1),
  );
  const selectedAlert = alertPredictions[selectedAlertIndex];
  const calibrated = scoreType === "calibrated_probability";
  const scoreLabel = calibrated ? "Estimated probability" : "Model score";
  const windowLabel = calibrated ? "estimated probability" : "score";
  const x = (seconds: number) =>
    PADDING.left +
    (Math.max(0, Math.min(recordingDuration, seconds)) / recordingDuration) *
      plotWidth;
  const y = (score: number) =>
    PADDING.top + (1 - Math.max(0, Math.min(1, score))) * plotHeight;
  const thresholdY = y(threshold);

  if (predictions.length === 0) {
    return (
      <p className="rounded-md border border-rule bg-surface-soft px-4 py-4 text-sm text-ink-muted">
        No prediction windows were stored for this recording.
      </p>
    );
  }

  const handleAlertNavigation = (event: KeyboardEvent<HTMLDivElement>) => {
    if (alertPredictions.length === 0) return;
    let nextIndex = selectedAlertIndex;
    if (event.key === "ArrowRight" || event.key === "ArrowDown")
      nextIndex = Math.min(alertPredictions.length - 1, selectedAlertIndex + 1);
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp")
      nextIndex = Math.max(0, selectedAlertIndex - 1);
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = alertPredictions.length - 1;
    else return;
    event.preventDefault();
    setActiveAlertIndex(nextIndex);
  };

  return (
    <div aria-label="Prediction score timeline" role="group">
      <div className="overflow-x-auto rounded-lg border border-rule bg-surface-soft p-2 sm:p-3">
        <svg
          className="h-auto min-w-[680px] w-full"
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          role="img"
          aria-labelledby="prediction-chart-title prediction-chart-description"
        >
          <title id="prediction-chart-title">
            {calibrated
              ? "Estimated window probability timeline"
              : "Prediction score timeline"}
          </title>
          <desc id="prediction-chart-description">
            Every scored four-second window across the recording. Highlighted
            windows crossed the configured threshold.
          </desc>
          {[1, 0.5, 0].map((value) => (
            <g key={value}>
              <line
                x1={PADDING.left}
                y1={y(value)}
                x2={CHART_WIDTH - PADDING.right}
                y2={y(value)}
                stroke="currentColor"
                strokeWidth="1"
                className="text-rule"
              />
              <text
                x={PADDING.left - 10}
                y={y(value) + 4}
                textAnchor="end"
                className="fill-ink-muted text-[11px]"
              >
                {value.toFixed(1)}
              </text>
            </g>
          ))}
          <text
            x="14"
            y={PADDING.top + plotHeight / 2}
            textAnchor="middle"
            transform={`rotate(-90 14 ${PADDING.top + plotHeight / 2})`}
            className="fill-ink-muted text-[11px] font-semibold"
          >
            {scoreLabel}
          </text>
          {alertPredictions.map(({ prediction, windowIndex }) => {
            const left = x(prediction.startSeconds);
            const right = Math.max(left + 1, x(prediction.endSeconds));
            return (
              <rect
                key={`alert-band-${windowIndex}`}
                x={left}
                y={PADDING.top}
                width={Math.max(1, right - left)}
                height={plotHeight}
                className="fill-amber-soft/75"
              />
            );
          })}
          <path
            d={linePredictions
              .map(
                (prediction, index) =>
                  `${index === 0 ? "M" : "L"} ${x(windowCenterSeconds(prediction)).toFixed(2)} ${y(prediction.score).toFixed(2)}`,
              )
              .join(" ")}
            fill="none"
            stroke="currentColor"
            strokeWidth="2.25"
            vectorEffect="non-scaling-stroke"
            className="text-teal"
            data-testid="prediction-score-line"
            data-point-count={linePredictions.length}
          />
          {hoverPredictions.map(({ prediction, windowIndex }) => {
            const alert = prediction.seizureDetected;
            const alertIndex = alert
              ? (alertIndexByWindow.get(windowIndex) ?? -1)
              : -1;
            const selected = alert && alertIndex === selectedAlertIndex;
            const label = predictionLabel(prediction, windowIndex, threshold);
            return (
              <g key={`point-${windowIndex}`}>
                <circle
                  cx={x(windowCenterSeconds(prediction))}
                  cy={y(prediction.score)}
                  r="11"
                  className="fill-transparent stroke-transparent"
                  aria-label={label}
                  role={alert ? "button" : undefined}
                  tabIndex={alert ? 0 : -1}
                  data-alert-point={alert ? "true" : undefined}
                  data-score={prediction.score}
                  onMouseEnter={
                    alertIndex >= 0
                      ? () => setActiveAlertIndex(alertIndex)
                      : undefined
                  }
                  onFocus={
                    alertIndex >= 0
                      ? () => setActiveAlertIndex(alertIndex)
                      : undefined
                  }
                >
                  <title>{label}</title>
                </circle>
                {alert && (
                  <circle
                    cx={x(windowCenterSeconds(prediction))}
                    cy={y(prediction.score)}
                    r={selected ? 5 : 3.5}
                    className="pointer-events-none fill-amber stroke-white"
                    strokeWidth="1"
                    data-alert-point="true"
                    data-score={prediction.score}
                  />
                )}
              </g>
            );
          })}
          <line
            x1={PADDING.left}
            y1={thresholdY}
            x2={CHART_WIDTH - PADDING.right}
            y2={thresholdY}
            stroke="currentColor"
            strokeDasharray="5 5"
            className="text-amber"
          />
          <rect
            x={CHART_WIDTH - PADDING.right - 128}
            y={thresholdY - 20}
            width="128"
            height="18"
            rx="4"
            className="fill-surface"
          />
          <text
            x={CHART_WIDTH - PADDING.right - 8}
            y={thresholdY - 7}
            textAnchor="end"
            className="fill-amber text-[11px] font-semibold"
          >
            Alert threshold · {threshold.toFixed(2)}
          </text>
          <text
            x={PADDING.left}
            y={CHART_HEIGHT - 10}
            className="fill-ink-muted text-[11px]"
          >
            0:00
          </text>
          <text
            x={PADDING.left + plotWidth / 2}
            y={CHART_HEIGHT - 10}
            textAnchor="middle"
            className="fill-ink-muted text-[11px]"
          >
            {formatSeconds(recordingDuration / 2)}
          </text>
          <text
            x={CHART_WIDTH - PADDING.right}
            y={CHART_HEIGHT - 10}
            textAnchor="end"
            className="fill-ink-muted text-[11px]"
          >
            {formatSeconds(recordingDuration)}
          </text>
        </svg>
      </div>
      <div
        className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink-muted"
        aria-label="Prediction timeline legend"
      >
        <span className="inline-flex items-center gap-2">
          <span className="size-2 rounded-full bg-teal" aria-hidden="true" />
          {calibrated ? "Window probability" : "Window score"}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="size-2 rounded-full bg-amber" aria-hidden="true" />
          Window above threshold
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            className="w-4 border-t border-dashed border-amber"
            aria-hidden="true"
          />
          Alert threshold {threshold.toFixed(2)}
        </span>
      </div>
      {selectedAlert ? (
        <div
          className="mt-3 rounded-md border border-amber/30 bg-amber-soft px-3 py-2 text-xs leading-5 text-ink outline-none focus-visible:ring-2 focus-visible:ring-amber/40"
          role="group"
          tabIndex={0}
          aria-label="Browse exact flagged windows. Use the arrow keys, Home, or End."
          onKeyDown={handleAlertNavigation}
        >
          <p aria-live="polite">
            <span className="font-semibold text-amber">
              Flagged window {selectedAlertIndex + 1} of{" "}
              {alertPredictions.length}
            </span>{" "}
            ·{" "}
            <span className="font-mono">
              {formatSeconds(selectedAlert.prediction.startSeconds)}–
              {formatSeconds(selectedAlert.prediction.endSeconds)}
            </span>{" "}
            · {windowLabel} {selectedAlert.prediction.score.toFixed(3)}
          </p>
          <p className="mt-1 text-ink-muted">
            Use the arrow keys to inspect exact flagged times. Hover any visible
            point for its window details.
          </p>
        </div>
      ) : (
        <p className="mt-2 text-xs text-ink-muted">
          Hover any visible point for its exact window time and score. No window
          crossed the configured threshold.
        </p>
      )}
    </div>
  );
}

/** Keep every current-model window in the line and preserve alerts for unusually long recordings. */
function linePoints(
  predictions: PredictionWindow[],
  maxPoints: number,
): PredictionWindow[] {
  if (predictions.length <= maxPoints) return predictions;
  const alertCount = predictions.filter(
    (prediction) => prediction.seizureDetected,
  ).length;
  if (alertCount >= maxPoints)
    return predictions.filter((prediction) => prediction.seizureDetected);
  const normalBudget = Math.max(2, maxPoints - alertCount);
  const stride = Math.max(1, Math.ceil(predictions.length / normalBudget));
  return predictions.filter(
    (prediction, index) =>
      prediction.seizureDetected ||
      index === 0 ||
      index === predictions.length - 1 ||
      index % stride === 0,
  );
}

/** Describe one exact prediction window for native SVG hover details. */
function predictionLabel(
  prediction: PredictionWindow,
  windowIndex: number,
  threshold: number,
): string {
  const label =
    prediction.scoreType === "calibrated_probability"
      ? "estimated probability"
      : "score";
  return `Window ${windowIndex + 1}, ${formatSeconds(prediction.startSeconds)}–${formatSeconds(prediction.endSeconds)}, ${label} ${prediction.score.toFixed(3)}, ${prediction.seizureDetected ? "above" : "below"} threshold ${threshold.toFixed(2)}`;
}

/** Position each plotted value at the centre of its four-second support window. */
function windowCenterSeconds(prediction: PredictionWindow): number {
  return (prediction.startSeconds + prediction.endSeconds) / 2;
}

/** Format seconds as a compact recording-relative timestamp. */
function formatSeconds(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const remainingSeconds = whole % 60;
  if (hours > 0)
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}
