"use client";

import Link from "next/link";
import { Dialog } from "radix-ui";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiMediaUrl, getRecording, getResult, getSession } from "@/lib/api";
import {
  listDetections,
  videoTimeForEegTime,
  type DetectionJob,
} from "@/lib/video-detection";
import type {
  AnalysisResult,
  PredictionLabel,
  Recording,
  Session,
} from "@/lib/types";
import { Icon } from "./Icon";
import { LoadingOrb } from "./LoadingOrb";
import { RecordingNavigator } from "./RecordingNavigator";
import { PredictionTimeline } from "./PredictionTimeline";
import { SignalViewer, type SignalSeekRequest } from "./SignalViewer";
import { SourceClockTimeline } from "./SourceClockTimeline";
import { SyncedVideoReview, type VideoSeekRequest } from "./SyncedVideoReview";
import { formatRelativeTime } from "@/lib/format";

/** Render one recording result within its session-scoped navigation context. */
export function ResultScreen({ recordId }: { recordId: string }) {
  return <ResultContent key={recordId} recordId={recordId} />;
}

/** Load and render a fresh result whenever the selected recording changes. */
function ResultContent({ recordId }: { recordId: string }) {
  const [sourceOnly, setSourceOnly] = useState<Recording | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [caseVideoJobs, setCaseVideoJobs] = useState<DetectionJob[]>([]);
  const [videoDialogOpen, setVideoDialogOpen] = useState(false);
  const [playbackPlaying, setPlaybackPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [playbackRequestId, setPlaybackRequestId] = useState(0);
  const [selectedVideoJobId, setSelectedVideoJobId] = useState<string | null>(
    null,
  );
  const [videoSeekRequest, setVideoSeekRequest] =
    useState<VideoSeekRequest | null>(null);
  const [selectedEegTimeOverride, setSelectedEegTimeOverride] = useState<
    number | null | undefined
  >(undefined);
  const [signalSeekRequest, setSignalSeekRequest] =
    useState<SignalSeekRequest | null>(null);
  const videoSeekRequestId = useRef(0);
  const signalSeekRequestId = useRef(0);
  const playbackTimeRef = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      try {
        const nextResult = await getResult(recordId, controller.signal);
        if (controller.signal.aborted) return;
        setResult(nextResult);
        try {
          const nextSession = await getSession(
            nextResult.sessionId,
            controller.signal,
          );
          if (!controller.signal.aborted) setSession(nextSession);
        } catch (sessionError) {
          if (
            sessionError instanceof DOMException &&
            sessionError.name === "AbortError"
          )
            return;
        }
      } catch (loadError: unknown) {
        try {
          const recording = await getRecording(recordId, controller.signal);
          if (
            !controller.signal.aborted &&
            recording.status === "failed" &&
            recording.sourceAvailable
          ) {
            setSourceOnly(recording);
            return;
          }
        } catch {
          /* The original request error remains actionable. */
        }

        if (
          loadError instanceof DOMException &&
          loadError.name === "AbortError"
        )
          return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "The result could not be loaded.",
        );
      }
    };
    void load();
    return () => controller.abort();
  }, [recordId]);

  useEffect(() => {
    if (!result || !session?.caseId) return;
    const controller = new AbortController();
    void listDetections(controller.signal)
      .then(({ jobs }) => {
        if (controller.signal.aborted) return;
        const caseJobs = jobs
          .filter((job) => job.case_id === session.caseId)
          .sort((left, right) =>
            left.created_at.localeCompare(right.created_at),
          );
        setCaseVideoJobs(caseJobs);
      })
      .catch((loadError: unknown) => {
        if (
          loadError instanceof DOMException &&
          loadError.name === "AbortError"
        )
          return;
        setCaseVideoJobs([]);
      });
    return () => controller.abort();
  }, [result, session?.caseId]);

  const linkedVideoClips = caseVideoJobs
    .filter(
      (job) =>
        job.sync?.status !== "linked" ||
        job.sync.record_id === result?.recordId,
    )
    .sort(
      (left, right) =>
        (left.sync?.eeg_source_start_seconds ?? 0) -
        (right.sync?.eeg_source_start_seconds ?? 0),
    );

  const firstFlag = result?.predictionWindows.find(
    (window) => window.seizureDetected,
  );
  const defaultEegTime = firstFlag
    ? (firstFlag.startSeconds + firstFlag.endSeconds) / 2
    : result?.annotationEvents[0]?.onsetSeconds;
  const selectedEegTime =
    selectedEegTimeOverride === undefined
      ? (defaultEegTime ?? null)
      : selectedEegTimeOverride;
  const mappedVideoClip =
    selectedEegTime === null
      ? null
      : (linkedVideoClips.find(
          (job) =>
            videoTimeForEegTime(job.sync?.mapped_segments, selectedEegTime) !==
            null,
        ) ?? null);

  const selectEegTime = useCallback(
    (seconds: number) => {
      const boundedSeconds = Math.max(
        0,
        Math.min(result?.recordingDurationSeconds ?? seconds, seconds),
      );
      playbackTimeRef.current = boundedSeconds;
      setSelectedEegTimeOverride(boundedSeconds);
      setPlaybackRequestId((current) => current + 1);
      setSignalSeekRequest({
        timeSeconds: boundedSeconds,
        requestId: ++signalSeekRequestId.current,
      });
      const clip = linkedVideoClips.find(
        (job) =>
          videoTimeForEegTime(job.sync?.mapped_segments, boundedSeconds) !==
          null,
      );
      const videoSeconds = clip?.sync
        ? videoTimeForEegTime(clip.sync.mapped_segments, boundedSeconds)
        : null;
      if (!clip || videoSeconds === null) {
        setVideoSeekRequest(null);
        return;
      }
      setSelectedVideoJobId(clip.job_id);
      setVideoSeekRequest({
        jobId: clip.job_id,
        videoSeconds,
        requestId: ++videoSeekRequestId.current,
      });
    },
    [linkedVideoClips, result?.recordingDurationSeconds],
  );

  const updatePlaybackTime = useCallback((seconds: number) => {
    playbackTimeRef.current = seconds;
    setSelectedEegTimeOverride(seconds);
  }, []);

  const updatePlaybackState = useCallback((isPlaying: boolean) => {
    setPlaybackPlaying(isPlaying);
  }, []);

  const updateLegacyPlaybackTime = useCallback((seconds: number | null) => {
    if (seconds === null) return;
    playbackTimeRef.current = seconds;
    setSelectedEegTimeOverride(seconds);
  }, []);

  useEffect(() => {
    if (!result || !playbackPlaying) return;
    if (videoDialogOpen && mappedVideoClip?.video_available) return;
    let previousFrame = performance.now();
    let frameId = 0;
    const advance = (now: number) => {
      const elapsedSeconds = (now - previousFrame) / 1000;
      previousFrame = now;
      const nextTime = Math.min(
        result.recordingDurationSeconds,
        playbackTimeRef.current + elapsedSeconds * playbackRate,
      );
      playbackTimeRef.current = nextTime;
      setSelectedEegTimeOverride(nextTime);
      if (nextTime >= result.recordingDurationSeconds) {
        setPlaybackPlaying(false);
        return;
      }
      frameId = requestAnimationFrame(advance);
    };
    frameId = requestAnimationFrame(advance);
    return () => cancelAnimationFrame(frameId);
  }, [
    mappedVideoClip?.job_id,
    mappedVideoClip?.video_available,
    playbackPlaying,
    playbackRate,
    result,
    videoDialogOpen,
  ]);

  const startPlayback = () => {
    if (!result) return;
    const startAt =
      selectedEegTime === null ||
      selectedEegTime >= result.recordingDurationSeconds
        ? 0
        : selectedEegTime;
    selectEegTime(startAt);
    setPlaybackPlaying(true);
  };

  if (sourceOnly)
    return (
      <div className="page-frame">
        <h1 className="text-2xl font-semibold">
          {sourceOnly.displayName} · source review
        </h1>
        <p className="my-4 text-sm text-ink-muted">
          Analysis unavailable. The original recording remains available for
          owner review.
        </p>
        <div className="mb-4 flex gap-4 text-sm">
          <a
            className="underline"
            href={apiMediaUrl(
              `/api/recordings/${encodeURIComponent(recordId)}/original`,
            )}
          >
            Download original EEG
          </a>
          {sourceOnly.sessionId && (
            <a
              className="underline"
              href={apiMediaUrl(
                `/api/sessions/${encodeURIComponent(sourceOnly.sessionId)}/original`,
              )}
            >
              Download original archive
            </a>
          )}
        </div>
        <SignalViewer
          recordId={recordId}
          predictionWindows={[]}
          recordingDurationSeconds={sourceOnly.durationSeconds ?? 10}
          selectedEegTime={selectedEegTimeOverride ?? 0}
          selectionRequest={signalSeekRequest}
          onEegTimeSelect={selectEegTime}
        />
      </div>
    );
  if (error) return <ResultError message={error} />;
  if (!result)
    return (
      <div className="page-frame">
        <div className="flex min-h-56 items-center justify-center px-5 py-12">
          <LoadingOrb
            label="Loading recording review…"
            state="searching"
            size={64}
          />
        </div>
      </div>
    );

  const copy = predictionCopy(result.prediction, result.scoreType);
  const calibrated = result.scoreType === "calibrated_probability";
  const toneClass =
    copy.tone === "red"
      ? "text-red"
      : copy.tone === "amber"
        ? "text-amber"
        : "text-teal-dark";

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link
          className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
          href={"/sessions/" + encodeURIComponent(result.sessionId)}
        >
          <Icon name="back" className="size-4" />
          Back to session
        </Link>

        <header className="mt-4 border-b border-rule pb-4">
          <h1
            id="result-heading"
            className="text-[clamp(1.6rem,3vw,2rem)] font-semibold leading-tight tracking-[-0.03em] text-ink"
          >
            {result.recordingLabel}
          </h1>
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            {session?.sourceAvailable && (
              <a
                className="underline"
                href={apiMediaUrl(
                  `/api/recordings/${encodeURIComponent(result.recordId)}/original`,
                )}
              >
                Download original EEG
              </a>
            )}
            {session?.sourceAvailable && (
              <a
                className="underline"
                href={apiMediaUrl(
                  `/api/sessions/${encodeURIComponent(result.sessionId)}/original`,
                )}
              >
                Download original archive
              </a>
            )}
          </div>
          {session?.sourceAvailable && (
            <a
              className="mt-2 inline-block text-sm underline"
              href={apiMediaUrl(
                `/api/sessions/${encodeURIComponent(result.sessionId)}/original-report`,
              )}
            >
              Download original report, if included
            </a>
          )}
          {session && !session.sourceAvailable && (
            <p className="mt-2 text-xs text-ink-muted">
              Original sources unavailable. Previously deleted originals cannot
              be recovered.
            </p>
          )}
          {session?.retentionPolicy === "until-deletion" && (
            <p className="mt-2 text-xs text-ink-muted">
              Encrypted sources and results remain available until you delete
              this case.
            </p>
          )}
        </header>

        <div className="mt-5 space-y-5">
          {session && session.recordings.length > 1 && (
            <RecordingNavigator
              session={session}
              activeRecordId={result.recordId}
            />
          )}

          <section
            className="panel overflow-hidden"
            aria-labelledby="shared-timeline-heading"
          >
            <div className="border-b border-rule px-4 py-3 sm:px-6">
              <h2
                id="shared-timeline-heading"
                className="text-base font-bold tracking-[-0.015em]"
              >
                Shared timeline
              </h2>
            </div>
            <SourceClockTimeline
              predictions={result.predictionWindows}
              events={result.annotationEvents}
              clips={linkedVideoClips}
              durationSeconds={result.recordingDurationSeconds}
              selectedEegTime={selectedEegTime}
              onSelectEegTime={selectEegTime}
            />
            <div className="flex flex-wrap items-center gap-2 border-b border-rule px-3 py-2 sm:px-4">
              <button
                className="min-h-10 rounded-md bg-teal-dark px-4 text-sm font-semibold text-white"
                type="button"
                onClick={
                  playbackPlaying
                    ? () => setPlaybackPlaying(false)
                    : startPlayback
                }
                aria-label={
                  playbackPlaying
                    ? "Pause EEG and video playback"
                    : "Play EEG and video"
                }
              >
                {playbackPlaying ? "Pause" : "Play"}
              </button>
              <button
                className="min-h-10 rounded-md border border-rule px-3 text-sm font-semibold"
                type="button"
                onClick={() => selectEegTime((selectedEegTime ?? 0) - 10)}
                aria-label="Seek EEG back 10 seconds"
              >
                −10 s
              </button>
              <button
                className="min-h-10 rounded-md border border-rule px-3 text-sm font-semibold"
                type="button"
                onClick={() => selectEegTime((selectedEegTime ?? 0) + 10)}
                aria-label="Seek EEG forward 10 seconds"
              >
                +10 s
              </button>
              <label className="flex min-h-10 items-center gap-2 text-xs font-semibold text-ink-muted">
                Speed
                <select
                  className="min-h-10 rounded-md border border-rule bg-surface px-2 text-sm text-ink"
                  aria-label="Shared playback speed"
                  value={playbackRate}
                  onChange={(event) =>
                    setPlaybackRate(Number(event.target.value))
                  }
                >
                  {[0.25, 0.5, 0.75, 1, 1.25, 1.5, 2].map((rate) => (
                    <option key={rate} value={rate}>
                      {rate}×
                    </option>
                  ))}
                </select>
              </label>
              <output
                className="ml-auto font-mono text-xs tabular-nums text-ink-muted"
                aria-label={`Current EEG recording time ${formatRelativeTime(selectedEegTime ?? 0)}`}
              >
                EEG {formatRelativeTime(selectedEegTime ?? 0)} ·{" "}
                {mappedVideoClip?.video_available
                  ? "Synchronized video"
                  : mappedVideoClip
                    ? "Matched clip unavailable"
                    : "No synchronized video coverage"}
              </output>
            </div>
            <div
              className={
                linkedVideoClips.length > 0
                  ? "grid min-w-0 xl:grid-cols-[minmax(0,1fr)_16rem]"
                  : "min-w-0"
              }
            >
              <div
                className={
                  linkedVideoClips.length > 0
                    ? "min-w-0 border-b border-rule xl:border-b-0 xl:border-r"
                    : "min-w-0"
                }
              >
                <section
                  role="region"
                  aria-label="EEG Viewer"
                  className="min-w-0"
                >
                  <SignalViewer
                    recordId={result.recordId}
                    predictionWindows={result.predictionWindows}
                    recordingDurationSeconds={result.recordingDurationSeconds}
                    selectedEegTime={selectedEegTime}
                    selectionRequest={
                      signalSeekRequest ??
                      (selectedEegTime === null
                        ? null
                        : { timeSeconds: selectedEegTime, requestId: 0 })
                    }
                    onEegTimeSelect={selectEegTime}
                    embedded
                  />
                </section>
              </div>
              {linkedVideoClips.length > 0 && (
                <aside className="min-w-0 border-t border-rule p-3 xl:border-l xl:border-t-0">
                  <Dialog.Root
                    open={videoDialogOpen}
                    modal={false}
                    onOpenChange={setVideoDialogOpen}
                  >
                    <label className="flex min-h-10 cursor-pointer items-center gap-2 text-xs font-semibold text-ink-muted">
                      <input
                        className="size-4 accent-teal"
                        type="checkbox"
                        checked={videoDialogOpen}
                        onChange={(event) =>
                          setVideoDialogOpen(event.target.checked)
                        }
                      />
                      Show synchronized video popup
                    </label>
                    <Dialog.Portal>
                      <Dialog.Content
                        onInteractOutside={(event) => event.preventDefault()}
                        className="fixed inset-x-2 bottom-4 z-50 max-h-[45vh] overflow-auto rounded-xl border border-rule bg-surface p-3 shadow-2xl sm:inset-x-auto sm:bottom-auto sm:right-4 sm:top-20 sm:max-h-[min(82vh,560px)] sm:w-[min(480px,calc(100vw-2rem))]"
                      >
                        <div className="mb-4 flex items-center justify-between">
                          <Dialog.Title className="font-semibold">
                            Synchronized video
                          </Dialog.Title>
                          <Dialog.Close className="min-h-9 rounded border border-rule px-3">
                            Close
                          </Dialog.Close>
                        </div>
                        <Dialog.Description className="sr-only">
                          Owner-only reference playback, synchronized when
                          metadata uniquely matches the EEG.
                        </Dialog.Description>
                        <SyncedVideoReview
                          clips={linkedVideoClips}
                          selectedJobId={
                            mappedVideoClip?.job_id ??
                            selectedVideoJobId ??
                            linkedVideoClips[0].job_id
                          }
                          onSelectedJobIdChange={(jobId) => {
                            setSelectedVideoJobId(jobId);
                            setVideoSeekRequest(null);
                          }}
                          selectedEegTime={selectedEegTime}
                          onEegTimeSelect={selectEegTime}
                          onPlaybackEegTime={updateLegacyPlaybackTime}
                          playback={{
                            timeSeconds: selectedEegTime ?? 0,
                            isPlaying: playbackPlaying,
                            playbackRate,
                            requestId: playbackRequestId,
                          }}
                          onPlaybackTimeChange={updatePlaybackTime}
                          onPlaybackStateChange={updatePlaybackState}
                          onPlaybackRateChange={setPlaybackRate}
                          recordingDurationSeconds={
                            result.recordingDurationSeconds
                          }
                          seekRequest={videoSeekRequest}
                          compact
                        />
                      </Dialog.Content>
                    </Dialog.Portal>
                  </Dialog.Root>
                </aside>
              )}
            </div>
          </section>

          <section
            className="panel overflow-hidden"
            aria-labelledby="model-decision-heading"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-4 py-3 sm:px-6">
              <div>
                <p className="eyebrow">
                  {result.modelName} · {result.modelVersion}
                </p>
                <h2
                  id="model-decision-heading"
                  className={"mt-1 text-base font-bold " + toneClass}
                >
                  {copy.title}
                </h2>
              </div>
              <p className="text-xs font-semibold text-ink-muted">
                {result.scoreType === "development_score"
                  ? "Development · not a diagnosis"
                  : calibrated
                    ? "Window estimate · not a diagnosis"
                    : "Uncalibrated · research only · not a diagnosis"}
              </p>
            </div>
            <dl className="grid gap-3 px-4 py-3 sm:grid-cols-3 sm:px-6">
              <div>
                <dt className="text-xs font-semibold text-ink-muted">
                  {calibrated ? "Peak window estimate" : "Peak window score"}
                </dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums text-ink">
                  {result.highestWindow?.score.toFixed(3) ?? "Unavailable"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-ink-muted">
                  Threshold
                </dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums text-ink">
                  {result.threshold.toFixed(3)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-ink-muted">
                  Flagged windows
                </dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums text-ink">
                  {result.flaggedWindowCount} / {result.windowCount}
                </dd>
              </div>
            </dl>
          </section>

          <section
            className="panel p-5"
            aria-labelledby="model-contribution-heading"
          >
            <h2 id="model-contribution-heading" className="font-semibold">
              Model contribution
            </h2>
            <p className="mt-2 text-sm text-ink-muted">
              Attribution describes the model score. It does not localize
              seizure origin.
            </p>
            {result.researchAttributions.length ? (
              result.researchAttributions.map((attribution) => (
                <div key={attribution.windowIndex} className="mt-4">
                  <button
                    type="button"
                    className="text-sm underline"
                    onClick={() =>
                      selectEegTime(attribution.windowStartSeconds)
                    }
                  >
                    Window {attribution.windowStartSeconds.toFixed(1)}–
                    {attribution.windowEndSeconds.toFixed(1)} s
                  </button>
                  <ol className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-xs">
                    {[...attribution.channelScores]
                      .sort(
                        (left, right) =>
                          right.meanAbsoluteAttribution -
                          left.meanAbsoluteAttribution,
                      )
                      .map((channel) => (
                        <li key={channel.label}>
                          {channel.label}:{" "}
                          {channel.meanAbsoluteAttribution.toPrecision(3)}
                        </li>
                      ))}
                  </ol>
                  <div className="mt-3 flex" aria-label="Time attribution">
                    {attribution.timeBins.map((bin) => {
                      const magnitude = bin.channelScores.reduce(
                        (sum, value) => sum + Math.abs(value),
                        0,
                      );
                      const peak = Math.max(
                        ...attribution.timeBins.map((item) =>
                          item.channelScores.reduce(
                            (sum, value) => sum + Math.abs(value),
                            0,
                          ),
                        ),
                        1e-12,
                      );
                      return (
                        <button
                          type="button"
                          key={bin.startSeconds}
                          className="h-8 flex-1 bg-teal"
                          style={{ opacity: 0.2 + (0.8 * magnitude) / peak }}
                          aria-label={`Model contribution at ${(attribution.windowStartSeconds + bin.startSeconds).toFixed(2)} seconds`}
                          title={`${(attribution.windowStartSeconds + bin.startSeconds).toFixed(2)} s · ${magnitude.toPrecision(3)}`}
                          onClick={() =>
                            selectEegTime(
                              attribution.windowStartSeconds + bin.startSeconds,
                            )
                          }
                        />
                      );
                    })}
                  </div>
                </div>
              ))
            ) : (
              <p className="mt-3 text-sm text-ink-muted">
                Attribution unavailable. A compatible model and reviewed
                background dataset are required; scores alone do not explain the
                model.
              </p>
            )}
          </section>

          <section
            className="panel overflow-hidden"
            aria-labelledby="prediction-timeline-heading"
          >
            <div className="border-b border-rule px-4 py-3 sm:px-6">
              <h2
                id="prediction-timeline-heading"
                className="text-base font-bold tracking-[-0.015em]"
              >
                Prediction score timeline
              </h2>
            </div>
            <div className="px-3 py-3 sm:px-5">
              <PredictionTimeline
                predictions={result.predictionWindows}
                durationSeconds={result.recordingDurationSeconds}
                threshold={result.threshold}
                scoreType={result.scoreType}
                selectedTimeSeconds={selectedEegTime}
                onTimeSelect={selectEegTime}
              />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

/** Render a concise headline that distinguishes development and reviewed output. */
function predictionCopy(
  prediction: PredictionLabel,
  scoreType: string,
): {
  title: string;
  tone: "teal" | "amber" | "red";
} {
  const development = scoreType === "development_score";
  const calibrated = scoreType === "calibrated_probability";
  if (prediction === "seizure")
    return {
      title: development
        ? "Development flag"
        : calibrated
          ? "Model alert"
          : "Research threshold flag",
      tone: calibrated ? "red" : "amber",
    };
  if (prediction === "no-seizure")
    return {
      title: "No flagged windows",
      tone: "teal",
    };
  return {
    title: "Incomplete result",
    tone: "amber",
  };
}

/** Render a recoverable result-loading error. */
function ResultError({ message }: { message: string }) {
  return (
    <div className="page-frame">
      <div
        className="max-w-xl rounded-lg border border-red/30 bg-red-soft px-5 py-6"
        role="alert"
      >
        <Icon name="alert" className="size-5 text-red" />
        <h1 className="mt-4 text-xl font-bold text-ink">Result unavailable</h1>
        <p className="mt-2 text-sm leading-6 text-red">{message}</p>
        <Link
          className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4"
          href="/sessions"
        >
          Return to EEG sessions <Icon name="arrow" className="size-4" />
        </Link>
      </div>
    </div>
  );
}
