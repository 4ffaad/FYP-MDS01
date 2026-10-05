import type { DetectionJob } from "@/lib/video-detection";

/** Account for same-case clips without exposing their source filenames. */
export function VideoSyncInventory({
  jobs,
  recordId,
}: {
  jobs: DetectionJob[];
  recordId: string;
}) {
  if (jobs.length === 0) return null;

  const linkedHere = jobs.filter(
    (job) => job.sync?.status === "linked" && job.sync.record_id === recordId,
  ).length;
  const linkedElsewhere = jobs.filter(
    (job) => job.sync?.status === "linked" && job.sync.record_id !== recordId,
  ).length;
  const waiting = jobs.filter((job) => job.sync?.status === "pending").length;
  const unresolved = jobs.length - linkedHere - linkedElsewhere - waiting;

  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="video-sync-inventory-heading"
    >
      <details open={jobs.length <= 8}>
        <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-7">
          <span>
            <span
              id="video-sync-inventory-heading"
              className="block text-base font-bold"
            >
              Video synchronization status
            </span>
            <span className="mt-1 block text-xs text-ink-muted">
              {jobs.length} clips · {linkedHere} linked here · {linkedElsewhere}{" "}
              linked to another EEG · {unresolved} unresolved · {waiting}{" "}
              waiting
            </span>
          </span>
          <span className="text-xs font-semibold text-teal-dark">
            Clip outcomes
          </span>
        </summary>

        <div className="border-t border-rule px-5 py-5 sm:px-7">
          <p className="mb-4 text-sm leading-6 text-ink-muted">
            Clips link only when their supplied filename token, frame data, and
            clock anchors produce one unique match. Unresolved clips stay
            separate.
          </p>
          <ol className="divide-y divide-rule">
            {jobs.map((job, index) => (
              <li
                key={job.job_id}
                className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,0.8fr)] sm:items-center"
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-ink">
                    Video {String(index + 1).padStart(2, "0")}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-ink-muted">
                    {syncStatus(job, recordId)}
                  </p>
                </div>
                <p className="text-xs leading-5 text-ink-muted">
                  {processingStatus(job)}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </details>
    </section>
  );
}

function syncStatus(job: DetectionJob, recordId: string): string {
  const sync = job.sync;
  if (!sync) return "Sync status unavailable";
  if (sync.status === "linked")
    return sync.record_id === recordId
      ? "Linked to this EEG"
      : "Linked to another EEG recording";
  if (sync.status === "pending") return "Waiting for sync metadata";
  if (sync.status === "unmatched") return "No unique metadata match";
  if (sync.status === "ambiguous") return "More than one metadata match";
  return "Sync data unavailable";
}

function processingStatus(job: DetectionJob): string {
  if (job.status === "ready") return "VSViG score available";
  if (job.status === "expired") return "Expired · no retained result";
  if (job.status === "queued") return "Queued for processing";
  if (job.status === "processing") return "Video processing";
  if (job.video_available) return "Protected review available · no VSViG score";
  return "Processing failed · no protected review";
}
