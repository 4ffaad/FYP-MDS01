"use client";

import type { EegAnnotationEvent, PredictionWindow } from "@/lib/types";
import { useRef, type PointerEvent, type ReactNode } from "react";
import { videoTimeForEegTime, type DetectionJob } from "@/lib/video-detection";
import { formatRelativeTime } from "@/lib/format";

/** Put model flags, imported markers, and verified video coverage on EEG time. */
export function SourceClockTimeline({
  predictions,
  events,
  clips,
  durationSeconds,
  selectedEegTime,
  onSelectEegTime,
}: {
  predictions: PredictionWindow[];
  events: EegAnnotationEvent[];
  clips: DetectionJob[];
  durationSeconds: number;
  selectedEegTime: number | null;
  onSelectEegTime: (seconds: number) => void;
}) {
  const videoSegments = clips.flatMap((clip, clipIndex) =>
    (clip.sync?.mapped_segments ?? []).map((segment) => ({
      clip,
      clipIndex,
      ...segment,
      eegEndSeconds:
        segment.eeg_source_start_seconds +
        segment.video_end_seconds -
        segment.video_start_seconds,
    })),
  );
  const timelineEnd = Math.max(
    durationSeconds,
    predictions.at(-1)?.endSeconds ?? 0,
    ...events.map((event) => event.onsetSeconds + event.durationSeconds),
    ...videoSegments.map((segment) => segment.eegEndSeconds),
    1,
  );
  const position = (seconds: number) =>
    `${(Math.max(0, Math.min(timelineEnd, seconds)) / timelineEnd) * 100}%`;
  const playheadPosition =
    selectedEegTime === null ? null : position(selectedEegTime);
  const linkedClip =
    selectedEegTime === null
      ? null
      : (clips.find(
          (clip) =>
            videoTimeForEegTime(clip.sync?.mapped_segments, selectedEegTime) !==
            null,
        ) ?? null);
  const linkedVideoTime = linkedClip?.sync
    ? videoTimeForEegTime(linkedClip.sync.mapped_segments, selectedEegTime ?? 0)
    : null;
  const sourceTimeLabel = formatRelativeTime(selectedEegTime ?? 0);
  const videoTimeLabel =
    linkedClip && linkedVideoTime !== null
      ? " · Video " +
        String(clips.indexOf(linkedClip) + 1).padStart(2, "0") +
        " · " +
        formatRelativeTime(linkedVideoTime)
      : selectedEegTime === null
        ? ""
        : " · No video";
  const scrubTrack = useRef<HTMLElement | null>(null);
  const scrubPointerId = useRef<number | null>(null);
  const scrubAt = (clientX: number) => {
    const track = scrubTrack.current;
    if (!track) return;
    const bounds = track.getBoundingClientRect();
    onSelectEegTime(
      (Math.max(0, Math.min(bounds.width, clientX - bounds.left)) /
        bounds.width) *
        timelineEnd,
    );
  };
  const beginScrub = (event: PointerEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("button")) return;
    const track = (event.target as HTMLElement).closest<HTMLElement>(
      "[data-timeline-track]",
    );
    if (!track || !track.getBoundingClientRect().width) return;
    scrubTrack.current = track;
    scrubPointerId.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    scrubAt(event.clientX);
  };
  const moveScrub = (event: PointerEvent<HTMLDivElement>) => {
    if (scrubPointerId.current === event.pointerId) scrubAt(event.clientX);
  };
  const endScrub = (event: PointerEvent<HTMLDivElement>) => {
    if (scrubPointerId.current !== event.pointerId) return;
    scrubPointerId.current = null;
    scrubTrack.current = null;
  };

  return (
    <div
      className="space-y-1 border-b border-rule px-3 py-2 sm:px-4"
      role="group"
      aria-label="EEG and video source-clock timeline"
    >
      <div
        className="space-y-1 touch-pan-y"
        onPointerDown={beginScrub}
        onPointerMove={moveScrub}
        onPointerUp={endScrub}
        onPointerCancel={endScrub}
        onKeyDown={(event) => {
          if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
          event.preventDefault();
          onSelectEegTime(
            Math.max(
              0,
              Math.min(
                timelineEnd,
                (selectedEegTime ?? 0) + (event.key === "ArrowRight" ? 1 : -1),
              ),
            ),
          );
        }}
        tabIndex={0}
        role="group"
        aria-label="Shared EEG timeline. Click or drag any lane to seek; use arrow keys to move one second."
      >
        <TimelineTrack label="Model flags" playheadPosition={playheadPosition}>
          <div
            className="absolute inset-0"
            role="group"
            aria-label={`${predictions.filter((prediction) => prediction.seizureDetected).length} threshold-crossing model windows`}
          >
            {predictions
              .filter((prediction) => prediction.seizureDetected)
              .map((prediction, index) => (
                <button
                  key={`${prediction.startSeconds}-${index}`}
                  className="absolute inset-y-1 min-w-px rounded-sm bg-amber/80 hover:bg-amber focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-dark"
                  style={{
                    left: position(prediction.startSeconds),
                    width: `${Math.max(0.12, ((prediction.endSeconds - prediction.startSeconds) / timelineEnd) * 100)}%`,
                  }}
                  type="button"
                  aria-label={`Select flagged model window at EEG ${formatRelativeTime(prediction.startSeconds)} to ${formatRelativeTime(prediction.endSeconds)}, score ${prediction.score.toFixed(3)}`}
                  title={`Flagged model window · EEG ${formatRelativeTime(prediction.startSeconds)}–${formatRelativeTime(prediction.endSeconds)} · score ${prediction.score.toFixed(3)}`}
                  onClick={() =>
                    onSelectEegTime(
                      prediction.startSeconds +
                        (prediction.endSeconds - prediction.startSeconds) / 2,
                    )
                  }
                />
              ))}
          </div>
        </TimelineTrack>

        <TimelineTrack label="EEG markers" playheadPosition={playheadPosition}>
          {events.map((event, index) => (
            <button
              key={`${event.onsetSeconds}-${event.kind}-${index}`}
              className={`absolute top-1/2 h-4 w-0.5 -translate-x-1/2 -translate-y-1/2 focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-dark ${markerTone(event)}`}
              style={{ left: position(event.onsetSeconds) }}
              type="button"
              aria-label={`Select ${eventLabel(event)} at EEG ${formatRelativeTime(event.onsetSeconds)}`}
              title={`${eventLabel(event)} · EEG ${formatRelativeTime(event.onsetSeconds)}`}
              onClick={() => onSelectEegTime(event.onsetSeconds)}
            />
          ))}
        </TimelineTrack>

        <TimelineTrack label="Video clips" playheadPosition={playheadPosition}>
          {videoSegments.map((segment, index) => {
            const duration =
              segment.eegEndSeconds - segment.eeg_source_start_seconds;
            return (
              <button
                key={`${segment.clip.job_id}-${index}`}
                className="absolute inset-y-1 min-w-1 rounded-sm bg-teal-dark/80 hover:bg-teal-dark focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-dark"
                style={{
                  left: position(segment.eeg_source_start_seconds),
                  width: `${Math.max(0.18, (duration / timelineEnd) * 100)}%`,
                }}
                type="button"
                aria-label={`Select Video ${String(segment.clipIndex + 1).padStart(2, "0")} coverage from EEG ${formatRelativeTime(segment.eeg_source_start_seconds)} to ${formatRelativeTime(segment.eegEndSeconds)}`}
                title={`Video ${String(segment.clipIndex + 1).padStart(2, "0")} · EEG ${formatRelativeTime(segment.eeg_source_start_seconds)}–${formatRelativeTime(segment.eegEndSeconds)}`}
                onClick={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const fraction =
                    event.detail === 0 || bounds.width === 0
                      ? 0.5
                      : Math.max(
                          0,
                          Math.min(
                            1,
                            (event.clientX - bounds.left) / bounds.width,
                          ),
                        );
                  onSelectEegTime(
                    segment.eeg_source_start_seconds + fraction * duration,
                  );
                }}
              />
            );
          })}
        </TimelineTrack>

        <div className="ml-[5.25rem] flex justify-between font-mono text-[0.68rem] tabular-nums text-ink-muted sm:ml-[6rem]">
          <span>EEG 0:00</span>
          <span>EEG {formatRelativeTime(timelineEnd / 2)}</span>
          <span>EEG {formatRelativeTime(timelineEnd)}</span>
        </div>
      </div>

      <p
        className="flex min-h-4 justify-between font-mono text-[0.68rem] tabular-nums text-ink-muted"
        role="status"
        aria-label={"EEG " + sourceTimeLabel + videoTimeLabel}
      >
        <span>EEG {sourceTimeLabel}</span>
        {videoTimeLabel && <span>{videoTimeLabel.slice(3)}</span>}
      </p>
    </div>
  );
}

function TimelineTrack({
  label,
  playheadPosition,
  children,
}: {
  label: string;
  playheadPosition: string | null;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-[4.75rem_minmax(0,1fr)] items-center gap-2 sm:grid-cols-[5.25rem_minmax(0,1fr)] sm:gap-3">
      <span className="text-right text-[0.65rem] font-semibold text-ink-muted sm:text-[0.7rem]">
        {label}
      </span>
      <div
        data-timeline-track
        className="relative h-5 overflow-hidden rounded-sm bg-[#fffef6]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #e8e3d3 1px, transparent 1px)",
          backgroundSize: "16.6667% 100%",
        }}
      >
        {children}
        {playheadPosition !== null && (
          <span
            className="pointer-events-none absolute inset-y-0 z-10 w-px bg-ink"
            style={{ left: playheadPosition }}
            aria-hidden="true"
          />
        )}
      </div>
    </div>
  );
}

function markerTone(event: EegAnnotationEvent): string {
  if (event.kind === "seizure_event") return "bg-red";
  if (event.kind === "manual_annotation") return "bg-amber";
  return "bg-teal-dark";
}

function eventLabel(event: EegAnnotationEvent): string {
  if (event.kind === "seizure_event") return "source-tagged event";
  if (event.kind === "manual_annotation") return "manual event";
  return "imported event";
}
