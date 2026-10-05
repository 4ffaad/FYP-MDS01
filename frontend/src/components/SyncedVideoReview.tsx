"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  gradCamSampleForVideoTime,
  poseSampleForVideoTime,
  VideoGradCamOverlay,
  VideoModelPatchBlurOverlay,
} from "@/components/VideoModelEvidenceOverlay";
import { formatRelativeTime } from "@/lib/format";
import {
  detectionVisualizationUrl,
  eegTimeForVideoTime,
  getDetectionResults,
  videoTimeForEegTime,
  videoJobFailureMessage,
  type DetectionJob,
  type DetectionResult,
} from "@/lib/video-detection";

export type VideoSeekRequest = {
  jobId: string;
  videoSeconds: number;
  requestId: number;
};

/** Show one owner's Nicolet-linked clips and seek them from EEG source time. */
export function SyncedVideoReview({
  clips,
  selectedJobId,
  onSelectedJobIdChange,
  selectedEegTime,
  onEegTimeSelect,
  onPlaybackEegTime,
  recordingDurationSeconds,
  seekRequest,
  compact = false,
}: {
  clips: DetectionJob[];
  selectedJobId: string;
  onSelectedJobIdChange: (jobId: string) => void;
  selectedEegTime: number | null;
  onEegTimeSelect: (seconds: number) => void;
  onPlaybackEegTime: (seconds: number | null) => void;
  recordingDurationSeconds: number;
  seekRequest: VideoSeekRequest | null;
  compact?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoFrameRef = useRef<HTMLDivElement>(null);
  const [unavailableJobId, setUnavailableJobId] = useState<string | null>(null);
  const [blurMode, setBlurMode] = useState<"face+patches" | "face" | "all">(
    "face+patches",
  );
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [videoTimeState, setVideoTimeState] = useState<{
    jobId: string;
    time: number;
  } | null>(null);
  const [resultState, setResultState] = useState<{
    jobId: string;
    result: DetectionResult | null;
  } | null>(null);
  const selectedClip =
    clips.find((clip) => clip.job_id === selectedJobId) ?? clips[0];
  const selectedJobIdForResult = selectedClip?.job_id;
  const selectedStatusForResult = selectedClip?.status;
  const selectedVideoAvailable = selectedClip?.video_available;
  const currentVideoTime =
    videoTimeState?.jobId === selectedClip?.job_id ? videoTimeState.time : 0;
  const selectiveBlurLabel = selectedClip?.review_privacy_method?.includes(
    "patient-blur",
  )
    ? "Legacy patient blur"
    : "Face blur";
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

  function toggleFullscreen() {
    const frame = videoFrameRef.current;
    if (!frame) return;
    if (document.fullscreenElement === frame) {
      void document.exitFullscreen();
    } else {
      void frame.requestFullscreen();
    }
  }

  useEffect(() => {
    const video = videoRef.current;
    if (
      video &&
      selectedClip?.video_available &&
      seekRequest?.jobId === selectedClip.job_id &&
      video.readyState >= HTMLMediaElement.HAVE_METADATA
    ) {
      video.currentTime = Math.max(
        0,
        Math.min(video.duration, seekRequest.videoSeconds),
      );
    }
  }, [selectedClip, seekRequest]);

  useEffect(() => {
    if (
      !selectedJobIdForResult ||
      selectedStatusForResult !== "ready" ||
      !selectedVideoAvailable
    )
      return;
    const controller = new AbortController();
    const jobId = selectedJobIdForResult;
    void getDetectionResults(jobId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setResultState({ jobId, result });
      })
      .catch(() => {
        if (!controller.signal.aborted) setResultState({ jobId, result: null });
      });
    return () => controller.abort();
  }, [selectedJobIdForResult, selectedStatusForResult, selectedVideoAvailable]);

  useEffect(() => {
    if (
      selectedEegTime !== null &&
      videoTimeForEegTime(
        selectedClip?.sync?.mapped_segments,
        selectedEegTime,
      ) === null
    ) {
      videoRef.current?.pause();
    }
  }, [selectedClip, selectedEegTime]);

  const timeline = useMemo(
    () =>
      clips.flatMap((clip, clipIndex) =>
        (clip.sync?.mapped_segments ?? []).map((segment) => ({
          clip,
          clipIndex,
          ...segment,
        })),
      ),
    [clips],
  );
  const timelineEnd = Math.max(
    recordingDurationSeconds,
    ...timeline.map(
      (segment) =>
        segment.eeg_source_start_seconds +
        segment.video_end_seconds -
        segment.video_start_seconds,
    ),
  );
  const totalVideoSeconds = clips.reduce(
    (total, clip) => total + (clip.sync?.video_duration_seconds ?? 0),
    0,
  );
  const eegCoverageSeconds = clips.reduce(
    (total, clip) => total + (clip.sync?.eeg_coverage_seconds ?? 0),
    0,
  );
  const selectedResult =
    resultState?.jobId === selectedClip?.job_id ? resultState.result : null;
  const selectedPrediction = selectedResult?.predictions.find(
    (prediction) =>
      currentVideoTime >= prediction.start_time &&
      currentVideoTime < prediction.end_time,
  );
  const currentPoseSample = selectedResult
    ? poseSampleForVideoTime(
        selectedPrediction,
        currentVideoTime,
        selectedResult.model.sample_fps,
      )
    : null;
  const currentGradCamSample = selectedResult
    ? gradCamSampleForVideoTime(
        selectedPrediction,
        currentVideoTime,
        selectedResult.model.sample_fps,
      )
    : null;
  const reviewBlurCoverage =
    selectedResult?.visualization?.face_blur_coverage ??
    selectedResult?.privacy?.face_blur_coverage ??
    selectedResult?.visualization?.patient_blur_coverage ??
    selectedResult?.visualization?.face_detection_coverage ??
    selectedResult?.privacy?.patient_blur_coverage ??
    selectedResult?.privacy?.face_detection_coverage;

  if (!selectedClip) return null;

  return (
    <section
      className={compact ? "min-w-0" : "panel overflow-hidden"}
      aria-label={compact ? "Synchronized video review" : undefined}
      aria-labelledby={compact ? undefined : "synchronized-video-heading"}
    >
      {!compact && (
        <div className="border-b border-rule px-5 py-5 sm:px-7">
          <p className="eyebrow">VEEG review</p>
          <h2
            id="synchronized-video-heading"
            className="mt-1 text-lg font-semibold"
          >
            Synchronized camera video
          </h2>
        </div>
      )}

      <div className={compact ? "space-y-2" : "space-y-5 p-5 sm:p-7"}>
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <label className="block text-sm font-semibold text-ink">
            <span className={compact ? "sr-only" : ""}>
              {compact ? "Video clip" : "Select synchronized video clip"}
            </span>
            <select
              className={`w-full rounded-lg border border-rule-strong bg-surface px-2 text-sm font-medium ${compact ? "min-h-8 text-xs" : "mt-2 min-h-11 px-3"}`}
              value={selectedClip.job_id}
              onChange={(event) => {
                onSelectedJobIdChange(event.currentTarget.value);
                setUnavailableJobId(null);
              }}
            >
              {clips.map((clip, index) => (
                <option key={clip.job_id} value={clip.job_id}>
                  {clipLabel(clip, index)}
                </option>
              ))}
            </select>
          </label>
          {!compact && (
            <Link
              className="text-sm font-semibold text-teal-dark underline underline-offset-4"
              href={`/video-detection/${encodeURIComponent(selectedClip.job_id)}`}
            >
              Open clip details
            </Link>
          )}
        </div>

        {!compact && (
          <div>
            <p className="mb-2 text-xs font-semibold text-ink-muted">
              EEG time covered by these clips
            </p>
            <div
              className="relative h-9 overflow-hidden rounded-md bg-surface-soft"
              role="group"
              aria-label="Synchronized camera clip timeline"
            >
              {timelineEnd > 0 &&
                timeline.map((segment, index) => {
                  const segmentDuration =
                    segment.video_end_seconds - segment.video_start_seconds;
                  const left =
                    (segment.eeg_source_start_seconds / timelineEnd) * 100;
                  const width = (segmentDuration / timelineEnd) * 100;
                  return (
                    <button
                      key={`${segment.clip.job_id}-${index}`}
                      className="absolute inset-y-1 min-w-1 rounded-sm bg-teal-dark/80 hover:bg-teal-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-dark"
                      style={{ left: `${left}%`, width: `${width}%` }}
                      type="button"
                      aria-label={`Select ${clipLabel(segment.clip, segment.clipIndex)} at EEG ${formatRelativeTime(segment.eeg_source_start_seconds)}`}
                      title={`${clipLabel(segment.clip, segment.clipIndex)} · EEG ${formatRelativeTime(segment.eeg_source_start_seconds)}`}
                      onClick={() => {
                        onSelectedJobIdChange(segment.clip.job_id);
                        onEegTimeSelect(segment.eeg_source_start_seconds);
                        setUnavailableJobId(null);
                      }}
                    />
                  );
                })}
            </div>
            <div className="mt-1 flex justify-between font-mono text-[0.68rem] tabular-nums text-ink-muted">
              <span>0:00</span>
              <span>{formatRelativeTime(timelineEnd)}</span>
            </div>
            {eegCoverageSeconds + 0.5 < totalVideoSeconds && (
              <p className="mt-2 text-xs leading-5 text-ink-muted">
                EEG covers {formatRelativeTime(eegCoverageSeconds)} of{" "}
                {formatRelativeTime(totalVideoSeconds)} video. Footage outside
                EEG signal segments is not linked on this timeline.
              </p>
            )}
          </div>
        )}

        {!compact && (
          <fieldset className="flex flex-wrap items-center gap-3 text-xs">
            <legend className="sr-only">Video display blur</legend>
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input
                className="size-4 accent-teal"
                type="radio"
                name={`video-blur-${selectedClip.job_id}`}
                checked={blurMode === "face+patches"}
                onChange={() => setBlurMode("face+patches")}
              />
              Face + 15 patches
            </label>
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input
                className="size-4 accent-teal"
                type="radio"
                name={`video-blur-${selectedClip.job_id}`}
                checked={blurMode === "face"}
                onChange={() => setBlurMode("face")}
              />
              {selectiveBlurLabel} only
            </label>
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input
                className="size-4 accent-teal"
                type="radio"
                name={`video-blur-${selectedClip.job_id}`}
                checked={blurMode === "all"}
                onChange={() => setBlurMode("all")}
              />
              Blur all
            </label>
          </fieldset>
        )}

        {!compact && (
          <button
            className="min-h-9 rounded-md border border-rule px-3 text-xs font-semibold text-ink hover:bg-surface-soft"
            type="button"
            aria-label={isFullscreen ? "Exit full screen" : "Full screen"}
            onClick={toggleFullscreen}
          >
            {isFullscreen ? "Exit full screen" : "Full screen"}
          </button>
        )}

        {selectedClip.video_available ? (
          unavailableJobId === selectedClip.job_id ? (
            <p
              className="rounded-lg border border-amber/40 bg-amber-soft p-4 text-sm text-ink-muted"
              role="status"
            >
              The protected review video is unavailable in this browser.
            </p>
          ) : (
            <div
              ref={videoFrameRef}
              className={
                isFullscreen
                  ? "flex h-screen w-screen items-center justify-center bg-black"
                  : "relative aspect-video overflow-hidden rounded-xl bg-black"
              }
              data-testid="synchronized-video-frame"
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
                    key={selectedClip.job_id}
                    ref={videoRef}
                    className="size-full object-contain"
                    src={detectionVisualizationUrl(selectedClip.job_id)}
                    controls
                    controlsList="nofullscreen"
                    playsInline
                    preload="metadata"
                    crossOrigin="use-credentials"
                    data-testid="synchronized-video-player"
                    aria-label={`${clipLabel(selectedClip, clips.indexOf(selectedClip))}, ${blurMode === "all" ? "full-frame blurred" : selectiveBlurLabel.toLocaleLowerCase()} review video`}
                    onLoadedMetadata={(event) => {
                      const video = event.currentTarget;
                      if (seekRequest?.jobId === selectedClip.job_id) {
                        video.currentTime = Math.max(
                          0,
                          Math.min(video.duration, seekRequest.videoSeconds),
                        );
                        setVideoTimeState({
                          jobId: selectedClip.job_id,
                          time: video.currentTime,
                        });
                      }
                    }}
                    onTimeUpdate={(event) => {
                      const videoSeconds = event.currentTarget.currentTime;
                      setVideoTimeState({
                        jobId: selectedClip.job_id,
                        time: videoSeconds,
                      });
                      onPlaybackEegTime(
                        eegTimeForVideoTime(
                          selectedClip.sync?.mapped_segments,
                          videoSeconds,
                        ),
                      );
                    }}
                    onError={() => setUnavailableJobId(selectedClip.job_id)}
                  >
                    Your browser cannot play this protected review video.
                  </video>
                  <VideoModelPatchBlurOverlay
                    videoRef={videoRef}
                    poseSample={currentPoseSample}
                    strengthPercent={selectedClip.blur_strength_percent}
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
          )
        ) : (
          <div className="rounded-lg border border-rule bg-surface-soft p-4">
            <p className="text-sm font-semibold text-ink">
              {selectedClip.status === "failed"
                ? "No privacy-safe video copy is available"
                : "Video processing is still in progress"}
            </p>
            <p className="mt-1 text-sm leading-6 text-ink-muted">
              {selectedClip.status === "failed"
                ? videoJobFailureMessage("failed", selectedClip.error)
                : `Current stage: ${selectedClip.current_stage.replaceAll("-", " ")}.`}
            </p>
          </div>
        )}
        {!compact && (
          <p className="text-xs text-ink-muted">
            Face blur · VSViG patch blur {selectedClip.blur_strength_percent}%
          </p>
        )}
        {!compact && typeof reviewBlurCoverage === "number" && (
          <p className="text-xs text-ink-muted">
            {selectiveBlurLabel} · {Math.round(reviewBlurCoverage * 1000) / 10}%
            {" of frames"}
            {(selectedResult?.visualization?.full_frame_fallback_frames ?? 0) >
              0 &&
              ` · full-frame fallback ${selectedResult?.visualization?.full_frame_fallback_frames} frames`}
          </p>
        )}
        {!compact &&
          currentPoseSample &&
          selectedPrediction?.model_evidence && (
            <p className="text-xs text-ink-muted">
              {selectedPrediction.model_evidence.method ===
              "vsvig-graph-grad-cam"
                ? "VSViG Grad-CAM · warmer patches contribute more to the score"
                : "Older run · patch sensitivity only"}
            </p>
          )}
        {!compact &&
          resultState?.jobId === selectedClip.job_id &&
          !resultState.result && (
            <p className="text-xs text-ink-muted" role="status">
              Model evidence is unavailable for this clip.
            </p>
          )}
      </div>
    </section>
  );
}

function clipLabel(clip: DetectionJob, index: number): string {
  const segments = clip.sync?.mapped_segments ?? [];
  if (!segments.length)
    return `Video clip ${String(index + 1).padStart(2, "0")}`;
  const start = Math.min(
    ...segments.map((segment) => segment.eeg_source_start_seconds),
  );
  const coverage = clip.sync?.eeg_coverage_seconds ?? 0;
  return `Video clip ${String(index + 1).padStart(2, "0")} · EEG ${formatRelativeTime(start)} · ${formatRelativeTime(coverage)} linked`;
}
