"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
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
  getDetection,
  getDetectionResults,
  prepareReferencePlayback,
  referencePlaybackUrl,
  videoTimeForEegTime,
  type DetectionJob,
  type DetectionResult,
  type VideoEegSync,
} from "@/lib/video-detection";

const PLAYBACK_PREPARE_DEBOUNCE_MS = 350;

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
  playback,
  onPlaybackStateChange,
  onPlaybackRateChange,
  onBufferingChange,
  recordingDurationSeconds,
  seekRequest,
  compact = false,
}: {
  clips: DetectionJob[];
  selectedJobId: string;
  onSelectedJobIdChange: (jobId: string) => void;
  selectedEegTime: number | null;
  onEegTimeSelect: (seconds: number) => void;
  /** Optional owner-controlled EEG clock; video follows this clock. */
  playback?: SharedVideoPlayback;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackRateChange?: (rate: number) => void;
  onBufferingChange?: (isBuffering: boolean) => void;
  recordingDurationSeconds: number;
  seekRequest: VideoSeekRequest | null;
  compact?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoFrameRef = useRef<HTMLDivElement>(null);
  const appliedRequestRef = useRef<string | null>(null);
  const expectedProgrammaticSeekRef = useRef<number | null>(null);
  const pauseForUnmappedTime = useRef(false);
  const [bookmarks, setBookmarks] = useState<
    Array<{ jobId: string; seconds: number }>
  >([]);
  const [unavailableJobId, setUnavailableJobId] = useState<string | null>(null);
  const [bufferingJobId, setBufferingJobId] = useState<string | null>(null);
  const [retryingPlaybackJobId, setRetryingPlaybackJobId] = useState<
    string | null
  >(null);
  const [localPlaybackRate, setLocalPlaybackRate] = useState(1);
  const [blurMode, setBlurMode] = useState<"face+patches" | "face" | "all">(
    "face+patches",
  );
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [videoTimeState, setVideoTimeState] = useState<{
    jobId: string;
    time: number;
  } | null>(null);
  const [playbackJobOverrides, setPlaybackJobOverrides] = useState<
    Record<string, DetectionJob>
  >({});
  const [resultState, setResultState] = useState<{
    jobId: string;
    result: DetectionResult | null;
  } | null>(null);
  const selectedClipFromProps =
    clips.find((clip) => clip.job_id === selectedJobId) ?? clips[0];
  const selectedClip = selectedClipFromProps
    ? (playbackJobOverrides[selectedClipFromProps.job_id] ??
      selectedClipFromProps)
    : undefined;
  const selectedClipIndex = selectedClip
    ? clips.findIndex((clip) => clip.job_id === selectedClip.job_id)
    : -1;
  const sharedPlayback =
    selectedClip?.sync?.status === "linked" ? playback : undefined;
  const selectedJobIdForResult = selectedClip?.job_id;
  const selectedStatusForResult = selectedClip?.status;
  const selectedJobIsReferenceOnly = selectedClip?.reference_only === true;
  const selectedClipJobId = selectedClip?.job_id;
  const selectedClipPlaybackStatus = selectedClip?.playback_status;
  const selectedClipIsReferenceOnly = selectedClip?.reference_only === true;
  const authoritativeEegTime = sharedPlayback?.timeSeconds ?? selectedEegTime;
  const hasSharedPlayback = sharedPlayback !== undefined;
  const latestPlaybackRef = useRef(sharedPlayback);
  const latestClipRef = useRef(selectedClip);
  const latestEegTimeRef = useRef(authoritativeEegTime);
  useLayoutEffect(() => {
    latestPlaybackRef.current = sharedPlayback;
    latestClipRef.current = selectedClip;
    latestEegTimeRef.current = authoritativeEegTime;
  }, [authoritativeEegTime, selectedClip, sharedPlayback]);
  const isBuffering = bufferingJobId === selectedClip?.job_id;
  const currentVideoTime =
    videoTimeState?.jobId === selectedClip?.job_id
      ? (videoTimeState?.time ?? 0)
      : 0;
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

  useEffect(() => {
    const initialStatus = selectedClipPlaybackStatus ?? "";
    if (
      !selectedClipIsReferenceOnly ||
      !selectedClipJobId ||
      ![
        "metadata_pending",
        "metadata_checking",
        "conversion_required",
        "processing",
      ].includes(initialStatus)
    )
      return;
    const controller = new AbortController();
    const jobId = selectedClipJobId;
    let cancelled = false;
    let waitingForPlayer = false;
    queueMicrotask(() => {
      if (!cancelled) onBufferingChange?.(true);
    });

    const refresh = (job: DetectionJob) => {
      if (!cancelled) {
        setPlaybackJobOverrides((current) => ({ ...current, [jobId]: job }));
      }
      return job;
    };
    const waitForNextPoll = () =>
      new Promise<void>((resolve) => window.setTimeout(resolve, 900));

    void (async () => {
      try {
        let job = latestClipRef.current;
        if (!job) return;
        while (
          ["metadata_pending", "metadata_checking"].includes(
            job.playback_status ?? "",
          )
        ) {
          await waitForNextPoll();
          if (controller.signal.aborted) return;
          job = refresh((await getDetection(jobId, controller.signal)).job);
        }
        if (
          job.playback_status === "conversion_required" ||
          job.playback_status === "processing"
        ) {
          // Avoid queueing copies for clips the owner leaves during rapid seeks.
          await new Promise<void>((resolve) =>
            window.setTimeout(resolve, PLAYBACK_PREPARE_DEBOUNCE_MS),
          );
          if (controller.signal.aborted) return;
          // The owner-open request also promotes an already queued background
          // prewarm, so this clip is not stuck behind the rest of the folder.
          job = refresh(
            (await prepareReferencePlayback(jobId, controller.signal)).job,
          );
        }
        while (job.playback_status === "processing") {
          await waitForNextPoll();
          if (controller.signal.aborted) return;
          job = refresh((await getDetection(jobId, controller.signal)).job);
        }
        if (
          job.playback_status === "direct" ||
          job.playback_status === "ready"
        ) {
          waitingForPlayer = true;
          setUnavailableJobId(null);
        } else if (
          job.playback_status === "failed" ||
          job.playback_status === "unavailable"
        ) {
          setUnavailableJobId(jobId);
        }
      } catch {
        if (!controller.signal.aborted) setUnavailableJobId(jobId);
      } finally {
        if (!controller.signal.aborted && !waitingForPlayer) {
          setBufferingJobId(null);
          onBufferingChange?.(false);
        }
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [
    onBufferingChange,
    selectedClipJobId,
    selectedClipIsReferenceOnly,
    selectedClipPlaybackStatus,
  ]);
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

  const noSynchronizedVideoAtSelectedTime =
    sharedPlayback !== undefined &&
    authoritativeEegTime !== null &&
    videoTimeForEegTime(
      selectedClip?.sync?.mapped_segments,
      authoritativeEegTime,
    ) === null;

  useEffect(() => {
    if (!hasSharedPlayback || authoritativeEegTime === null) return;
    const covering = timeline.find(
      (segment) =>
        videoTimeForEegTime([segment], authoritativeEegTime) !== null,
    );
    if (covering && covering.clip.job_id !== selectedClip?.job_id) {
      pauseForUnmappedTime.current = true;
      onSelectedJobIdChange(covering.clip.job_id);
      return;
    }
    if (
      selectedClip?.sync?.status === "linked" &&
      videoTimeForEegTime(
        selectedClip.sync.mapped_segments,
        authoritativeEegTime,
      ) === null
    ) {
      pauseForUnmappedTime.current = true;
      videoRef.current?.pause();
      onBufferingChange?.(false);
      return;
    }
    pauseForUnmappedTime.current = false;
  }, [
    authoritativeEegTime,
    onBufferingChange,
    onSelectedJobIdChange,
    selectedClip?.job_id,
    selectedClip?.sync,
    hasSharedPlayback,
    timeline,
  ]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !selectedClip?.video_available) return;

    const currentEegTime = latestEegTimeRef.current;
    const currentPlayback = latestPlaybackRef.current;
    const seek =
      currentPlayback && currentEegTime !== null
        ? videoTimeForEegTime(
            selectedClip.sync?.mapped_segments,
            currentEegTime,
          )
        : seekRequest?.jobId === selectedClip.job_id
          ? seekRequest.videoSeconds
          : null;
    if (seek === null) return;
    if (video.readyState < HTMLMediaElement.HAVE_METADATA) return;

    // The request id changes only for a clinician seek or clip switch. The
    // source-clock ticker no longer forces a media seek on every React render.
    const requestId = currentPlayback
      ? `${selectedClip.job_id}:${currentPlayback.requestId}`
      : `${seekRequest?.jobId ?? ""}:${seekRequest?.requestId ?? ""}`;
    const isNewRequest = requestId !== appliedRequestRef.current;
    let seekTimer: number | undefined;
    if (Math.abs(video.currentTime - seek) > (isNewRequest ? 0.05 : 0.5)) {
      // Rapid EEG seeks can otherwise make the browser decode and fetch every
      // intermediate video position. Keep the newest target and issue one seek.
      seekTimer = window.setTimeout(() => {
        if (
          videoRef.current !== video ||
          video.readyState < HTMLMediaElement.HAVE_METADATA
        )
          return;
        const boundedSeek = Math.max(0, Math.min(video.duration, seek));
        expectedProgrammaticSeekRef.current = boundedSeek;
        video.currentTime = boundedSeek;
        appliedRequestRef.current = requestId;
      }, 75);
    } else {
      appliedRequestRef.current = requestId;
    }

    if (currentPlayback) {
      if (video.playbackRate !== currentPlayback.playbackRate)
        video.playbackRate = currentPlayback.playbackRate;
      if (currentPlayback.isPlaying && video.paused)
        void video.play().catch(() => onPlaybackStateChange?.(false));
      if (!currentPlayback.isPlaying && !video.paused) video.pause();
    }
    return () => {
      if (seekTimer !== undefined) window.clearTimeout(seekTimer);
    };
  }, [
    onPlaybackStateChange,
    seekRequest?.requestId,
    seekRequest?.jobId,
    seekRequest?.videoSeconds,
    selectedClip?.job_id,
    selectedClip?.sync?.mapped_segments,
    selectedClip?.video_available,
    sharedPlayback?.isPlaying,
    sharedPlayback?.playbackRate,
    sharedPlayback?.requestId,
  ]);

  useEffect(() => {
    if (!hasSharedPlayback) return;
    const timer = window.setInterval(() => {
      const playbackState = latestPlaybackRef.current;
      const clip = latestClipRef.current;
      const video = videoRef.current;
      if (
        !playbackState?.isPlaying ||
        !clip?.video_available ||
        !video ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        video.seeking
      )
        return;
      const desired = videoTimeForEegTime(
        clip.sync?.mapped_segments,
        playbackState.timeSeconds,
      );
      if (desired === null || Math.abs(video.currentTime - desired) <= 0.4)
        return;
      expectedProgrammaticSeekRef.current = desired;
      video.currentTime = Math.max(0, Math.min(video.duration, desired));
    }, 250);
    return () => window.clearInterval(timer);
  }, [hasSharedPlayback, selectedClip?.job_id]);

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
    resultState?.jobId === selectedClip?.job_id
      ? (resultState?.result ?? null)
      : null;
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

  const retryReferencePlayback = async () => {
    const jobId = selectedClip?.job_id;
    if (!jobId || retryingPlaybackJobId === jobId) return;
    setRetryingPlaybackJobId(jobId);
    setUnavailableJobId(null);
    setBufferingJobId(jobId);
    onBufferingChange?.(true);
    try {
      const { job } = await prepareReferencePlayback(jobId);
      setPlaybackJobOverrides((current) => ({ ...current, [jobId]: job }));
      if (job.playback_status !== "processing") {
        setBufferingJobId(null);
        onBufferingChange?.(false);
      }
    } catch {
      setUnavailableJobId(jobId);
      setBufferingJobId(null);
      onBufferingChange?.(false);
    } finally {
      setRetryingPlaybackJobId((current) =>
        current === jobId ? null : current,
      );
    }
  };

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
              The protected video could not be loaded. Check that your session
              is active and that the clip is available.
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
                    src={
                      selectedClip.reference_only
                        ? referencePlaybackUrl(selectedClip.job_id)
                        : detectionVisualizationUrl(selectedClip.job_id)
                    }
                    controls
                    controlsList="nofullscreen"
                    playsInline
                    preload="metadata"
                    crossOrigin="use-credentials"
                    data-testid="synchronized-video-player"
                    aria-label={`${clipLabel(selectedClip, selectedClipIndex)}, ${unblurred ? "unblurred owner-only" : blurMode === "all" ? "full-frame blurred" : selectiveBlurLabel.toLocaleLowerCase()} review video`}
                    onLoadedMetadata={(event) => {
                      setBufferingJobId(null);
                      onBufferingChange?.(false);
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
                        const boundedSeek = Math.max(
                          0,
                          Math.min(video.duration, seek),
                        );
                        expectedProgrammaticSeekRef.current = boundedSeek;
                        video.currentTime = boundedSeek;
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
                      setVideoTimeState({
                        jobId: selectedClip.job_id,
                        time: event.currentTarget.currentTime,
                      });
                    }}
                    onLoadStart={() => {
                      setBufferingJobId(selectedClip.job_id);
                      onBufferingChange?.(true);
                    }}
                    onWaiting={() => {
                      setBufferingJobId(selectedClip.job_id);
                      onBufferingChange?.(true);
                    }}
                    onCanPlay={() => {
                      setBufferingJobId(null);
                      onBufferingChange?.(false);
                    }}
                    onPlaying={() => {
                      setBufferingJobId(null);
                      onBufferingChange?.(false);
                    }}
                    onSeeking={(event) => {
                      const expected = expectedProgrammaticSeekRef.current;
                      const currentTime = event.currentTarget.currentTime;
                      if (
                        expected !== null &&
                        Math.abs(expected - currentTime) < 0.25
                      )
                        return;
                      // A manual seek can supersede a pending programmatic seek.
                      // Clear that expectation before its seeked event arrives.
                      expectedProgrammaticSeekRef.current = null;
                      setBufferingJobId(selectedClip.job_id);
                      onBufferingChange?.(true);
                    }}
                    onSeeked={(event) => {
                      setBufferingJobId(null);
                      onBufferingChange?.(false);
                      const videoSeconds = event.currentTarget.currentTime;
                      setVideoTimeState({
                        jobId: selectedClip.job_id,
                        time: videoSeconds,
                      });
                      const expected = expectedProgrammaticSeekRef.current;
                      if (expected !== null) {
                        if (Math.abs(expected - videoSeconds) < 0.25)
                          expectedProgrammaticSeekRef.current = null;
                        // Ignore a completion from a seek that was superseded
                        // by a newer EEG target; it must not rewind EEG time.
                        return;
                      }
                      const eegTime = eegTimeForVideoTime(
                        selectedClip.sync?.mapped_segments,
                        videoSeconds,
                      );
                      if (eegTime !== null) onEegTimeSelect(eegTime);
                    }}
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
                    onError={() => {
                      setUnavailableJobId(selectedClip.job_id);
                      if (sharedPlayback) onPlaybackStateChange?.(false);
                      onBufferingChange?.(false);
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
              {selectedClip.reference_only &&
              ["metadata_pending", "metadata_checking"].includes(
                selectedClip.playback_status ?? "",
              )
                ? "Checking the video clock and playback format"
                : selectedClip.reference_only &&
                    ["conversion_required", "processing"].includes(
                      selectedClip.playback_status ?? "",
                    )
                  ? "Preparing this video for playback"
                  : selectedClip.playback_status === "unavailable" ||
                      selectedClip.playback_status === "failed" ||
                      selectedClip.status === "failed"
                    ? "No playable review video is available"
                    : "Video is not available"}
            </p>
            <p className="mt-1 text-sm leading-6 text-ink-muted">
              {selectedClip.reference_only &&
              ["metadata_pending", "metadata_checking"].includes(
                selectedClip.playback_status ?? "",
              )
                ? "The encrypted original is saved. Its source clock and browser compatibility are being checked; OpenPose and VSViG are not run."
                : selectedClip.reference_only &&
                    selectedClip.playback_status === "processing"
                  ? "This opened clip is prioritized for browser playback. The encrypted original stays retained; OpenPose and VSViG are not run."
                  : selectedClip.reference_only &&
                      selectedClip.playback_status === "conversion_required"
                    ? "The encrypted original is retained. A browser-compatible review copy will be prepared automatically; no video-model inference runs."
                    : (selectedClip.playback_error ??
                      "The clip cannot be played here. EEG and synchronization status remain available.")}
            </p>
            {selectedClip.reference_only &&
              selectedClip.playback_status === "failed" &&
              selectedClip.source_available && (
                <button
                  className="mt-3 min-h-9 rounded border border-rule-strong px-3 text-sm font-semibold text-ink"
                  type="button"
                  disabled={retryingPlaybackJobId === selectedClip.job_id}
                  onClick={retryReferencePlayback}
                >
                  {retryingPlaybackJobId === selectedClip.job_id
                    ? "Retrying playback preparation…"
                    : "Retry playback preparation"}
                </button>
              )}
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
            EEG {formatRelativeTime(authoritativeEegTime ?? 0)} · Video{" "}
            {String(selectedClipIndex + 1).padStart(2, "0")} ·{" "}
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
