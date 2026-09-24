import type { EegAnnotationEvent, EegAnnotationSource } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format";

/** Display sanitized source event times without surfacing free-text annotations. */
export function EegAnnotationList({
  events,
  source,
  reviewRequired,
  videoStartMinusEegStartSeconds,
  videoDurationSeconds,
}: {
  events: EegAnnotationEvent[];
  source: EegAnnotationSource;
  reviewRequired: boolean;
  videoStartMinusEegStartSeconds?: number;
  videoDurationSeconds?: number | null;
}) {
  const showVideoTime =
    Number.isFinite(videoStartMinusEegStartSeconds) &&
    typeof videoDurationSeconds === "number" &&
    Number.isFinite(videoDurationSeconds);

  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="eeg-annotations-heading"
    >
      <div className="border-b border-rule px-5 py-5 sm:px-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="eeg-annotations-heading" className="text-base font-bold">
            Source EEG event markers
          </h2>
          <span className="rounded-full bg-surface-soft px-3 py-1 text-xs font-semibold text-ink-muted">
            {sourceLabel(source)}
          </span>
        </div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">
          Sanitized timestamps only. Source markers are not model outputs,
          verified ground truth, or a diagnosis.
        </p>
        {reviewRequired && (
          <p className="mt-1 text-sm font-semibold text-amber">
            Human review required
          </p>
        )}
      </div>
      {events.length === 0 ? (
        <p className="px-5 py-5 text-sm leading-6 text-ink-muted sm:px-7">
          No event times were supplied. This does not establish that no event
          occurred.
        </p>
      ) : (
        <ol className="divide-y divide-rule">
          {events.map((event, index) => {
            const videoTime = showVideoTime
              ? event.onsetSeconds - (videoStartMinusEegStartSeconds ?? 0)
              : null;
            const inVideoBounds =
              videoTime !== null &&
              videoTime >= 0 &&
              videoTime <= (videoDurationSeconds ?? 0);
            return (
              <li
                className="grid gap-2 px-5 py-4 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-7"
                key={`${event.onsetSeconds}-${event.kind}-${index}`}
              >
                <div>
                  <p className="font-semibold text-ink">
                    {eventLabel(event, source)}
                  </p>
                  <p className="mt-1 text-xs text-ink-muted">
                    EEG {formatRelativeTime(event.onsetSeconds)} · duration{" "}
                    {formatRelativeTime(event.durationSeconds)}
                  </p>
                </div>
                {showVideoTime && (
                  <p className="font-mono text-xs tabular-nums text-ink-muted">
                    {inVideoBounds && videoTime !== null
                      ? `Video ${formatRelativeTime(videoTime)}`
                      : "Outside video bounds"}
                  </p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function sourceLabel(source: EegAnnotationSource): string {
  if (source === "embedded-nicolet") return "Embedded Nicolet events";
  if (source === "reference") return "Imported reference events";
  if (source === "demo-fixture") return "Synthetic demo data";
  return "Source unavailable";
}

function eventLabel(
  event: EegAnnotationEvent,
  source: EegAnnotationSource,
): string {
  if (source === "demo-fixture") return "Synthetic demo marker";
  if (event.kind === "seizure_event") return "Source event marked seizure";
  if (event.kind === "manual_annotation") return "Manual source marker";
  return "Other source marker";
}
