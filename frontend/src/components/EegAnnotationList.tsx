import Link from "next/link";
import type { EegAnnotationEvent, EegAnnotationSource } from "@/lib/types";
import {
  videoTimeForEegTime,
  type DetectionJob,
  type VideoEegSync,
} from "@/lib/video-detection";
import { formatRelativeTime } from "@/lib/format";

/** Show source event locations compactly while preserving exact marker times. */
export function EegAnnotationList({
  events,
  source,
  recordingDurationSeconds,
  videoStartMinusEegStartSeconds,
  videoDurationSeconds,
  videoReviewHref,
  videoMappedSegments,
  videoClips,
  onEegTimeSelect,
}: {
  events: EegAnnotationEvent[];
  source: EegAnnotationSource;
  recordingDurationSeconds: number;
  videoStartMinusEegStartSeconds?: number;
  videoDurationSeconds?: number | null;
  videoReviewHref?: string;
  videoMappedSegments?: VideoEegSync["mapped_segments"];
  videoClips?: DetectionJob[];
  onEegTimeSelect?: (seconds: number) => void;
}) {
  const showVideoTime =
    Number.isFinite(videoStartMinusEegStartSeconds) &&
    typeof videoDurationSeconds === "number" &&
    Number.isFinite(videoDurationSeconds);
  const sourceSeizureCount = events.filter(
    (event) => event.kind === "seizure_event",
  ).length;
  const manualCount = events.filter(
    (event) => event.kind === "manual_annotation",
  ).length;
  const otherCount = events.length - sourceSeizureCount - manualCount;

  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="eeg-annotations-heading"
    >
      <details>
        <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-7">
          <span>
            <span
              id="eeg-annotations-heading"
              className="block text-base font-bold"
            >
              Imported EEG markers
            </span>
            <span className="mt-1 block text-xs text-ink-muted">
              {events.length} markers · {sourceLabel(source)}
            </span>
          </span>
          <span className="text-xs font-semibold text-teal-dark">
            Source timestamps
          </span>
        </summary>
        <div className="border-t border-rule px-5 py-5 sm:px-7">
          <p className="mb-4 text-sm leading-6 text-ink-muted">
            Imported timestamps; separate from the model output.
          </p>
          {events.length === 0 ? (
            <p className="text-sm leading-6 text-ink-muted">
              No source event times were supplied.
            </p>
          ) : (
            <>
              {recordingDurationSeconds > 0 && (
                <>
                  <div
                    className="relative h-8 rounded-md bg-surface-soft"
                    role="img"
                    aria-label={`${events.length} source markers across a ${formatRelativeTime(recordingDurationSeconds)} EEG recording.`}
                  >
                    <span
                      className="absolute inset-x-2 top-1/2 h-0.5 -translate-y-1/2 bg-rule-strong"
                      aria-hidden="true"
                    />
                    {events.map((event, index) => {
                      const position = Math.min(
                        100,
                        Math.max(
                          0,
                          (event.onsetSeconds / recordingDurationSeconds) * 100,
                        ),
                      );
                      return (
                        <span
                          key={`${event.onsetSeconds}-${event.kind}-${index}`}
                          className={`absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface-soft ${markerTone(event)}`}
                          style={{ left: `${position}%` }}
                          title={`${eventLabel(event)} · EEG ${formatRelativeTime(event.onsetSeconds)}`}
                          aria-hidden="true"
                        />
                      );
                    })}
                  </div>
                  <div className="mt-1 flex justify-between font-mono text-[0.68rem] tabular-nums text-ink-muted">
                    <span>0:00</span>
                    <span>{formatRelativeTime(recordingDurationSeconds)}</span>
                  </div>
                  <ul
                    className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink-muted"
                    aria-label="Source marker types"
                  >
                    <MarkerLegend tone="bg-red" label="Source-tagged seizure" />
                    <MarkerLegend tone="bg-amber" label="Manual" />
                    <MarkerLegend tone="bg-teal-dark" label="Other" />
                  </ul>
                </>
              )}

              <details className="mt-4 border-t border-rule pt-3">
                <summary className="cursor-pointer text-sm font-semibold text-ink">
                  View marker times
                </summary>
                <ol className="mt-3 divide-y divide-rule border-t border-rule sm:grid sm:grid-cols-2 sm:divide-y-0">
                  {events.map((event, index) => {
                    const videoTime = videoMappedSegments
                      ? videoTimeForEegTime(
                          videoMappedSegments,
                          event.onsetSeconds,
                        )
                      : showVideoTime
                        ? event.onsetSeconds -
                          (videoStartMinusEegStartSeconds ?? 0)
                        : null;
                    const inVideoBounds =
                      videoTime !== null &&
                      videoTime >= 0 &&
                      videoTime <= (videoDurationSeconds ?? 0);
                    const linkedClip = videoClips?.find(
                      (job) =>
                        job.sync?.status === "linked" &&
                        videoTimeForEegTime(
                          job.sync.mapped_segments,
                          event.onsetSeconds,
                        ) !== null,
                    );
                    const linkedVideoTime = linkedClip?.sync
                      ? videoTimeForEegTime(
                          linkedClip.sync.mapped_segments,
                          event.onsetSeconds,
                        )
                      : null;
                    const videoAction =
                      linkedClip &&
                      linkedVideoTime !== null &&
                      onEegTimeSelect ? (
                        <button
                          className="shrink-0 self-center font-mono text-xs tabular-nums text-teal-dark underline underline-offset-2"
                          type="button"
                          onClick={() => onEegTimeSelect(event.onsetSeconds)}
                          aria-label={`Open Video ${String(videoClips!.indexOf(linkedClip) + 1).padStart(2, "0")} at ${formatRelativeTime(linkedVideoTime)}`}
                        >
                          Video {formatRelativeTime(linkedVideoTime)}
                        </button>
                      ) : videoMappedSegments !== undefined ? (
                        videoTime !== null && videoReviewHref ? (
                          <Link
                            className="shrink-0 self-center font-mono text-xs tabular-nums text-teal-dark underline underline-offset-2"
                            href={`${videoReviewHref}?time=${videoTime.toFixed(3)}`}
                            aria-label={`Open video at ${formatRelativeTime(videoTime)}`}
                          >
                            Video {formatRelativeTime(videoTime)}
                          </Link>
                        ) : (
                          <span className="shrink-0 self-center text-xs text-ink-muted">
                            Outside synchronized EEG coverage
                          </span>
                        )
                      ) : showVideoTime ? (
                        inVideoBounds &&
                        videoTime !== null &&
                        videoReviewHref ? (
                          <Link
                            className="shrink-0 self-center font-mono text-xs tabular-nums text-teal-dark underline underline-offset-2"
                            href={`${videoReviewHref}?time=${videoTime.toFixed(3)}`}
                            aria-label={`Open video at ${formatRelativeTime(videoTime)}`}
                          >
                            Video {formatRelativeTime(videoTime)}
                          </Link>
                        ) : (
                          <p className="shrink-0 self-center font-mono text-xs tabular-nums text-ink-muted">
                            {inVideoBounds && videoTime !== null
                              ? `Video ${formatRelativeTime(videoTime)}`
                              : "Outside video bounds"}
                          </p>
                        )
                      ) : videoClips?.length ? (
                        <span className="shrink-0 self-center text-xs text-ink-muted">
                          No linked clip at this time
                        </span>
                      ) : null;
                    return (
                      <li
                        className="flex min-w-0 items-start justify-between gap-3 border-rule px-3 py-3 text-sm [&:nth-child(odd)]:sm:border-r"
                        key={`${event.onsetSeconds}-${event.kind}-${index}`}
                      >
                        <div className="min-w-0">
                          <p className="font-semibold text-ink">
                            {eventLabel(event)}
                          </p>
                          <p className="mt-1 font-mono text-xs tabular-nums text-ink-muted">
                            EEG {formatRelativeTime(event.onsetSeconds)}
                            {event.durationSeconds > 0 &&
                              ` · duration ${formatRelativeTime(event.durationSeconds)}`}
                          </p>
                        </div>
                        {videoAction}
                      </li>
                    );
                  })}
                </ol>
              </details>
            </>
          )}
        </div>
      </details>
    </section>
  );
}

function MarkerLegend({ tone, label }: { tone: string; label: string }) {
  return (
    <li className="inline-flex items-center gap-2">
      <span className={`size-2 rounded-full ${tone}`} aria-hidden="true" />
      {label}
    </li>
  );
}

function markerTone(event: EegAnnotationEvent): string {
  if (event.kind === "seizure_event") return "bg-red";
  if (event.kind === "manual_annotation") return "bg-amber";
  return "bg-teal-dark";
}

function sourceLabel(source: EegAnnotationSource): string {
  if (source === "embedded-nicolet") return "Embedded Nicolet events";
  if (source === "reference") return "Imported reference events";
  if (source === "demo-fixture") return "Synthetic demo data";
  return "Source unavailable";
}

function eventLabel(event: EegAnnotationEvent): string {
  if (event.kind === "seizure_event") return "Source-tagged seizure marker";
  if (event.kind === "manual_annotation") return "Manual source marker";
  return "Other source marker";
}
