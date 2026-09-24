"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getResult } from "@/lib/api";
import {
  getDetectionResults,
  type DetectionJob,
  type DetectionResult,
} from "@/lib/video-detection";
import { formatRelativeTime } from "@/lib/format";
import type { AnalysisResult, Session } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EegAnnotationList } from "./EegAnnotationList";

const READY_RECORDING_STATUSES = new Set(["inferred"]);
type LoadedEegResult =
  | { recordId: string; status: "ready"; result: AnalysisResult }
  | { recordId: string; status: "error" };
type LoadedVideoResult =
  | { jobId: string; status: "ready"; result: DetectionResult }
  | { jobId: string; status: "error" };

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
  const [offsetInput, setOffsetInput] = useState("0");
  const effectiveRecordId = readyRecordIds.includes(selectedRecordId)
    ? selectedRecordId
    : readyRecordIds.length === 1
      ? readyRecordIds[0]
      : "";
  const activeVideoJobId = videoJob?.status === "ready" ? videoJob.job_id : "";

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

  const offsetSeconds = offsetInput.trim() === "" ? null : Number(offsetInput);
  const offsetIsValid =
    offsetSeconds !== null &&
    Number.isFinite(offsetSeconds) &&
    Math.abs(offsetSeconds) <= 86_400;
  const pairedForDemo = hasEegLink && hasVideoLink;
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

      {pairedForDemo && (
        <section className="rounded-xl border border-amber/40 bg-amber-soft p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold">
              Assumed pairing — not verified
            </h3>
            <span className="rounded-full border border-amber/40 px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-[0.08em] text-amber">
              Demo assumption
            </span>
          </div>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-ink-muted">
            These analyses are shown together for demonstration only. The
            application has not verified that the recordings belong together or
            are synchronized. The offset below is local to this page and is not
            saved to the case.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,15rem)_1fr] sm:items-end">
            <label
              className="no-print block text-sm font-semibold"
              htmlFor="video-start-offset"
            >
              Video starts after EEG (seconds)
              <input
                id="video-start-offset"
                aria-label="Video starts after EEG (seconds)"
                className="mt-2 block min-h-11 w-full rounded-lg border border-rule bg-white px-3 font-mono text-sm tabular-nums text-ink outline-none focus-visible:ring-2 focus-visible:ring-teal"
                type="number"
                min="-86400"
                max="86400"
                step="0.1"
                value={offsetInput}
                onChange={(event) => setOffsetInput(event.target.value)}
              />
            </label>
            <p className="text-xs leading-5 text-ink-muted">
              Positive values mean the video begins later. The default 0s is an
              assumption, not a measured clock offset.
            </p>
          </div>
          {!offsetIsValid && (
            <p className="mt-2 text-sm text-red" role="alert">
              Enter an offset from −86,400 to +86,400 seconds to show mapped
              times.
            </p>
          )}
          {offsetIsValid && (
            <p className="print-only mt-2 text-xs">
              Assumed clock offset: {formatSignedSeconds(offsetSeconds)}. Video
              time = EEG time − offset.
            </p>
          )}
        </section>
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
                Window-level technical output only. Threshold flags are not a
                diagnosis or a recording-level probability.
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
                  Threshold-crossing intervals · review only
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
          reviewRequired={eegResult.annotationReviewRequired}
          videoStartMinusEegStartSeconds={
            pairedForDemo && offsetIsValid ? offsetSeconds : undefined
          }
          videoDurationSeconds={pairedForDemo ? videoDurationSeconds : null}
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
              Model scores are uncalibrated and are not probabilities or
              diagnoses. A protected preview, when available, remains in the
              authenticated video review.
            </p>
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
                  label="Threshold-crossing windows"
                  value={String(
                    videoResult.predictions.filter(
                      (item) => item.seizure_detected,
                    ).length,
                  )}
                />
                <ReportValue
                  label="Privacy review"
                  value={
                    videoResult.privacy?.review_required
                      ? "Human review required"
                      : videoResult.privacy
                        ? videoResult.privacy.quality_flags.length > 0
                          ? "Review quality flags"
                          : "No privacy quality flags reported"
                        : "Metadata unavailable"
                  }
                />
              </dl>
              {videoResult.privacy?.model_input_adaptation === "letterbox" && (
                <p className="mt-4 rounded-lg border border-amber/40 bg-amber-soft px-3 py-2 text-sm text-amber">
                  Demo-only letterbox adaptation was used. This preprocessing
                  path is exploratory and has not been validated for clinical
                  use.
                </p>
              )}
              <div className="mt-5 border-t border-rule pt-4">
                <h4 className="text-xs font-bold uppercase tracking-[0.08em] text-ink-muted">
                  Threshold-crossing intervals · review only
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
                          <span className="font-mono tabular-nums">
                            Video {formatRelativeTime(interval.start_time)}–
                            {formatRelativeTime(interval.end_time)}
                          </span>
                          {pairedForDemo && offsetIsValid && (
                            <span className="font-mono text-xs tabular-nums text-ink-muted">
                              Assumed EEG{" "}
                              {formatRelativeTime(
                                interval.start_time + (offsetSeconds ?? 0),
                              )}
                              –
                              {formatRelativeTime(
                                interval.end_time + (offsetSeconds ?? 0),
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
                  Video sensitivity evidence
                </h4>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {videoEvidenceSummary(videoResult)}
                </p>
              </div>
            </>
          ) : videoJob?.status === "failed" ||
            videoJob?.status === "expired" ? (
            <p className="mt-4 text-sm text-ink-muted">
              No video inference result is available because the job did not
              complete successfully.
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

      <p className="text-xs leading-5 text-ink-muted">
        Research and demonstration output only · not a diagnosis · source event
        markers are separate from model predictions · no pairing or clock offset
        has been verified.
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
  return `${value > 0 ? "+" : ""}${value}s`;
}

function videoEvidenceSummary(result: DetectionResult): string {
  const evidence = result.predictions.find(
    (item) => item.model_evidence,
  )?.model_evidence;
  if (!evidence)
    return "No patch-occlusion sensitivity artifact was returned for this output.";
  const patchCount = evidence.patches.length;
  return `${patchCount} patch-occlusion sensitivity change(s) were returned. This indicates model sensitivity to altered input regions; it is not a clinical or causal explanation.`;
}
