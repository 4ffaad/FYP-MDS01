"use client";

import Link from "next/link";
import type { ProcessingAttempt, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { Progress } from "./ui/progress";

export type VideoPipelineProgressEntry = {
  index: number;
  status:
    | "pending"
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
  videoEnabled = true,
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
  videoEnabled?: boolean;
  caseId: string | null;
  error: string | null;
}) {
  const eegProgress = session?.progress;
  const hasUploadProgress = uploadPercent !== null;
  const eegTotal = eegProgress?.totalRecordings ?? eegCount;
  const eegPercent = eegProgress?.percent ?? uploadPercent ?? 0;
  const eegResolved = eegProgress
    ? eegProgress.completedRecordings + eegProgress.failedRecordings
    : ((uploadPercent ?? 0) / 100) * eegTotal;
  const videoResolved = videos.filter((video) =>
    ["complete", "failed", "expired", "not-submitted"].includes(video.status),
  ).length;
  const videoUploadProgress = videos.reduce(
    (total, video) =>
      total +
      (video.status === "uploading"
        ? Math.max(0, Math.min(100, video.uploadPercent)) / 100
        : 0),
    0,
  );
  const videoAttention = videos.filter((video) =>
    ["failed", "expired", "not-submitted", "unconfirmed"].includes(
      video.status,
    ),
  ).length;
  const videoInProgress = videos.filter((video) =>
    ["pending", "queued", "uploading", "processing"].includes(video.status),
  ).length;
  const activeVideo = videos.find((video) =>
    ["uploading", "queued", "processing"].includes(video.status),
  );
  const workTotal = eegTotal + videoCount;
  const overallResolved = Math.min(
    workTotal,
    eegResolved + videoResolved + videoUploadProgress,
  );
  const overallPercent = workTotal
    ? Math.round((overallResolved / workTotal) * 100)
    : 0;
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
        <div className="mt-5">
          <div className="flex items-center justify-between gap-3 text-xs font-semibold text-ink-muted">
            <span>Overall pipeline progress</span>
            <span className="tabular-nums">
              {Math.floor(overallResolved)} of {workTotal} items progressed
            </span>
          </div>
          <Progress
            className="progress-well mt-2 h-3 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal"
            aria-label="Overall EEG and video processing progress"
            value={overallPercent}
          />
          <p className="mt-1 text-right text-xs tabular-nums text-ink-faint">
            {overallPercent}% · uploaded or completed/requiring review
          </p>
        </div>
      </header>

      <div
        className={`grid items-start gap-5 ${videoEnabled ? "lg:grid-cols-2" : "lg:grid-cols-1"}`}
      >
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
              ? `${eegProgress.completedRecordings} of ${eegTotal} EEG recordings complete`
              : hasUploadProgress
                ? `${eegCount} EEG recordings · ${Math.round(eegPercent)}% of archive uploaded`
                : `${eegCount} EEG recordings · Waiting for measured upload progress`}
          </p>
          {(eegProgress || hasUploadProgress) && (
            <>
              <Progress
                className="progress-well mt-3 h-2 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal"
                aria-label="EEG processing progress"
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
              Stage: {eegStageLabel(session.currentStage)}
            </p>
          )}
          {eegProgress?.failedRecordings ? (
            <p className="mt-3 rounded-lg bg-amber-soft/50 px-3 py-2 text-xs leading-5 text-ink-muted">
              One or more EEG recordings did not complete. The valid recordings
              are retained for review; open this patient review for the
              per-recording results.
            </p>
          ) : null}
          {session && session.processingAttempts.length > 0 ? (
            <details className="mt-4 border-t border-rule pt-3">
              <summary className="cursor-pointer text-sm font-semibold text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal">
                Show EEG processing stages · {session.processingAttempts.length}{" "}
                recorded
              </summary>
              <ol className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
                {session.processingAttempts.map((attempt, index) => (
                  <li
                    key={`${attempt.recordingSequenceIndex ?? "archive"}-${attempt.stage}-${index}`}
                    className="flex items-start justify-between gap-3 rounded-lg bg-surface-soft px-3 py-2 text-xs"
                  >
                    <span className="min-w-0">
                      <strong className="block text-ink">
                        {attempt.recordingSequenceIndex
                          ? `Recording ${String(attempt.recordingSequenceIndex).padStart(2, "0")}`
                          : "EEG archive"}
                        {" · "}
                        {eegStageLabel(attempt.stage)}
                      </strong>
                      <span className="text-ink-muted">
                        {attemptDuration(attempt)}
                      </span>
                    </span>
                    <span
                      className={`shrink-0 font-semibold ${attempt.status === "failed" ? "text-red" : attempt.status === "succeeded" ? "text-teal-dark" : "text-ink-muted"}`}
                    >
                      {attempt.status.replaceAll("_", " ")}
                    </span>
                  </li>
                ))}
              </ol>
            </details>
          ) : null}
        </section>

        {videoEnabled && (
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
                {videos.filter((video) => video.status === "complete").length}{" "}
                of {videoCount} complete
              </span>
            </div>
            <p className="mt-3 text-xs leading-5 text-ink-muted">
              Video jobs are submitted as soon as the patient case is created
              and run independently from EEG. The service processes one clip at
              a time; this page submits more as capacity opens.
            </p>
            {activeVideo && (
              <div
                className="mt-4 rounded-xl bg-surface-soft px-4 py-3"
                role="status"
                aria-live="polite"
              >
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-semibold text-ink">
                    Video {activeVideo.index + 1}
                  </span>
                  <span className="text-xs text-ink-muted">
                    {videoStatusLabel(activeVideo.status, activeVideo.stage)}
                  </span>
                </div>
                {activeVideo.status === "uploading" ? (
                  <>
                    <Progress
                      className="progress-well mt-2 h-2 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal"
                      aria-label={`Video ${activeVideo.index + 1} upload progress`}
                      value={Math.max(
                        0,
                        Math.min(100, activeVideo.uploadPercent),
                      )}
                    />
                    <p className="mt-1 text-right text-xs tabular-nums text-ink-faint">
                      {Math.round(activeVideo.uploadPercent)}% uploaded
                    </p>
                  </>
                ) : null}
              </div>
            )}
            {videoCount === 0 ? (
              <p className="mt-4 text-sm text-ink-muted">
                No video clips were selected.
              </p>
            ) : (
              <details className="mt-4" open={videoCount <= 5}>
                <summary className="cursor-pointer rounded-xl bg-surface-soft px-4 py-3 text-sm font-semibold text-ink shadow-hard-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal">
                  Show {videoCount} video clips ·{" "}
                  {videos.filter((video) => video.status === "complete").length}{" "}
                  complete · {videoInProgress} in progress · {videoAttention}{" "}
                  {videoAttention === 1 ? "needs" : "need"} attention
                </summary>
                <ol className="mt-3 max-h-96 space-y-3 overflow-y-auto pr-1">
                  {videos.map((video) => {
                    const label = videoStatusLabel(video.status, video.stage);
                    return (
                      <li
                        key={video.index}
                        className="border-t border-rule pt-3"
                      >
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
                            <Progress
                              className="progress-well mt-2 h-2 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal"
                              aria-label={`Video ${video.index + 1} upload progress`}
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
              </details>
            )}
          </section>
        )}
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
              ? "Open patient review to check status"
              : "Open patient review"}{" "}
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
  if (status === "pending") return "Pending upload";
  if (status === "uploading") return "Uploading";
  if (status === "processing") return stage ? stageLabel(stage) : "Processing";
  if (status === "complete") return "Complete";
  if (status === "failed") return "Failed";
  if (status === "expired") return "Expired";
  if (status === "not-submitted") return "Not submitted";
  if (status === "unconfirmed") return "Status unconfirmed";
  if (status === "queued") return "Queued by service";
  return "Queued";
}

function eegStageLabel(stage: string) {
  switch (stage) {
    case "validation":
      return "Validate archive";
    case "deidentification":
      return "Scrub EEG metadata";
    case "preprocessing":
      return "Prepare model input";
    case "inference":
      return "Run H5 model";
    case "explainability":
      return "Generate explanation";
    default:
      return stage.replaceAll("_", " ");
  }
}

function attemptDuration(attempt: ProcessingAttempt) {
  if (!attempt.startedAt) return "Waiting to start";
  const started = Date.parse(attempt.startedAt);
  const finished = attempt.finishedAt
    ? Date.parse(attempt.finishedAt)
    : Date.now();
  if (!Number.isFinite(started) || !Number.isFinite(finished))
    return "Timing unavailable";
  return `${Math.max(0, (finished - started) / 1000).toFixed(1)} sec`;
}

function stageLabel(stage: string) {
  switch (stage) {
    case "normalization":
      return "Preparing video";
    case "preflight":
      return "Checking video";
    case "privacy-transform":
      return "Privacy transform";
    case "pose-and-inference":
      return "OpenPose and VSViG";
    case "complete":
      return "Complete";
    case "failed":
      return "Failed";
    default:
      return stage.replaceAll("_", " ").replaceAll("-", " ");
  }
}
