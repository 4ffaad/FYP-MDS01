"use client";

import Link from "next/link";
import type { Session } from "@/lib/types";
import { Icon } from "./Icon";

export type VideoPipelineProgressEntry = {
  index: number;
  status:
    | "queued"
    | "uploading"
    | "processing"
    | "complete"
    | "failed"
    | "expired"
    | "not-submitted"
    | "unconfirmed";
  uploadPercent: number;
  stage: string | null;
  error: string | null;
};

export function PatientProcessingProgress({
  session,
  eegCount,
  uploadPercent,
  step,
  videos,
  videoCount,
  busy,
  finished,
  caseId,
  error,
}: {
  session: Session | null;
  eegCount: number;
  uploadPercent: number | null;
  step: string;
  videos: VideoPipelineProgressEntry[];
  videoCount: number;
  busy: boolean;
  finished: boolean;
  caseId: string | null;
  error: string | null;
}) {
  const eegProgress = session?.progress;
  const hasUploadProgress = uploadPercent !== null;
  const eegPercent = eegProgress?.percent ?? uploadPercent ?? 0;
  const hasIssues =
    session?.status === "failed" ||
    session?.status === "completed_with_errors" ||
    (eegProgress?.failedRecordings ?? 0) > 0 ||
    videos.some((video) =>
      ["failed", "expired", "not-submitted"].includes(video.status),
    );
  const hasUnconfirmedVideo = videos.some(
    (video) => video.status === "unconfirmed",
  );
  const title = finished
    ? hasIssues
      ? "Processing finished with issues"
      : "Processing complete"
    : "Processing patient review";

  return (
    <section
      className="mt-6 space-y-5"
      aria-label="Patient processing progress"
    >
      <header className="panel border-l-4 border-teal bg-teal-soft/30 p-5 sm:p-6">
        <p className="eyebrow">Patient review</p>
        <h2
          id="patient-processing-heading"
          tabIndex={-1}
          className="mt-2 scroll-mt-24 text-xl font-semibold tracking-tight text-ink focus:outline-none"
        >
          {title}
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted" role="status">
          {busy
            ? step
            : finished
              ? "All submitted processing jobs reached a terminal status."
              : step}
        </p>
        <p className="mt-2 text-xs leading-5 text-ink-muted">
          Research-only outputs. Video stage labels report service status, not
          progress, confidence, or diagnosis.
        </p>
      </header>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="eeg-progress-heading"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">EEG</p>
              <h3
                id="eeg-progress-heading"
                className="mt-1 text-base font-bold"
              >
                Recording analysis
              </h3>
            </div>
            <span className="rounded-full bg-surface-soft px-3 py-1 text-xs font-semibold text-ink-muted">
              {session
                ? session.status.replaceAll("_", " ")
                : hasUploadProgress
                  ? "Uploading"
                  : "Preparing"}
            </span>
          </div>
          <p className="mt-3 text-sm text-ink-muted">
            {eegProgress
              ? `${eegProgress.completedRecordings} of ${eegCount} EEG recordings complete`
              : hasUploadProgress
                ? `${eegCount} EEG recordings · ${Math.round(eegPercent)}% of archive uploaded`
                : `${eegCount} EEG recordings · Waiting for measured upload progress`}
          </p>
          {(eegProgress || hasUploadProgress) && (
            <>
              <progress
                className="mt-3 h-2 w-full accent-teal"
                aria-label="EEG processing progress"
                max={100}
                value={Math.max(0, Math.min(100, eegPercent))}
              />
              <div className="mt-2 flex justify-between text-xs tabular-nums text-ink-muted">
                <span>
                  {eegProgress
                    ? `${eegPercent}% resolved`
                    : `${eegPercent}% uploaded`}
                </span>
                {eegProgress?.failedRecordings ? (
                  <span className="text-amber">
                    {eegProgress.failedRecordings} need attention
                  </span>
                ) : null}
              </div>
            </>
          )}
          {session?.currentStage && !finished && (
            <p className="mt-3 text-xs text-ink-muted">
              Stage: {session.currentStage.replaceAll("_", " ")}
            </p>
          )}
          {eegProgress?.failedRecordings ? (
            <p className="mt-3 rounded-lg bg-amber-soft/50 px-3 py-2 text-xs leading-5 text-ink-muted">
              One or more EEG recordings did not complete. The valid recordings
              are retained for review; check Patient History for the
              per-recording result.
            </p>
          ) : null}
        </section>

        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="video-progress-heading"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Video</p>
              <h3
                id="video-progress-heading"
                className="mt-1 text-base font-bold"
              >
                Video processing
              </h3>
            </div>
            <span className="rounded-full bg-surface-soft px-3 py-1 text-xs font-semibold text-ink-muted">
              {videos.filter((video) => video.status === "complete").length} of{" "}
              {videoCount} complete
            </span>
          </div>
          <p className="mt-3 text-xs leading-5 text-ink-muted">
            Clips run one at a time after EEG processing to limit resource
            contention. Upload progress is measured; subsequent stages are shown
            as service status only.
          </p>
          {videoCount === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">
              No video clips were selected.
            </p>
          ) : (
            <ol className="mt-4 space-y-4">
              {videos.map((video) => {
                const label =
                  video.status === "queued" &&
                  (!session ||
                    !["completed", "completed_with_errors", "failed"].includes(
                      session.status,
                    ))
                    ? "Waiting for EEG"
                    : videoStatusLabel(video.status, video.stage);
                return (
                  <li key={video.index} className="border-t border-rule pt-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-ink">
                        Video {video.index + 1}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1.5 text-xs font-semibold ${["failed", "expired", "not-submitted"].includes(video.status) ? "text-red" : video.status === "complete" ? "text-teal-dark" : "text-ink-muted"}`}
                      >
                        {video.status === "complete" ? (
                          <Icon name="check" className="size-3.5" />
                        ) : ["failed", "expired", "not-submitted"].includes(
                            video.status,
                          ) ? (
                          <Icon name="alert" className="size-3.5" />
                        ) : null}
                        {label}
                      </span>
                    </div>
                    {video.status === "uploading" ? (
                      <>
                        <progress
                          className="mt-2 h-2 w-full accent-teal"
                          aria-label={`Video ${video.index + 1} upload progress`}
                          max={100}
                          value={Math.max(
                            0,
                            Math.min(100, video.uploadPercent),
                          )}
                        />
                        <p className="mt-1 text-right text-[0.68rem] tabular-nums text-ink-faint">
                          {Math.round(video.uploadPercent)}% uploaded
                        </p>
                      </>
                    ) : null}
                    {video.error ? (
                      <p
                        className="mt-2 rounded-lg bg-red-soft/60 px-3 py-2 text-xs leading-5 text-ink-muted"
                        role="alert"
                      >
                        {video.error}
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>

      {error ? (
        <div
          className="rounded-xl border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {caseId && (finished || hasUnconfirmedVideo) ? (
        <div className="flex justify-end border-t border-rule pt-5">
          <Link
            href={`/cases/${encodeURIComponent(caseId)}`}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-teal px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2"
          >
            {hasUnconfirmedVideo
              ? "Open Patient History to check status"
              : "Open patient history"}{" "}
            <Icon name="arrow" className="size-4" />
          </Link>
        </div>
      ) : null}
    </section>
  );
}

function videoStatusLabel(
  status: VideoPipelineProgressEntry["status"],
  stage: string | null,
) {
  if (status === "uploading") return "Uploading";
  if (status === "processing") return stage ? stageLabel(stage) : "Processing";
  if (status === "complete") return "Complete";
  if (status === "failed") return "Failed";
  if (status === "expired") return "Expired";
  if (status === "not-submitted") return "Not submitted";
  if (status === "unconfirmed") return "Status unconfirmed";
  return "Queued";
}

function stageLabel(stage: string) {
  switch (stage) {
    case "preflight":
      return "Checking video";
    case "privacy-transform":
      return "Privacy transform";
    case "pose-and-inference":
      return "Pose and VSViG";
    case "complete":
      return "Complete";
    case "failed":
      return "Failed";
    default:
      return stage.replaceAll("_", " ").replaceAll("-", " ");
  }
}
