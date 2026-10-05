"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPatientProfile, getResult } from "@/lib/api";
import {
  getDetectionResults,
  type DetectionJob,
  type DetectionResult,
  type VideoEegSync,
} from "@/lib/video-detection";
import { formatRelativeTime } from "@/lib/format";
import { reportDetails } from "@/lib/patient-profile-privacy";
import type { AnalysisResult, PatientProfile, Session } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EegAnnotationList } from "./EegAnnotationList";

const READY_RECORDING_STATUSES = new Set(["inferred"]);
type LoadedEegResult =
  | { recordId: string; status: "ready"; result: AnalysisResult }
  | { recordId: string; status: "error" };
type LoadedVideoResult =
  | { jobId: string; status: "ready"; result: DetectionResult }
  | { jobId: string; status: "error" };
type LoadedPatientProfile =
  | { caseId: string; status: "ready"; profile: PatientProfile | null }
  | { caseId: string; status: "error" };
/** Compose independently authorized modality results into a local print view. */
export function CombinedReviewReport({
  session,
  videoJob,
  hasEegLink,
  hasVideoLink,
}: {
  session: Session | null;
  videoJob: DetectionJob | null;
  hasEegLink: boolean;
  hasVideoLink: boolean;
}) {
  const readyRecordings =
    session?.recordings.filter((recording) =>
      READY_RECORDING_STATUSES.has(recording.status),
    ) ?? [];
  const readyRecordIds = readyRecordings.map((recording) => recording.recordId);
  const terminalSessionWithoutInference =
    session &&
    readyRecordings.length === 0 &&
    ["completed", "completed_with_errors", "failed"].includes(session.status)
      ? session
      : null;
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [eegLoad, setEegLoad] = useState<LoadedEegResult | null>(null);
  const [videoLoad, setVideoLoad] = useState<LoadedVideoResult | null>(null);
  const [profileLoad, setProfileLoad] = useState<LoadedPatientProfile | null>(
    null,
  );
  const sync = videoJob?.sync;
  const linkedRecordId = sync?.status === "linked" ? sync.record_id : null;
  const effectiveRecordId =
    sync?.status === "linked"
      ? linkedRecordId && readyRecordIds.includes(linkedRecordId)
        ? linkedRecordId
        : ""
      : readyRecordIds.includes(selectedRecordId)
        ? selectedRecordId
        : readyRecordIds.length === 1
          ? readyRecordIds[0]
          : "";
  const linkedRecording = session?.recordings.find(
    (recording) => recording.recordId === linkedRecordId,
  );
  const pairedForSync = Boolean(
    hasEegLink &&
      hasVideoLink &&
      sync?.status === "linked" &&
      linkedRecordId &&
      effectiveRecordId === linkedRecordId &&
      session?.caseId === videoJob?.case_id,
  );
  const verifiedSourceOffset =
    pairedForSync &&
    typeof sync?.eeg_source_start_seconds === "number" &&
    Number.isFinite(sync.eeg_source_start_seconds)
      ? sync.eeg_source_start_seconds
      : null;
  const partialSyncCoverage = Boolean(
    pairedForSync &&
      sync?.video_duration_seconds !== null &&
      sync?.video_duration_seconds !== undefined &&
      sync.eeg_coverage_seconds !== null &&
      sync.eeg_coverage_seconds !== undefined &&
      sync.eeg_coverage_seconds + 0.5 < sync.video_duration_seconds,
  );
  const activeVideoJobId = videoJob?.status === "ready" ? videoJob.job_id : "";
  const sessionCaseId = hasEegLink ? session?.caseId : null;
  const videoCaseId = hasVideoLink ? videoJob?.case_id : null;
  const profileCaseId =
    sessionCaseId && videoCaseId && sessionCaseId !== videoCaseId
      ? ""
      : (sessionCaseId ?? videoCaseId ?? "");

  useEffect(() => {
    if (!profileCaseId) return;
    const controller = new AbortController();
    void getPatientProfile(profileCaseId, controller.signal)
      .then((profile) => {
        if (!controller.signal.aborted)
          setProfileLoad({ caseId: profileCaseId, status: "ready", profile });
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setProfileLoad({ caseId: profileCaseId, status: "error" });
      });
    return () => controller.abort();
  }, [profileCaseId]);

  useEffect(() => {
    if (!effectiveRecordId) return;
    const controller = new AbortController();
    void getResult(effectiveRecordId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted)
          setEegLoad({
            recordId: effectiveRecordId,
            status: "ready",
            result,
          });
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setEegLoad({ recordId: effectiveRecordId, status: "error" });
      });
    return () => controller.abort();
  }, [effectiveRecordId]);

  useEffect(() => {
    if (!activeVideoJobId) return;
    const controller = new AbortController();
    void getDetectionResults(activeVideoJobId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted)
          setVideoLoad({
            jobId: activeVideoJobId,
            status: "ready",
            result,
          });
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setVideoLoad({ jobId: activeVideoJobId, status: "error" });
      });
    return () => controller.abort();
  }, [activeVideoJobId]);

  const currentEegLoad =
    eegLoad?.recordId === effectiveRecordId ? eegLoad : null;
  const eegResult =
    currentEegLoad?.status === "ready" ? currentEegLoad.result : null;
  const eegError = currentEegLoad?.status === "error";
  const currentVideoLoad =
    videoLoad?.jobId === activeVideoJobId ? videoLoad : null;
  const videoResult =
    currentVideoLoad?.status === "ready" ? currentVideoLoad.result : null;
  const videoError = currentVideoLoad?.status === "error";
  const currentProfileLoad =
    profileLoad?.caseId === profileCaseId ? profileLoad : null;
  const printablePatientDetails =
    currentProfileLoad?.status === "ready" && currentProfileLoad.profile
      ? Object.values(reportDetails(currentProfileLoad.profile)).flat()
      : [];

  const videoDurationSeconds =
    videoResult?.duration_seconds ?? videoJob?.duration_seconds ?? null;

  return (
    <section
      className="mt-8 space-y-5"
      id="combined-review-report"
      aria-labelledby="combined-review-heading"
    >
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-4">
        <div>
          <p className="eyebrow">Review output</p>
          <h2
            id="combined-review-heading"
            className="mt-2 text-2xl font-semibold tracking-[-0.04em]"
          >
            EEG and video review
          </h2>
        </div>
        <Button
          className="no-print"
          variant="outline"
          onClick={() => window.print()}
        >
          Print / Save as PDF
        </Button>
      </div>

      {hasVideoLink && (
        <section
          className={`rounded-xl border p-4 sm:p-5 ${pairedForSync ? "border-teal/35 bg-teal-soft/40" : "border-amber/40 bg-amber-soft"}`}
          aria-live="polite"
        >
          <h3 className="text-sm font-bold">
            {pairedForSync
              ? "Unique metadata match among uploaded clips"
              : sync?.status === "pending"
                ? "Checking Nicolet video synchronization"
                : sync?.status === "ambiguous"
                  ? "Video synchronization is ambiguous"
                  : "No verified EEG/video link"}
          </h3>
          {pairedForSync ? (
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              The sync-table filename, frame counts, and timestamp anchors
              uniquely match the uploaded clips for{" "}
              {linkedRecording?.displayName ?? "this EEG"}. The first aligned
              frame is at EEG time{" "}
              {formatRelativeTime(sync?.eeg_source_start_seconds ?? 0)}. This is
              a metadata match; it does not prove the uploaded video bytes are
              the original acquisition.
              {partialSyncCoverage &&
                ` Only ${formatRelativeTime(sync?.eeg_coverage_seconds ?? 0)} of ${formatRelativeTime(sync?.video_duration_seconds ?? 0)} is covered by EEG signal; footage outside EEG segments is omitted from the aligned timeline.`}
            </p>
          ) : (
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              {sync?.status === "pending"
                ? "Waiting for EEG processing or the video folder upload to finish."
                : "The source metadata did not establish one unique recording and camera stream. EEG and video remain separate."}
            </p>
          )}
        </section>
      )}

      {printablePatientDetails.length > 0 && (
        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="patient-details-heading"
        >
          <p className="eyebrow">Patient details · owner-only</p>
          <h3 id="patient-details-heading" className="mt-2 text-base font-bold">
            Patient details
          </h3>
          <dl className="mt-4 grid gap-4 sm:grid-cols-2">
            {printablePatientDetails.map((detail, index) => (
              <div
                key={`${detail.label}-${index}`}
                className={detail.value.length > 180 ? "sm:col-span-2" : ""}
              >
                <dt className="text-xs text-ink-muted">{detail.label}</dt>
                <dd className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-ink">
                  {detail.value}
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-xs leading-5 text-ink-muted">
            Only opted-in, privacy-safe report details are included here.
            Identifiers are omitted; EEG and video results remain separate.
          </p>
        </section>
      )}
      {currentProfileLoad?.status === "error" && (
        <p
          className="rounded-lg border border-amber/30 bg-amber-soft p-3 text-sm text-amber"
          role="status"
        >
          Patient details could not be loaded. EEG and video summaries remain
          available.
        </p>
      )}

      {hasEegLink && (
        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="eeg-evidence-heading"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 id="eeg-evidence-heading" className="text-base font-bold">
                EEG model output
              </h3>
              <p className="mt-1 text-sm leading-6 text-ink-muted">
                Window scores, threshold, and model sensitivity.
              </p>
            </div>
            {readyRecordings.length > 1 && (
              <label className="no-print block min-w-52 text-xs font-semibold">
                EEG recording
                <select
                  className="mt-1 block min-h-10 w-full rounded-lg border border-rule bg-white px-3 text-sm text-ink"
                  value={effectiveRecordId}
                  onChange={(event) => setSelectedRecordId(event.target.value)}
                >
                  <option value="">Select a completed recording</option>
                  {readyRecordings.map((recording) => (
                    <option key={recording.recordId} value={recording.recordId}>
                      {recording.displayName}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {eegError ? (
            <p className="mt-4 text-sm text-red" role="status">
              EEG result details are unavailable. Open the session to retry.
            </p>
          ) : eegResult ? (
            <>
              <Link
                className="mt-4 inline-flex text-sm font-semibold text-teal-dark underline underline-offset-4"
                href={`/results/${encodeURIComponent(eegResult.recordId)}`}
              >
                Open EEG timeline and explanation
              </Link>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <ReportValue
                  label="Model"
                  value={`${eegResult.modelName} · ${eegResult.modelVersion}`}
                />
                <ReportValue
                  label="Window scores flagged"
                  value={`${eegResult.flaggedWindowCount} / ${eegResult.windowCount}`}
                />
                <ReportValue
                  label="Score meaning"
                  value={
                    eegResult.scoreType === "calibrated_probability"
                      ? "Calibrated window estimate"
                      : "Development / uncalibrated score"
                  }
                />
                <ReportValue
                  label="Recording probability"
                  value={
                    eegResult.recordingProbabilityAvailable
                      ? "Available"
                      : "Not available"
                  }
                />
              </dl>
              <div className="mt-5 border-t border-rule pt-4">
                <h4 className="text-xs font-bold uppercase tracking-[0.08em] text-ink-muted">
                  Threshold-crossing intervals
                </h4>
                {eegResult.alertIntervals.length > 0 ? (
                  <ol className="mt-2 flex flex-wrap gap-2">
                    {eegResult.alertIntervals.slice(0, 12).map((interval) => (
                      <li
                        key={`${interval.startSeconds}-${interval.endSeconds}`}
                        className="rounded-lg bg-surface-soft px-3 py-2 font-mono text-xs tabular-nums"
                      >
                        {formatRelativeTime(interval.startSeconds)}–
                        {formatRelativeTime(interval.endSeconds)}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-ink-muted">
                    No threshold-crossing intervals were returned.
                  </p>
                )}
              </div>
              <div className="mt-5 border-t border-rule pt-4">
                <h4 className="text-xs font-bold uppercase tracking-[0.08em] text-ink-muted">
                  EEG attribution evidence
                </h4>
                {eegResult.researchAttributions.length > 0 ? (
                  <p className="mt-2 text-sm leading-6 text-ink-muted">
                    {eegResult.researchAttributions.length} model-specific
                    sensitivity artifact(s) available. These are not clinical
                    explanations or causal evidence.
                  </p>
                ) : (
                  <p className="mt-2 text-sm leading-6 text-ink-muted">
                    No attribution artifact is available for this runtime. The
                    score timeline alone does not explain why a score changed.
                  </p>
                )}
              </div>
            </>
          ) : terminalSessionWithoutInference ? (
            <p className="mt-4 text-sm text-ink-muted" role="status">
              EEG processing ended without an inferred recording.{" "}
              <Link
                className="font-semibold text-teal-dark underline underline-offset-4"
                href={`/sessions/${encodeURIComponent(terminalSessionWithoutInference.sessionId)}`}
              >
                Open session details
              </Link>{" "}
              to review its processing status.
            </p>
          ) : readyRecordings.length === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">
              Waiting for a completed EEG recording.
            </p>
          ) : effectiveRecordId ? (
            <p className="mt-4 text-sm text-ink-muted" role="status">
              Loading EEG result details…
            </p>
          ) : pairedForSync && linkedRecording ? (
            <p className="mt-4 text-sm text-ink-muted" role="status">
              This video is linked to {linkedRecording.displayName}, whose EEG
              status is {linkedRecording.status}. No completed EEG model result
              is available for that recording.
            </p>
          ) : (
            <p className="mt-4 text-sm text-ink-muted">
              Select one completed recording to include its result.
            </p>
          )}
        </section>
      )}

      {eegResult && (
        <EegAnnotationList
          events={eegResult.annotationEvents}
          source={eegResult.annotationSource}
          recordingDurationSeconds={eegResult.recordingDurationSeconds}
          videoMappedSegments={
            pairedForSync ? sync?.mapped_segments : undefined
          }
          videoDurationSeconds={pairedForSync ? videoDurationSeconds : null}
          videoReviewHref={
            pairedForSync && videoJob
              ? `/video-detection/${encodeURIComponent(videoJob.job_id)}`
              : undefined
          }
        />
      )}

      {hasVideoLink && (
        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="video-evidence-heading"
        >
          <div>
            <h3 id="video-evidence-heading" className="text-base font-bold">
              Video model output
            </h3>
            <p className="mt-1 text-sm leading-6 text-ink-muted">
              Uncalibrated model scores and movement sensitivity.
            </p>
            {videoJob?.job_id && (
              <Link
                className="mt-4 inline-flex text-sm font-semibold text-teal-dark underline underline-offset-4"
                href={`/video-detection/${encodeURIComponent(videoJob.job_id)}`}
              >
                Open video timeline and protected player
              </Link>
            )}
          </div>
          {videoError ? (
            <p className="mt-4 text-sm text-red" role="status">
              Video result details are unavailable. Open the video job to retry.
            </p>
          ) : videoResult ? (
            <>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <ReportValue
                  label="Model"
                  value={`${videoResult.model.model_name} · ${videoResult.model.model_version}`}
                />
                <ReportValue
                  label="Score calibration"
                  value="Uncalibrated · not a probability"
                />
                <ReportValue
                  label="VSViG model-input blur"
                  value={
                    typeof videoResult.privacy?.blur_strength_percent ===
                    "number"
                      ? `${videoResult.privacy.blur_strength_percent}% of default strength`
                      : "Not reported"
                  }
                />
                <ReportValue
                  label="Threshold-crossing windows"
                  value={String(
                    videoResult.predictions.filter(
                      (item) => item.seizure_detected,
                    ).length,
                  )}
                />
                <ReportValue
                  label="Face-redacted video"
                  value={videoRedactionSummary(videoResult)}
                />
              </dl>
              {videoResult.privacy?.model_input_adaptation === "letterbox" && (
                <p className="mt-4 rounded-lg border border-amber/40 bg-amber-soft px-3 py-2 text-sm text-amber">
                  Experimental letterbox adaptation was used. Its scores have
                  not been validated as equivalent to native-resolution input;
                  keep this result separate when evaluating the model.
                </p>
              )}
              <div className="mt-5 border-t border-rule pt-4">
                <h4 className="text-xs font-bold uppercase tracking-[0.08em] text-ink-muted">
                  Threshold-crossing intervals
                </h4>
                {videoResult.intervals.length > 0 ? (
                  <ol className="mt-2 space-y-2">
                    {videoResult.intervals
                      .slice(0, 12)
                      .map((interval, index) => (
                        <li
                          className="flex flex-wrap justify-between gap-x-4 gap-y-1 rounded-lg bg-surface-soft px-3 py-2 text-sm"
                          key={`${interval.start_time}-${interval.end_time}-${index}`}
                        >
                          {pairedForSync && videoJob ? (
                            <Link
                              className="font-mono tabular-nums text-teal-dark underline underline-offset-2"
                              href={`/video-detection/${encodeURIComponent(videoJob.job_id)}?time=${interval.start_time.toFixed(3)}`}
                            >
                              Video {formatRelativeTime(interval.start_time)}–
                              {formatRelativeTime(interval.end_time)}
                            </Link>
                          ) : (
                            <span className="font-mono tabular-nums">
                              Video {formatRelativeTime(interval.start_time)}–
                              {formatRelativeTime(interval.end_time)}
                            </span>
                          )}
                          {pairedForSync && verifiedSourceOffset !== null && (
                            <span className="font-mono text-xs tabular-nums text-ink-muted">
                              EEG source clock{" "}
                              {formatRelativeTime(
                                interval.start_time + verifiedSourceOffset,
                              )}
                              –
                              {formatRelativeTime(
                                interval.end_time + verifiedSourceOffset,
                              )}
                            </span>
                          )}
                        </li>
                      ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-ink-muted">
                    No threshold-crossing intervals were returned.
                  </p>
                )}
              </div>
              <div className="mt-5 border-t border-rule pt-4">
                <h4 className="text-xs font-bold uppercase tracking-[0.08em] text-ink-muted">
                  Video Grad-CAM evidence
                </h4>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {videoEvidenceSummary(videoResult)}
                </p>
              </div>
            </>
          ) : videoJob?.status === "failed" ||
            videoJob?.status === "expired" ? (
            <p className="mt-4 text-sm text-ink-muted">
              {videoJob.video_available
                ? "This clip has no VSViG score. Its privacy-safe video remains available for synchronized visual review."
                : "No video inference result or privacy-safe review copy is available for this clip."}
            </p>
          ) : videoJob?.status === "ready" ? (
            <p className="mt-4 text-sm text-ink-muted" role="status">
              Loading video result details…
            </p>
          ) : (
            <p className="mt-4 text-sm text-ink-muted">
              Waiting for video processing to finish.
            </p>
          )}
        </section>
      )}

      {pairedForSync && eegResult && videoResult && sync?.mapped_segments && (
        <PairedModelTimeline
          eegResult={eegResult}
          videoResult={videoResult}
          mappedSegments={sync.mapped_segments}
          eegResultHref={`/results/${encodeURIComponent(eegResult.recordId)}`}
          videoResultHref={`/video-detection/${encodeURIComponent(activeVideoJobId)}`}
        />
      )}

      <p className="text-xs leading-5 text-ink-muted">
        Research output · not a diagnosis · EEG and video scores remain
        separate.
      </p>
    </section>
  );
}

function ReportValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-ink-muted">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-ink">
        {value}
      </dd>
    </div>
  );
}

function formatSignedSeconds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "not set";
  const sign = value < 0 ? "−" : "+";
  return `${sign}${formatRelativeTime(Math.abs(value))}`;
}

function videoRedactionSummary(result: DetectionResult): string {
  const visualization = result.visualization;
  if (!visualization?.available) return "Not available";
  const selectiveBlur = visualization.privacy_method.includes("patient-blur")
    ? "Legacy patient-region blur"
    : "Face blur";
  return visualization.full_frame_fallback_frames > 0
    ? `${selectiveBlur} · full-frame fallback on ${visualization.full_frame_fallback_frames} frames`
    : selectiveBlur;
}

function PairedModelTimeline({
  eegResult,
  videoResult,
  mappedSegments,
  eegResultHref,
  videoResultHref,
}: {
  eegResult: AnalysisResult;
  videoResult: DetectionResult;
  mappedSegments: VideoEegSync["mapped_segments"];
  eegResultHref: string;
  videoResultHref: string;
}) {
  const start = 0;
  const mappedEnd = mappedSegments.reduce(
    (latest, segment) =>
      Math.max(
        latest,
        segment.eeg_source_start_seconds +
          segment.video_end_seconds -
          segment.video_start_seconds,
      ),
    0,
  );
  const end = Math.max(eegResult.recordingDurationSeconds, mappedEnd);
  const span = end;
  if (!Number.isFinite(span) || span <= 0) return null;

  const eegIntervals = eegResult.predictionWindows
    .filter((window) => window.seizureDetected)
    .map((window) => ({ start: window.startSeconds, end: window.endSeconds }));
  const videoIntervals = videoResult.intervals.flatMap((interval) =>
    mappedSegments.flatMap((segment) => {
      const videoStart = Math.max(
        interval.start_time,
        segment.video_start_seconds,
      );
      const videoEnd = Math.min(interval.end_time, segment.video_end_seconds);
      if (videoEnd <= videoStart) return [];
      return [
        {
          start:
            segment.eeg_source_start_seconds +
            videoStart -
            segment.video_start_seconds,
          end:
            segment.eeg_source_start_seconds +
            videoEnd -
            segment.video_start_seconds,
        },
      ];
    }),
  );
  const ticks = Array.from(
    { length: 5 },
    (_, index) => start + (span * index) / 4,
  );

  return (
    <section
      className="panel p-5 sm:p-6"
      aria-labelledby="paired-timeline-heading"
    >
      <h3 id="paired-timeline-heading" className="text-base font-bold">
        EEG and video timeline
      </h3>
      <p className="mt-1 text-sm leading-6 text-ink-muted">
        The unique camera metadata match is mapped onto the EEG source clock.
        Footage during EEG gaps is omitted from this aligned view. Model scores
        remain separate.
      </p>
      <div className="mt-5 space-y-4">
        <TimelineLane
          label="EEG flagged windows"
          intervals={eegIntervals}
          start={start}
          span={span}
          tone="bg-amber"
          href={eegResultHref}
        />
        <TimelineLane
          label="Video flagged windows"
          intervals={videoIntervals}
          start={start}
          span={span}
          tone="bg-teal-dark"
          href={videoResultHref}
        />
      </div>
      <div className="mt-2 grid grid-cols-5 font-mono text-[0.68rem] tabular-nums text-ink-muted">
        {ticks.map((tick, index) => (
          <span
            className={
              index === 0
                ? "text-left"
                : index === ticks.length - 1
                  ? "text-right"
                  : "text-center"
            }
            key={index}
          >
            {formatSignedSeconds(tick)}
          </span>
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-faint">Time relative to EEG start</p>
    </section>
  );
}

function TimelineLane({
  label,
  intervals,
  start,
  span,
  tone,
  href,
}: {
  label: string;
  intervals: Array<{ start: number; end: number }>;
  start: number;
  span: number;
  tone: string;
  href: string;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[12rem_minmax(0,1fr)] sm:items-center">
      <Link
        className="text-xs font-semibold text-ink hover:text-teal-dark"
        href={href}
      >
        {label}
      </Link>
      <div
        className="relative h-7 overflow-hidden rounded-md bg-surface-muted"
        role="img"
        aria-label={`${label}: ${intervals.length} threshold-crossing intervals`}
      >
        {[25, 50, 75].map((position) => (
          <span
            key={position}
            className="absolute inset-y-0 border-l border-white/80"
            style={{ left: `${position}%` }}
            aria-hidden="true"
          />
        ))}
        {intervals.map((interval, index) => {
          const clippedStart = Math.max(start, interval.start);
          const clippedEnd = Math.min(start + span, interval.end);
          if (clippedEnd <= clippedStart) return null;
          const left = ((clippedStart - start) / span) * 100;
          const width = ((clippedEnd - clippedStart) / span) * 100;
          return (
            <span
              key={`${interval.start}-${interval.end}-${index}`}
              className={`absolute inset-y-1 rounded-sm ${tone}`}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={`${formatRelativeTime(interval.start)}–${formatRelativeTime(interval.end)}`}
              aria-hidden="true"
            />
          );
        })}
      </div>
    </div>
  );
}

function videoEvidenceSummary(result: DetectionResult): string {
  const evidence = result.predictions.find(
    (item) => item.model_evidence,
  )?.model_evidence;
  if (!evidence) return "No Grad-CAM evidence was returned for this output.";
  if (evidence.method === "vsvig-graph-grad-cam")
    return "Relative model contribution across the strongest score window's 30 samples and 15 keypoint patches. This is not pixel-level localization or a clinical explanation.";
  return `${evidence.patches?.length ?? 0} legacy patch-sensitivity values are available. They are not a clinical or causal explanation.`;
}
