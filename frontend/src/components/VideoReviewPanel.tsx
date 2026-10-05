"use client";

import { Label } from "@primer/react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type KeyboardEvent,
} from "react";
import { Icon } from "@/components/Icon";
import type { DetectionResult } from "@/lib/video-detection";
import {
  gradCamSampleForVideoTime,
  poseSampleForVideoTime,
  VideoGradCamOverlay,
  VideoModelPatchBlurOverlay,
} from "@/components/VideoModelEvidenceOverlay";

type TimelinePoint = {
  timestamp: number;
  start_time: number;
  end_time: number;
  score: number;
  seizure_detected: boolean;
};

type ReviewEvent = {
  start_time: number;
  end_time: number;
  peak_score: number;
  peak_timestamp: number;
};

function formatTime(seconds: number) {
  const safeSeconds = Math.max(0, seconds);
  return `${Math.floor(safeSeconds / 60)}:${(safeSeconds % 60).toFixed(1).padStart(4, "0")}`;
}

function formatPercent(value: number) {
  return new Intl.NumberFormat(undefined, {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

function timelineFor(result: DetectionResult): TimelinePoint[] {
  if (result.timeline?.length) return result.timeline;
  return result.predictions.map((prediction) => ({
    timestamp: (prediction.start_time + prediction.end_time) / 2,
    start_time: prediction.start_time,
    end_time: prediction.end_time,
    score: prediction.score,
    seizure_detected: prediction.seizure_detected,
  }));
}

function eventsFor(
  result: DetectionResult,
  timeline: TimelinePoint[],
): ReviewEvent[] {
  if (result.events?.length) return result.events;
  return result.intervals.map((interval) => {
    const supporting = timeline.filter(
      (point) =>
        point.seizure_detected &&
        point.start_time < interval.end_time &&
        point.end_time > interval.start_time,
    );
    const peak = supporting.reduce(
      (best, point) => (point.score > best.score ? point : best),
      supporting[0] ?? timeline[0],
    );
    return {
      start_time: interval.start_time,
      end_time: interval.end_time,
      peak_score: peak.score,
      peak_timestamp: peak.timestamp,
    };
  });
}

export function VideoReviewPanel({
  result,
  duration,
  videoAvailable,
  videoUrl,
  initialTimeSeconds,
}: {
  result: DetectionResult;
  duration: number;
  videoAvailable: boolean;
  videoUrl: string;
  initialTimeSeconds?: number;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoFrameRef = useRef<HTMLDivElement>(null);
  const [currentTime, setCurrentTime] = useState(() =>
    Number.isFinite(initialTimeSeconds)
      ? Math.max(0, initialTimeSeconds ?? 0)
      : 0,
  );
  const [videoUnavailable, setVideoUnavailable] = useState(false);
  const [showEvents, setShowEvents] = useState(true);
  const [blurMode, setBlurMode] = useState<"face+patches" | "face" | "all">(
    "face+patches",
  );
  const [isFullscreen, setIsFullscreen] = useState(false);
  const timeline = useMemo(() => timelineFor(result), [result]);
  const events = useMemo(() => eventsFor(result, timeline), [result, timeline]);
  const peakScore =
    result.summary?.peak_score ??
    Math.max(...timeline.map((point) => point.score), 0);
  const hasPotentialEvent =
    result.summary?.potential_event_detected ?? events.length > 0;
  const usesPatientBlur =
    result.visualization?.privacy_method.includes("patient-blur") ??
    result.privacy?.method.includes("patient-blur") ??
    false;
  const selectiveBlurLabel = usesPatientBlur
    ? "Legacy patient blur"
    : "Face blur";
  const blurCoverage =
    result.visualization?.face_blur_coverage ??
    result.privacy?.face_blur_coverage ??
    result.visualization?.patient_blur_coverage;
  const faceDetectionCoverage = result.visualization?.face_detection_coverage;
  const blurCoverageLabel =
    typeof blurCoverage === "number"
      ? `${formatPercent(blurCoverage)} of frames`
      : typeof faceDetectionCoverage === "number"
        ? `${formatPercent(faceDetectionCoverage)} face detections`
        : null;
  const currentPoint =
    timeline.find(
      (point) =>
        currentTime >= point.start_time && currentTime < point.end_time,
    ) ??
    timeline.reduce(
      (closest, point) =>
        Math.abs(point.timestamp - currentTime) <
        Math.abs(closest.timestamp - currentTime)
          ? point
          : closest,
      timeline[0],
    );
  const currentEvent = events.find(
    (event) => currentTime >= event.start_time && currentTime <= event.end_time,
  );
  const currentPrediction = result.predictions.find(
    (prediction) =>
      currentTime >= prediction.start_time && currentTime < prediction.end_time,
  );
  const evidence = currentPrediction?.model_evidence;
  const currentPoseSample = poseSampleForVideoTime(
    currentPrediction,
    currentTime,
    result.model.sample_fps,
  );
  const currentGradCamSample = gradCamSampleForVideoTime(
    currentPrediction,
    currentTime,
    result.model.sample_fps,
  );
  const selectedBlurModeLabel =
    blurMode === "all"
      ? "Full-frame blur"
      : blurMode === "face"
        ? `${selectiveBlurLabel} only`
        : "Face + 15 patches";

  useEffect(() => {
    const updateFullscreen = () =>
      setIsFullscreen(document.fullscreenElement === videoFrameRef.current);
    document.addEventListener("fullscreenchange", updateFullscreen);
    return () =>
      document.removeEventListener("fullscreenchange", updateFullscreen);
  }, []);

  async function toggleFullscreen() {
    const frame = videoFrameRef.current;
    if (!frame) return;
    if (isFullscreen) {
      if (document.fullscreenElement === frame) {
        try {
          await document.exitFullscreen();
        } catch {
          setIsFullscreen(false);
        }
      } else {
        setIsFullscreen(false);
      }
      return;
    }

    if (typeof frame.requestFullscreen !== "function") {
      setIsFullscreen(true);
      return;
    }

    try {
      await frame.requestFullscreen();
    } catch {
      setIsFullscreen(true);
    }
  }

  function seek(timestamp: number) {
    const nextTime = Math.max(0, Math.min(duration, timestamp));
    setCurrentTime(nextTime);
    if (videoRef.current?.readyState) videoRef.current.currentTime = nextTime;
  }

  useEffect(() => {
    if (
      typeof initialTimeSeconds === "number" &&
      Number.isFinite(initialTimeSeconds)
    ) {
      const nextTime = Math.max(0, Math.min(duration, initialTimeSeconds));
      if (videoRef.current?.readyState) videoRef.current.currentTime = nextTime;
    }
  }, [initialTimeSeconds, duration]);

  return (
    <section
      className="panel mt-6 overflow-hidden"
      aria-labelledby="video-review-heading"
    >
      <div className="border-b border-rule bg-surface-soft/80 px-5 py-5 sm:px-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Video review</p>
            <h2
              id="video-review-heading"
              className="mt-1 text-xl font-semibold sm:text-2xl"
            >
              VSViG score and protected video
            </h2>
          </div>
          <Label
            variant={hasPotentialEvent ? "attention" : "success"}
            size="large"
          >
            {hasPotentialEvent ? "Threshold crossed" : "No flagged intervals"}
          </Label>
        </div>
      </div>

      <div className="grid gap-6 p-5 sm:p-7 lg:grid-cols-[minmax(0,1.15fr)_minmax(17rem,0.85fr)]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <fieldset className="flex flex-wrap gap-3 text-xs text-ink-muted">
              <legend className="sr-only">Video display blur</legend>
              <label className="inline-flex cursor-pointer items-center gap-2">
                <input
                  className="size-4 accent-teal"
                  type="radio"
                  name={`video-display-blur-${result.model.model_version}`}
                  checked={blurMode === "face+patches"}
                  onChange={() => setBlurMode("face+patches")}
                />
                Face + 15 patches
              </label>
              <label className="inline-flex cursor-pointer items-center gap-2">
                <input
                  className="size-4 accent-teal"
                  type="radio"
                  name={`video-display-blur-${result.model.model_version}`}
                  checked={blurMode === "face"}
                  onChange={() => setBlurMode("face")}
                />
                {selectiveBlurLabel} only
              </label>
              <label className="inline-flex cursor-pointer items-center gap-2">
                <input
                  className="size-4 accent-teal"
                  type="radio"
                  name={`video-display-blur-${result.model.model_version}`}
                  checked={blurMode === "all"}
                  onChange={() => setBlurMode("all")}
                />
                Blur all
              </label>
            </fieldset>
            <span className="text-xs text-ink-muted">
              Face blur · patch blur{" "}
              {result.privacy?.blur_strength_percent ?? "—"}%
            </span>
            <button
              className="min-h-9 rounded-md border border-rule px-3 text-xs font-semibold text-ink hover:bg-surface-soft"
              type="button"
              aria-label={isFullscreen ? "Exit full screen" : "Full screen"}
              onClick={toggleFullscreen}
            >
              {isFullscreen ? "Exit full screen" : "Full screen"}
            </button>
          </div>
          {videoAvailable && !videoUnavailable ? (
            <div
              ref={videoFrameRef}
              className={
                isFullscreen
                  ? "fixed inset-0 z-[100] flex h-dvh w-screen items-center justify-center bg-black"
                  : "relative aspect-video w-full overflow-hidden rounded-2xl bg-black"
              }
              data-testid="video-review-frame"
            >
              <div
                className={
                  isFullscreen
                    ? "relative aspect-video max-h-full max-w-full overflow-hidden bg-black"
                    : "absolute inset-0"
                }
                style={
                  isFullscreen ? { width: "min(100vw, 177.78vh)" } : undefined
                }
              >
                <div
                  className={`absolute inset-0 ${blurMode === "all" ? "blur-[8px]" : ""}`}
                >
                  <video
                    ref={videoRef}
                    className="size-full object-contain"
                    src={videoUrl}
                    controls
                    controlsList="nofullscreen"
                    playsInline
                    preload="metadata"
                    crossOrigin="use-credentials"
                    aria-label={`${blurMode === "all" ? "Full-frame blurred" : `${selectiveBlurLabel}-protected`} patient video with model evidence, synchronized to the VSViG score timeline`}
                    onLoadedMetadata={() => {
                      if (videoRef.current) {
                        const requestedTime =
                          typeof initialTimeSeconds === "number" &&
                          Number.isFinite(initialTimeSeconds)
                            ? initialTimeSeconds
                            : currentTime;
                        videoRef.current.currentTime = Math.max(
                          0,
                          Math.min(duration, requestedTime),
                        );
                      }
                    }}
                    onTimeUpdate={(event) =>
                      setCurrentTime(event.currentTarget.currentTime)
                    }
                    onError={() => setVideoUnavailable(true)}
                  >
                    Your browser cannot play this review video.
                  </video>
                  <VideoModelPatchBlurOverlay
                    videoRef={videoRef}
                    poseSample={currentPoseSample}
                    strengthPercent={
                      result.privacy?.blur_strength_percent ?? 100
                    }
                    enabled={blurMode === "face+patches"}
                  />
                  <VideoGradCamOverlay
                    poseSample={currentPoseSample}
                    gradCamSample={currentGradCamSample}
                  />
                </div>
                <span className="pointer-events-none absolute left-3 top-3 z-20 rounded-md bg-black/75 px-2.5 py-1.5 text-xs font-semibold text-white">
                  {selectedBlurModeLabel}
                </span>
                <button
                  className="absolute right-3 top-3 z-20 min-h-9 rounded-md bg-black/75 px-3 text-xs font-semibold text-white hover:bg-black"
                  type="button"
                  aria-label={isFullscreen ? "Exit full screen" : "Full screen"}
                  onClick={toggleFullscreen}
                >
                  {isFullscreen ? "Exit full screen" : "Full screen"}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex aspect-video min-h-64 flex-col items-center justify-center rounded-2xl border border-rule bg-surface-soft px-6 text-center">
              <span className="grid size-12 place-items-center rounded-2xl bg-teal-soft text-teal-dark">
                <Icon name="shield" className="size-6" />
              </span>
              <h3 className="mt-4 text-sm font-semibold">
                Review video is unavailable
              </h3>
              <p className="mt-2 max-w-md text-xs leading-5 text-ink-muted">
                {videoAvailable
                  ? "The protected video could not be loaded. Reload this result to retry."
                  : "This job has no retained review video."}{" "}
                Use the score timeline and event times below to review the
                result.
              </p>
            </div>
          )}
          {result.visualization && (
            <p className="mt-3 text-xs text-ink-muted">
              {selectiveBlurLabel}
              {blurCoverageLabel ? ` · ${blurCoverageLabel}` : ""}
              {result.visualization.full_frame_fallback_frames > 0
                ? ` · full-frame fallback ${result.visualization.full_frame_fallback_frames} frames`
                : ""}
            </p>
          )}
          {currentPoseSample && evidence && (
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
              <span>
                {evidence.method === "vsvig-graph-grad-cam"
                  ? `VSViG Grad-CAM · ${evidence.target_class === "flagged" ? "flagged" : "below threshold"} window`
                  : "Older run · patch sensitivity only"}
              </span>
              {evidence.method === "vsvig-graph-grad-cam" && (
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="size-2.5 rounded-sm bg-gradient-to-r from-amber to-red"
                    aria-hidden="true"
                  />
                  Warmer patch = stronger contribution
                </span>
              )}
            </div>
          )}

          <fieldset className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-3 text-xs text-ink-muted">
            <legend className="sr-only">Timeline display controls</legend>
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input
                className="size-4 accent-teal"
                type="checkbox"
                checked={showEvents}
                onChange={(event) => setShowEvents(event.target.checked)}
              />
              Event markers
            </label>
          </fieldset>
        </div>

        <aside
          className="rounded-2xl border border-rule bg-surface-soft p-5"
          aria-labelledby="assessment-heading"
        >
          <p className="eyebrow">Model assessment</p>
          <h3 id="assessment-heading" className="mt-2 text-lg font-semibold">
            {hasPotentialEvent
              ? "Threshold crossed"
              : "No threshold-crossing interval found"}
          </h3>
          <p className="mt-2 text-sm text-ink-muted">
            Research output · not a diagnosis.
          </p>
          <dl className="mt-6 grid gap-4 border-t border-rule pt-5">
            <div className="flex items-end justify-between gap-4">
              <dt className="text-xs text-ink-muted">Peak model score</dt>
              <dd className="font-mono text-2xl font-semibold tabular-nums text-teal-dark">
                {peakScore.toFixed(2)}
              </dd>
            </div>
            <div
              className="-mt-2"
              role="img"
              aria-label={`Peak score ${peakScore.toFixed(3)} on a fixed 0 to 1 display scale; threshold ${result.model.threshold.toFixed(3)}`}
            >
              <div className="relative mx-1 h-2 rounded-full bg-rule">
                <span
                  className="absolute -top-1 h-4 w-px bg-amber"
                  style={{
                    left: `${Math.max(0, Math.min(100, result.model.threshold * 100))}%`,
                  }}
                  aria-hidden="true"
                />
                <span
                  className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-teal-dark"
                  style={{
                    left: `${Math.max(0, Math.min(100, peakScore * 100))}%`,
                  }}
                  aria-hidden="true"
                />
              </div>
              <div className="mt-2 flex justify-between text-[0.65rem] tabular-nums text-ink-muted">
                <span>0.0</span>
                <span>Threshold {result.model.threshold.toFixed(2)}</span>
                <span>1.0</span>
              </div>
            </div>
            <div className="flex items-end justify-between gap-4">
              <dt className="text-xs text-ink-muted">Event windows</dt>
              <dd className="font-mono text-lg font-semibold tabular-nums text-ink">
                {events.length}
              </dd>
            </div>
            {events[0] && (
              <div className="flex items-end justify-between gap-4">
                <dt className="text-xs text-ink-muted">First event window</dt>
                <dd className="font-mono text-sm font-semibold tabular-nums text-ink">
                  {formatTime(events[0].start_time)}–
                  {formatTime(events[0].end_time)}
                </dd>
              </div>
            )}
            {currentPoint && (
              <div className="flex items-end justify-between gap-4">
                <dt className="text-xs text-ink-muted">
                  Selected window score
                </dt>
                <dd className="font-mono text-sm font-semibold tabular-nums text-ink">
                  {currentPoint.score.toFixed(2)}
                  {currentEvent ? " · within flagged interval" : ""}
                </dd>
              </div>
            )}
            <div className="flex items-end justify-between gap-4">
              <dt className="text-xs text-ink-muted">Selected video time</dt>
              <dd className="font-mono text-sm font-semibold tabular-nums text-ink">
                {formatTime(currentTime)}
              </dd>
            </div>
          </dl>
        </aside>
      </div>

      <RiskTimeline
        timeline={timeline}
        events={events}
        threshold={result.summary?.threshold ?? result.model.threshold}
        duration={duration}
        currentTime={currentTime}
        showEvents={showEvents}
        onSeek={seek}
      />
      <EventList events={events} onSeek={seek} />
      <PrivacyIndicator result={result} />
    </section>
  );
}

function RiskTimeline({
  timeline,
  events,
  threshold,
  duration,
  currentTime,
  showEvents,
  onSeek,
}: {
  timeline: TimelinePoint[];
  events: ReviewEvent[];
  threshold: number;
  duration: number;
  currentTime: number;
  showEvents: boolean;
  onSeek: (timestamp: number) => void;
}) {
  const left = 42;
  const right = 884;
  const top = 18;
  const bottom = 156;
  const xForTime = (time: number) =>
    left + (Math.max(0, Math.min(duration, time)) / duration) * (right - left);
  const yForScore = (score: number) =>
    bottom - Math.max(0, Math.min(1, score)) * (bottom - top);
  const handleChartClick = (event: MouseEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    onSeek(((event.clientX - bounds.left) / bounds.width) * duration);
  };
  const handleChartKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    const step = Math.max(1, duration / 20);
    const nextTime =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? duration
          : event.key === "ArrowLeft"
            ? currentTime - step
            : event.key === "ArrowRight"
              ? currentTime + step
              : null;
    if (nextTime === null) return;
    event.preventDefault();
    onSeek(nextTime);
  };

  return (
    <section
      className="border-t border-rule px-5 py-5 sm:px-7"
      aria-labelledby="risk-timeline-heading"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Synchronized evidence</p>
          <h3
            id="risk-timeline-heading"
            className="mt-1 text-base font-semibold"
          >
            VSViG score over time
          </h3>
        </div>
        <p className="text-xs text-ink-muted">Select a score point or event.</p>
      </div>
      <svg
        className="mt-5 h-auto w-full cursor-crosshair overflow-visible text-ink-muted"
        viewBox="0 0 900 190"
        role="group"
        aria-label="VSViG model scores over recording time"
        aria-describedby="risk-timeline-help"
        tabIndex={0}
        onClick={handleChartClick}
        onKeyDown={handleChartKeyDown}
      >
        {[0, 0.5, 1].map((tick) => (
          <g key={tick}>
            <line
              x1={left}
              x2={right}
              y1={yForScore(tick)}
              y2={yForScore(tick)}
              stroke="currentColor"
              opacity="0.12"
            />
            <text
              x="0"
              y={yForScore(tick) + 4}
              fontSize="12"
              fill="currentColor"
            >
              {tick.toFixed(1)}
            </text>
          </g>
        ))}
        <line
          x1={left}
          x2={right}
          y1={yForScore(threshold)}
          y2={yForScore(threshold)}
          stroke="var(--color-amber, #8a5a00)"
          strokeDasharray="5 5"
        />
        {showEvents &&
          events.map((event) => (
            <rect
              key={`${event.start_time}-${event.end_time}`}
              x={xForTime(event.start_time)}
              y={top}
              width={Math.max(
                2,
                xForTime(event.end_time) - xForTime(event.start_time),
              )}
              height={bottom - top}
              fill="var(--color-amber, #8a5a00)"
              opacity="0.1"
              pointerEvents="none"
            />
          ))}
        <polyline
          fill="none"
          stroke="var(--color-teal, #0066cc)"
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={timeline
            .map(
              (point) =>
                `${xForTime(point.timestamp)},${yForScore(point.score)}`,
            )
            .join(" ")}
        />
        {timeline.map((point) => (
          <circle
            key={`${point.start_time}-${point.end_time}`}
            cx={xForTime(point.timestamp)}
            cy={yForScore(point.score)}
            r="3.5"
            fill={
              point.seizure_detected
                ? "var(--color-amber, #8a5a00)"
                : "var(--color-teal, #0066cc)"
            }
            role="button"
            tabIndex={0}
            aria-label={`${formatTime(point.start_time)} to ${formatTime(point.end_time)}, score ${point.score.toFixed(2)}, ${point.seizure_detected ? "flagged window" : "not flagged"}`}
            onClick={(event) => {
              event.stopPropagation();
              onSeek(point.timestamp);
            }}
            onKeyDown={(event) =>
              handleVideoTimelineKeyDown(event, point.timestamp, onSeek)
            }
          />
        ))}
        <line
          x1={xForTime(currentTime)}
          x2={xForTime(currentTime)}
          y1={top}
          y2={bottom}
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.75"
          pointerEvents="none"
        />
        <text x={left} y="184" fontSize="12" fill="currentColor">
          0:00
        </text>
        <text
          x={right}
          y="184"
          textAnchor="end"
          fontSize="12"
          fill="currentColor"
        >
          {formatTime(duration)}
        </text>
      </svg>
      <p id="risk-timeline-help" className="mt-2 text-xs text-ink-muted">
        Dashed line: configured research threshold {threshold.toFixed(2)} ·
        scores are not calibrated probabilities.
      </p>
    </section>
  );
}

function EventList({
  events,
  onSeek,
}: {
  events: ReviewEvent[];
  onSeek: (timestamp: number) => void;
}) {
  return (
    <section
      className="border-t border-rule px-5 py-5 sm:px-7"
      aria-labelledby="detected-events-heading"
    >
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Model output</p>
          <h3
            id="detected-events-heading"
            className="mt-1 text-base font-semibold"
          >
            VSViG flagged intervals
          </h3>
        </div>
        <span className="font-mono text-xs tabular-nums text-ink-muted">
          {events.length.toString().padStart(2, "0")}
        </span>
      </div>
      {events.length ? (
        <ol className="mt-4 grid gap-3 sm:grid-cols-2">
          {events.map((event, index) => (
            <li key={`${event.start_time}-${event.end_time}`}>
              <button
                className="group flex w-full items-center justify-between gap-4 rounded-xl border border-rule bg-surface-soft px-4 py-3 text-left transition-colors hover:border-teal/40 hover:bg-teal-soft/30 focus-visible:ring-4 focus-visible:ring-teal/20"
                type="button"
                onClick={() => onSeek(event.peak_timestamp)}
              >
                <span>
                  <span className="block text-sm font-semibold text-ink">
                    Event {index + 1}
                  </span>
                  <span className="mt-1 block font-mono text-xs tabular-nums text-ink-muted">
                    {formatTime(event.start_time)}–{formatTime(event.end_time)}
                  </span>
                </span>
                <span className="text-right">
                  <span className="block text-[0.65rem] font-bold tracking-[0.1em] text-ink-faint uppercase">
                    Peak score
                  </span>
                  <span className="mt-1 block font-mono text-sm font-semibold tabular-nums text-teal-dark">
                    {event.peak_score.toFixed(2)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-4 text-sm text-ink-muted">No flagged intervals.</p>
      )}
    </section>
  );
}

function PrivacyIndicator({ result }: { result: DetectionResult }) {
  const usesPatientBlur =
    result.privacy?.method.includes("patient-blur") ?? false;
  const usesTrackedFaceBlur =
    result.privacy?.method.includes("tracked-face-blur") ?? false;
  const hasPrivacyMetadata = Boolean(result.privacy?.method);
  return (
    <section
      className="border-t border-rule bg-surface-soft px-5 py-5 sm:px-7"
      aria-labelledby="privacy-indicator-heading"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-teal-soft text-teal-dark">
          <Icon name="shield" className="size-4" />
        </span>
        <div>
          <h3 id="privacy-indicator-heading" className="text-sm font-semibold">
            Privacy
          </h3>
          <p className="mt-1 text-xs text-ink-muted">
            {hasPrivacyMetadata
              ? `${usesPatientBlur ? "Patient region" : usesTrackedFaceBlur ? "Tracked face" : "Face"} blur + full-frame fallback`
              : "Privacy provenance unavailable"}
            {result.visualization?.available
              ? " · encrypted until expiry"
              : " · no retained review video"}
          </p>
          <p className="mt-1 text-xs text-ink-muted">
            Source video is removed after processing.
          </p>
        </div>
      </div>
    </section>
  );
}

export function handleVideoTimelineKeyDown(
  event: KeyboardEvent<SVGCircleElement>,
  timestamp: number,
  onSeek: (timestamp: number) => void,
) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSeek(timestamp);
  }
}
