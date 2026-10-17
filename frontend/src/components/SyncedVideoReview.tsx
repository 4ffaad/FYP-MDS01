"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  gradCamSampleForVideoTime,
  poseSampleForVideoTime,
  VideoGradCamOverlay,
  VideoModelPatchBlurOverlay,
} from "@/components/VideoModelEvidenceOverlay";
import { apiMediaUrl } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import {
  detectionVisualizationUrl,
  eegTimeForVideoTime,
  getDetectionResults,
  videoTimeForEegTime,
  type DetectionJob,
  type DetectionResult,
  type VideoEegSync,
} from "@/lib/video-detection";

export type VideoSeekRequest = {
  jobId: string;
  videoSeconds: number;
  requestId: number;
};

export type SharedVideoPlayback = {
  timeSeconds: number;
  isPlaying: boolean;
  playbackRate: number;
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
  playback,
  onPlaybackTimeChange,
  onPlaybackStateChange,
  onPlaybackRateChange,
  recordingDurationSeconds,
  seekRequest,
  compact = false,
}: {
  clips: DetectionJob[];
  selectedJobId: string;
  onSelectedJobIdChange: (jobId: string) => void;
  selectedEegTime: number | null;
  onEegTimeSelect: (seconds: number) => void;
  onPlaybackEegTime?: (seconds: number | null) => void;
  /** Optional owner-controlled EEG clock; video updates are reported back. */
  playback?: SharedVideoPlayback;
  onPlaybackTimeChange?: (seconds: number) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackRateChange?: (rate: number) => void;
  recordingDurationSeconds: number;
  seekRequest: VideoSeekRequest | null;
  compact?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoFrameRef = useRef<HTMLDivElement>(null);
  const appliedRequestRef = useRef<string | null>(null);
  const pauseForUnmappedTime = useRef(false);
  const [bookmarks, setBookmarks] = useState<
    Array<{ jobId: string; seconds: number }>
  >([]);
  const [unavailableJobId, setUnavailableJobId] = useState<string | null>(null);
  const [bufferingJobId, setBufferingJobId] = useState<string | null>(null);
  const [localPlaybackRate, setLocalPlaybackRate] = useState(1);
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
  const sharedPlayback =
    selectedClip?.sync?.status === "linked" ? playback : undefined;
  const selectedJobIdForResult = selectedClip?.job_id;
  const selectedStatusForResult = selectedClip?.status;
  const selectedJobIsReferenceOnly = selectedClip?.reference_only === true;
  const selectedVideoAvailable = selectedClip?.video_available;
  const isBuffering = bufferingJobId === selectedClip?.job_id;
  const currentVideoTime =
    videoTimeState?.jobId === selectedClip?.job_id ? videoTimeState.time : 0;
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
  const selectiveBlurLabel = selectedClip?.review_privacy_method?.includes(
    "patient-blur",
  )
    ? "Legacy patient blur"
    : "Face blur";
  const unblurred =
    selectedClip?.review_privacy_method === "unblurred-owner-source";
  const selectedBlurModeLabel = unblurred
    ? "Owner reference · unblurred"
    : blurMode === "all"
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

  useEffect(() => {
    if (
      !selectedJobIdForResult ||
      selectedStatusForResult !== "ready" ||
      selectedJobIsReferenceOnly
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
  }, [
    selectedJobIdForResult,
    selectedJobIsReferenceOnly,
    selectedStatusForResult,
  ]);

  function toggleFullscreen() {
    const frame = videoFrameRef.current;
    if (!frame) return;
    if (document.fullscreenElement === frame) {
      void document.exitFullscreen();
    } else {
      void frame.requestFullscreen();
    }
  }

  const authoritativeEegTime = sharedPlayback?.timeSeconds ?? selectedEegTime;
  const noSynchronizedVideoAtSelectedTime =
    sharedPlayback !== undefined &&
    authoritativeEegTime !== null &&
    videoTimeForEegTime(
      selectedClip?.sync?.mapped_segments,
      authoritativeEegTime,
    ) === null;

  useEffect(() => {
    if (sharedPlayback) {
      const covering = timeline.find(
        (segment) =>
          authoritativeEegTime !== null &&
          videoTimeForEegTime([segment], authoritativeEegTime) !== null,
      );
      if (covering && covering.clip.job_id !== selectedClip?.job_id) {
        onSelectedJobIdChange(covering.clip.job_id);
        return;
      }
    }

    const video = videoRef.current;
    if (!video || !selectedClip?.video_available) {
      pauseForUnmappedTime.current = true;
      video?.pause();
      return;
    }

    const seek =
      sharedPlayback && authoritativeEegTime !== null
        ? videoTimeForEegTime(
            selectedClip.sync?.mapped_segments,
            authoritativeEegTime,
          )
        : seekRequest?.jobId === selectedClip.job_id
          ? seekRequest.videoSeconds
          : null;

    if (seek === null) {
      if (sharedPlayback) {
        pauseForUnmappedTime.current = true;
        video.pause();
      }
      return;
    }
    pauseForUnmappedTime.current = false;
    if (video.readyState < HTMLMediaElement.HAVE_METADATA) return;

    const requestId = sharedPlayback
      ? `${selectedClip.job_id}:${sharedPlayback.requestId}`
      : `${seekRequest?.jobId ?? ""}:${seekRequest?.requestId ?? ""}`;
    const isNewRequest = requestId !== appliedRequestRef.current;
    appliedRequestRef.current = requestId;
    if (isNewRequest || Math.abs(video.currentTime - seek) > 0.2) {
      video.currentTime = Math.max(0, Math.min(video.duration, seek));
    }

    if (sharedPlayback) {
      if (video.playbackRate !== sharedPlayback.playbackRate)
        video.playbackRate = sharedPlayback.playbackRate;
      if (sharedPlayback.isPlaying && video.paused)
        void video.play().catch(() => onPlaybackStateChange?.(false));
      if (!sharedPlayback.isPlaying && !video.paused) video.pause();
    }
  }, [
    authoritativeEegTime,
    onSelectedJobIdChange,
    onPlaybackStateChange,
    sharedPlayback,
    seekRequest,
    selectedClip,
    timeline,
  ]);

  useEffect(() => {
    if (
      selectedClip?.sync?.status === "linked" &&
      authoritativeEegTime !== null &&
      videoTimeForEegTime(
        selectedClip?.sync?.mapped_segments,
        authoritativeEegTime,
      ) === null
    ) {
      pauseForUnmappedTime.current = true;
      videoRef.current?.pause();
    }
  }, [selectedClip, authoritativeEegTime]);

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
        {selectedClip.review_warning && (
          <p
            className="rounded-lg border border-amber/40 bg-amber-soft px-4 py-3 text-sm leading-6 text-ink-muted"
            role="status"
          >
            {selectedClip.review_warning}
          </p>
        )}
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
                const nextClip = clips.find(
                  (clip) => clip.job_id === event.currentTarget.value,
                );
                const firstSegment = nextClip?.sync?.mapped_segments[0];
                if (firstSegment)
                  onEegTimeSelect(firstSegment.eeg_source_start_seconds);
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
                Recorded EEG samples overlap{" "}
                {formatRelativeTime(eegCoverageSeconds)}
                of {formatRelativeTime(totalVideoSeconds)} video. Verified video
                remains on its source clock through internal EEG gaps; footage
                outside the recording span is not linked.
              </p>
            )}
          </div>
        )}

        {!compact && !unblurred && (
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
          noSynchronizedVideoAtSelectedTime ? (
            <div
              className="grid aspect-video place-items-center rounded-xl bg-black p-6 text-center text-sm font-semibold text-white"
              role="status"
            >
              No synchronized video covers EEG{" "}
              {formatRelativeTime(authoritativeEegTime ?? 0)}.
            </div>
          ) : unavailableJobId === selectedClip.job_id ? (
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
                  className={`absolute inset-0 ${!unblurred && blurMode === "all" ? "blur-[8px]" : ""}`}
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
                    aria-label={`${clipLabel(selectedClip, clips.indexOf(selectedClip))}, ${unblurred ? "unblurred owner-only" : blurMode === "all" ? "full-frame blurred" : selectiveBlurLabel.toLocaleLowerCase()} review video`}
                    onLoadedMetadata={(event) => {
                      setBufferingJobId(null);
                      const video = event.currentTarget;
                      const seek =
                        sharedPlayback && authoritativeEegTime !== null
                          ? videoTimeForEegTime(
                              selectedClip.sync?.mapped_segments,
                              authoritativeEegTime,
                            )
                          : seekRequest?.jobId === selectedClip.job_id
                            ? seekRequest.videoSeconds
                            : null;
                      if (seek !== null) {
                        video.currentTime = Math.max(
                          0,
                          Math.min(video.duration, seek),
                        );
                      }
                      if (sharedPlayback) {
                        video.playbackRate = sharedPlayback.playbackRate;
                        if (sharedPlayback.isPlaying)
                          void video
                            .play()
                            .catch(() => onPlaybackStateChange?.(false));
                      }
                      setVideoTimeState({
                        jobId: selectedClip.job_id,
                        time: video.currentTime,
                      });
                    }}
                    onTimeUpdate={(event) => {
                      const videoSeconds = event.currentTarget.currentTime;
                      setVideoTimeState({
                        jobId: selectedClip.job_id,
                        time: videoSeconds,
                      });
                      const eegTime = eegTimeForVideoTime(
                        selectedClip.sync?.mapped_segments,
                        videoSeconds,
                      );
                      if (eegTime !== null) {
                        if (onPlaybackTimeChange) onPlaybackTimeChange(eegTime);
                        else onPlaybackEegTime?.(eegTime);
                      } else if (sharedPlayback) {
                        if (sharedPlayback.isPlaying) {
                          const lastSegment =
                            selectedClip.sync?.mapped_segments.at(-1);
                          const atVideoEnd =
                            videoSeconds >= selectedClip.duration_seconds - 0.1;
                          const atMappedEnd =
                            lastSegment !== undefined &&
                            videoSeconds >= lastSegment.video_end_seconds - 0.1;
                          const endEegTime = lastSegment
                            ? lastSegment.eeg_source_start_seconds +
                              lastSegment.video_end_seconds -
                              lastSegment.video_start_seconds
                            : null;
                          const next = timeline.find(
                            (segment) =>
                              segment.clip.job_id !== selectedClip.job_id &&
                              endEegTime !== null &&
                              Math.abs(
                                segment.eeg_source_start_seconds - endEegTime,
                              ) < 0.2,
                          );
                          if (next && atVideoEnd && atMappedEnd) {
                            onEegTimeSelect(next.eeg_source_start_seconds);
                            onPlaybackTimeChange?.(
                              next.eeg_source_start_seconds,
                            );
                          } else if (!atVideoEnd) {
                            pauseForUnmappedTime.current = true;
                            event.currentTarget.pause();
                          }
                        }
                      } else {
                        onPlaybackEegTime?.(null);
                      }
                    }}
                    onWaiting={() => setBufferingJobId(selectedClip.job_id)}
                    onCanPlay={() => setBufferingJobId(null)}
                    onPlaying={() => setBufferingJobId(null)}
                    onSeeking={() => setBufferingJobId(selectedClip.job_id)}
                    onSeeked={() => setBufferingJobId(null)}
                    onPlay={() => {
                      if (sharedPlayback) onPlaybackStateChange?.(true);
                    }}
                    onPause={() => {
                      if (sharedPlayback && !pauseForUnmappedTime.current)
                        onPlaybackStateChange?.(false);
                    }}
                    onRateChange={(event) => {
                      const rate = event.currentTarget.playbackRate;
                      setLocalPlaybackRate(rate);
                      if (sharedPlayback) onPlaybackRateChange?.(rate);
                    }}
                    onEnded={() => {
                      const lastSegment =
                        selectedClip.sync?.mapped_segments.at(-1);
                      if (
                        !lastSegment ||
                        lastSegment.video_end_seconds <
                          selectedClip.duration_seconds - 0.2
                      )
                        return;
                      const end =
                        lastSegment.eeg_source_start_seconds +
                        lastSegment.video_end_seconds -
                        lastSegment.video_start_seconds;
                      const next = timeline.find(
                        (segment) =>
                          segment.clip.job_id !== selectedClip.job_id &&
                          Math.abs(segment.eeg_source_start_seconds - end) <
                            0.2,
                      );
                      if (next) {
                        onEegTimeSelect(next.eeg_source_start_seconds);
                        if (sharedPlayback?.isPlaying)
                          onPlaybackStateChange?.(true);
                      } else if (sharedPlayback) {
                        onPlaybackStateChange?.(false);
                      }
                    }}
                    onError={() => {
                      setUnavailableJobId(selectedClip.job_id);
                      if (sharedPlayback) onPlaybackStateChange?.(false);
                    }}
                  >
                    Your browser cannot play this protected review video.
                  </video>
                  <VideoModelPatchBlurOverlay
                    videoRef={videoRef}
                    poseSample={currentPoseSample}
                    strengthPercent={selectedClip.blur_strength_percent}
                    enabled={!unblurred && blurMode === "face+patches"}
                  />
                  <VideoGradCamOverlay
                    poseSample={currentPoseSample}
                    gradCamSample={currentGradCamSample}
                  />
                  {isBuffering && (
                    <span
                      className="absolute bottom-3 left-3 z-20 rounded bg-black/75 px-2 py-1 text-xs text-white"
                      role="status"
                    >
                      Loading video frame…
                    </span>
                  )}
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
                ? "No playable review video is available"
                : "Video processing is still in progress"}
            </p>
            <p className="mt-1 text-sm leading-6 text-ink-muted">
              {selectedClip.status === "failed"
                ? "The clip cannot be played in this review. EEG and synchronization status remain available."
                : `Current stage: ${selectedClip.current_stage.replaceAll("-", " ")}.`}
            </p>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {sharedPlayback && selectedClip.video_available && (
            <button
              className="min-h-9 rounded border border-rule px-3 font-semibold"
              type="button"
              aria-label={
                sharedPlayback.isPlaying
                  ? "Pause EEG and video playback"
                  : "Play EEG and video"
              }
              onClick={() => onPlaybackStateChange?.(!sharedPlayback.isPlaying)}
            >
              {sharedPlayback.isPlaying
                ? "Pause EEG + video"
                : "Play EEG + video"}
            </button>
          )}
          <label>
            Speed{" "}
            <select
              aria-label="Video playback speed"
              value={String(sharedPlayback?.playbackRate ?? localPlaybackRate)}
              onChange={(event) => {
                const rate = Number(event.target.value);
                setLocalPlaybackRate(rate);
                if (videoRef.current) videoRef.current.playbackRate = rate;
                if (sharedPlayback) onPlaybackRateChange?.(rate);
              }}
            >
              <option value="0.25">0.25×</option>
              <option value="0.5">0.5×</option>
              <option value="1">1×</option>
            </select>
          </label>
          {[-1, 1].map((direction) => (
            <button
              className="min-h-9 rounded border border-rule px-3"
              type="button"
              key={direction}
              onClick={() => {
                const video = videoRef.current;
                if (video) {
                  video.pause();
                  video.currentTime = Math.max(
                    0,
                    Math.min(
                      video.duration,
                      video.currentTime +
                        direction / Math.max(selectedClip.fps, 1),
                    ),
                  );
                }
              }}
            >
              {direction < 0 ? "Previous frame" : "Next frame"}
            </button>
          ))}
          <button
            className="min-h-9 rounded border border-rule px-3"
            type="button"
            onClick={() =>
              setBookmarks((items) => [
                ...items,
                {
                  jobId: selectedClip.job_id,
                  seconds: videoRef.current?.currentTime ?? 0,
                },
              ])
            }
          >
            Bookmark {formatRelativeTime(currentVideoTime)}
          </button>
          {selectedClip.source_available && (
            <a
              className="underline"
              href={apiMediaUrl(
                `/api/video-detection/jobs/${encodeURIComponent(selectedClip.job_id)}/original`,
              )}
            >
              Download original video
            </a>
          )}
        </div>
        {bookmarks
          .filter((item) => item.jobId === selectedClip.job_id)
          .map((item, index) => (
            <button
              className="mr-2 min-h-9 text-xs underline"
              key={index}
              type="button"
              onClick={() => {
                if (videoRef.current)
                  videoRef.current.currentTime = item.seconds;
              }}
            >
              Bookmark {formatRelativeTime(item.seconds)}
            </button>
          ))}
        {selectedClip.sync?.status === "linked" && (
          <p role="status" className="text-xs text-ink-muted">
            EEG{" "}
            {formatRelativeTime(
              eegTimeForVideoTime(
                selectedClip.sync.mapped_segments,
                currentVideoTime,
              ) ?? 0,
            )}{" "}
            · Video {String(clips.indexOf(selectedClip) + 1).padStart(2, "0")} ·{" "}
            {formatRelativeTime(currentVideoTime)}
          </p>
        )}
        <p className="text-xs text-ink-muted" role="status">
          {syncStatusMessage(
            selectedClip.sync?.status,
            selectedClip.video_available,
          )}
        </p>
        {!compact && !unblurred && (
          <p className="text-xs text-ink-muted">
            Face blur · VSViG patch blur {selectedClip.blur_strength_percent}%
          </p>
        )}
        {!compact && !unblurred && typeof reviewBlurCoverage === "number" && (
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
    return `Video clip ${String(index + 1).padStart(2, "0")} · ${syncStatusLabel(clip.sync?.status)}`;
  const start = Math.min(
    ...segments.map((segment) => segment.eeg_source_start_seconds),
  );
  const coverage = clip.sync?.eeg_coverage_seconds ?? 0;
  return `Video clip ${String(index + 1).padStart(2, "0")} · EEG ${formatRelativeTime(start)} · ${formatRelativeTime(coverage)} signal`;
}

function syncStatusLabel(status: VideoEegSync["status"] | undefined): string {
  switch (status) {
    case "linked":
      return "matched";
    case "incomplete_folder":
      return "folder incomplete";
    case "pending":
      return "awaiting EEG";
    case "missing_reference":
      return "missing anchors";
    case "clock_mismatch":
      return "clock mismatch";
    case "frame_mismatch":
      return "frame mismatch";
    case "ambiguous":
      return "ambiguous";
    case "unmatched":
      return "unmatched";
    default:
      return "unavailable";
  }
}

function syncStatusMessage(
  status: VideoEegSync["status"] | undefined,
  videoAvailable: boolean,
): string {
  switch (status) {
    case "linked":
      return "Unique metadata match · partial EEG coverage may apply. This confirms a match among uploads, not original byte identity.";
    case "incomplete_folder":
      return "The camera folder upload is incomplete, so synchronization has not been resolved.";
    case "pending":
      return "Waiting for the EEG recording metadata needed to resolve synchronization.";
    case "missing_reference":
      return "The EEG metadata has no complete clock-anchor reference for this clip.";
    case "clock_mismatch":
      return "The EEG clock anchors do not agree with this clip's frame timing.";
    case "frame_mismatch":
      return "The anchored frame count does not agree with this clip's duration and frame rate.";
    case "ambiguous":
      return "The upload metadata matches more than one possible recording; no synchronized link was made.";
    case "unmatched":
      return "No unique EEG match was found. The clip can still be reviewed independently when playable.";
    default:
      return videoAvailable
        ? "No usable EEG synchronization metadata is available. The clip can still be reviewed independently."
        : "No playable video is available for this clip.";
  }
}
