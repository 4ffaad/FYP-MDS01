"use client";

import { Label } from "@primer/react";
import {
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type KeyboardEvent,
} from "react";
import { Icon } from "@/components/Icon";
import type { DetectionResult } from "@/lib/video-detection";

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
  videoUrl,
  mediaLoading,
  mediaError,
  onRetryVisualization,
}: {
  result: DetectionResult;
  duration: number;
  videoUrl: string | null;
  mediaLoading: boolean;
  mediaError: string | null;
  onRetryVisualization?: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [showScore, setShowScore] = useState(true);
  const [showEvents, setShowEvents] = useState(true);
  const timeline = useMemo(() => timelineFor(result), [result]);
  const events = useMemo(() => eventsFor(result, timeline), [result, timeline]);
  const peakScore =
    result.summary?.peak_score ??
    Math.max(...timeline.map((point) => point.score), 0);
  const hasPotentialEvent =
    result.summary?.potential_event_detected ?? events.length > 0;
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

  function seek(timestamp: number) {
    const nextTime = Math.max(0, Math.min(duration, timestamp));
    if (videoRef.current) videoRef.current.currentTime = nextTime;
    setCurrentTime(nextTime);
  }

  return (
    <section
      className="panel mt-6 overflow-hidden"
      aria-labelledby="video-review-heading"
    >
      <div className="border-b border-rule bg-surface-soft/80 px-5 py-5 sm:px-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Protected review workspace</p>
            <h2
              id="video-review-heading"
              className="mt-1 text-xl font-semibold sm:text-2xl"
            >
              Privacy-safe video and model evidence
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">
              Playback shows the protected visualization only. The VSViG score
              is synchronized to the window covering the current video time.
            </p>
          </div>
          <Label
            variant={hasPotentialEvent ? "attention" : "success"}
            size="large"
          >
            {hasPotentialEvent
              ? "Review flagged intervals"
              : "No flagged intervals"}
          </Label>
        </div>
      </div>

      <div className="grid gap-6 p-5 sm:p-7 lg:grid-cols-[minmax(0,1.15fr)_minmax(17rem,0.85fr)]">
        <div className="min-w-0">
          <div className="relative aspect-video overflow-hidden rounded-2xl bg-[#0f171d] shadow-inner">
            {videoUrl ? (
              <video
                ref={videoRef}
                className="size-full object-contain"
                controls
                controlsList="nodownload"
                disablePictureInPicture
                playsInline
                preload="metadata"
                src={videoUrl}
                aria-label="Privacy-safe video with skeleton overlay"
                onTimeUpdate={(event) =>
                  setCurrentTime(event.currentTarget.currentTime)
                }
              />
            ) : (
              <div className="flex size-full min-h-64 flex-col items-center justify-center px-6 text-center text-white">
                <span className="grid size-12 place-items-center rounded-2xl bg-white/10 text-teal-light">
                  {mediaLoading ? (
                    <Icon name="spinner" className="size-6 animate-spin" />
                  ) : (
                    <Icon name="shield" className="size-6" />
                  )}
                </span>
                <p className="mt-4 text-sm font-semibold">
                  {mediaLoading
                    ? "Loading protected visualization"
                    : "Protected visualization unavailable"}
                </p>
                <p className="mt-2 max-w-sm text-xs leading-5 text-white/65">
                  {mediaError ??
                    "This legacy result has no retained review video. The original video is never exposed here."}
                </p>
                {mediaError && onRetryVisualization && (
                  <button
                    type="button"
                    className="mt-4 rounded-lg border border-white/20 px-3 py-2 text-xs font-semibold text-white transition hover:border-white/40 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-teal-light/60"
                    onClick={onRetryVisualization}
                  >
                    Retry protected video
                  </button>
                )}
              </div>
            )}
            {videoUrl && showScore && currentPoint && (
              <div className="pointer-events-none absolute left-4 top-4 rounded-xl border border-white/15 bg-[#0f171d]/90 px-3 py-2 text-white shadow-lg backdrop-blur">
                <p className="text-[0.65rem] font-bold tracking-[0.12em] text-teal-light uppercase">
                  VSViG model score
                </p>
                <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                  {currentPoint.score.toFixed(2)}
                </p>
                <p className="text-[0.65rem] text-white/65">
                  Uncalibrated · not a probability
                </p>
              </div>
            )}
            {videoUrl && showEvents && currentEvent && (
              <div className="pointer-events-none absolute bottom-4 left-4 rounded-lg border border-amber-300/30 bg-amber-950/85 px-3 py-2 text-xs text-amber-100 shadow-lg backdrop-blur">
                Event {events.indexOf(currentEvent) + 1} · human review
              </div>
            )}
          </div>

          <fieldset className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-3 text-xs text-ink-muted">
            <legend className="sr-only">Video overlay controls</legend>
            <span className="inline-flex items-center gap-2 font-semibold text-teal-dark">
              <Icon name="check" className="size-4" weight="bold" />
              Skeleton overlay baked into protected video
            </span>
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input
                className="size-4 accent-teal"
                type="checkbox"
                checked={showScore}
                onChange={(event) => setShowScore(event.target.checked)}
              />
              Current score
            </label>
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
              ? "Potential seizure activity detected"
              : "No threshold-crossing interval found"}
          </h3>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            {hasPotentialEvent
              ? "The configured research threshold was crossed in one or more windows. Review the protected video and event boundaries before drawing conclusions."
              : "No VSViG window crossed the configured research threshold. This does not rule out seizure activity."}
          </p>
          <dl className="mt-6 grid gap-4 border-t border-rule pt-5">
            <div className="flex items-end justify-between gap-4">
              <dt className="text-xs text-ink-muted">Peak model score</dt>
              <dd className="font-mono text-2xl font-semibold tabular-nums text-teal-dark">
                {peakScore.toFixed(2)}
              </dd>
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
          </dl>
          <p className="mt-6 rounded-xl border border-amber/25 bg-amber-soft/50 px-3 py-3 text-xs leading-5 text-amber">
            This is a research score, not a calibrated clinical probability or
            diagnosis.
          </p>
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
        <p className="text-xs text-ink-muted">
          Click the chart or an event to seek the video. Focus the chart and use
          Home, End, or the arrow keys for keyboard seeking.
        </p>
      </div>
      <svg
        className="mt-5 h-auto w-full cursor-crosshair overflow-visible text-ink-muted"
        viewBox="0 0 900 190"
        role="group"
        aria-label="VSViG model scores over video time"
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
          <p className="eyebrow">Review queue</p>
          <h3
            id="detected-events-heading"
            className="mt-1 text-base font-semibold"
          >
            Detected events
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
        <p className="mt-4 text-sm leading-6 text-ink-muted">
          No window crossed the configured threshold. This does not rule out
          seizure activity.
        </p>
      )}
    </section>
  );
}

function PrivacyIndicator({ result }: { result: DetectionResult }) {
  const hasVisualization = result.visualization?.available === true;
  const hasNoAudio = result.visualization?.audio_included === false;
  const hasPrivacyMetadata =
    result.privacy?.method === "face-detection-and-full-frame-blur";
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
            Privacy protection
          </h3>
          <ul className="mt-3 grid gap-2 text-xs leading-5 text-ink-muted sm:grid-cols-3">
            <PrivacyCheck
              ok={hasVisualization}
              text="Protected visualization available"
            />
            <PrivacyCheck
              ok={hasPrivacyMetadata}
              text="Face-redaction provenance recorded"
            />
            <PrivacyCheck ok={hasNoAudio} text="No audio in visual artifact" />
          </ul>
          <p className="mt-3 text-[0.7rem] leading-5 text-ink-faint">
            The original upload and temporary model input are deleted after
            processing. The retained artifact is encrypted private storage; this
            transform does not guarantee anonymity.
          </p>
        </div>
      </div>
    </section>
  );
}

function PrivacyCheck({ ok, text }: { ok: boolean; text: string }) {
  return (
    <li
      className={
        ok
          ? "flex items-center gap-2 text-teal-dark"
          : "flex items-center gap-2 text-amber"
      }
    >
      <Icon
        name={ok ? "check" : "alert"}
        className="size-4 shrink-0"
        weight="bold"
      />
      <span>{ok ? text : `${text} unavailable`}</span>
    </li>
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
