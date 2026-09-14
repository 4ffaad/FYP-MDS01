"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import {
  detectionVideoUrl,
  getDetection,
  getDetectionResults,
  listDetections,
  uploadDetection,
  type DetectionJob,
  type DetectionResult,
} from "@/lib/video-detection";

const stageNames: Record<string, string> = {
  preflight: "Checking video",
  "pose-and-inference": "Extracting poses and scoring windows",
  "review-video": "Preparing review video",
  complete: "Ready for review",
  failed: "Processing stopped",
  expired: "Retention expired",
};

function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

export function VideoDetectionUploadScreen() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<DetectionJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const abort = new AbortController();

    listDetections(abort.signal)
      .then(({ jobs: detectedJobs }) => setJobs(detectedJobs))
      .catch((error: unknown) => {
        if (!abort.signal.aborted) {
          setError(
            error instanceof Error
              ? error.message
              : "Your video jobs could not be loaded.",
          );
        }
      });

    return () => abort.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;

    setBusy(true);
    setError(null);

    try {
      const { job } = await uploadDetection(file, setProgress);
      router.push(`/video-detection/${encodeURIComponent(job.job_id)}`);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "The video could not be submitted.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="page-frame">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-semibold tracking-tight">
          Video seizure detection
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">
          Upload a patient clip to review movement-based model scores and
          possible event intervals.
        </p>

        <form onSubmit={submit} className="panel mt-8 max-w-2xl space-y-5 p-6">
          <div>
            <label
              htmlFor="detection-video"
              className="block text-sm font-semibold"
            >
              Patient video
            </label>
            <p
              id="video-help"
              className="mt-2 text-sm leading-6 text-ink-muted"
            >
              MP4, MOV or WebM. Use a clip showing one patient. Face redaction
              runs before pose extraction and model scoring; audio is excluded.
              Your account owns this upload.
            </p>
            <input
              id="detection-video"
              aria-describedby="video-help"
              className="mt-4 block w-full text-sm file:mr-4 file:rounded-md file:border file:border-rule file:bg-surface-soft file:px-4 file:py-2"
              type="file"
              accept=".mp4,.mov,.webm"
              disabled={busy}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </div>

          <p className="text-sm leading-6 text-ink-muted">
            The source is encrypted immediately. The detector receives
            face-redacted frames and review playback is face-redacted and muted.
          </p>
          {error && (
            <p role="alert" className="text-sm text-red">
              {error}
            </p>
          )}
          {busy && (
            <p role="status" className="text-sm text-ink-muted">
              {progress < 100
                ? `Uploading ${progress}%`
                : "Validating and securing video…"}
            </p>
          )}

          <Button disabled={!file || busy} type="submit">
            <Icon
              name={busy ? "spinner" : "activity"}
              className={`size-4 ${busy ? "animate-spin" : ""}`}
            />
            {busy ? "Submitting…" : "Start detection"}
          </Button>
        </form>

        <section className="mt-10" aria-labelledby="recent-detections">
          <h2 id="recent-detections" className="text-lg font-semibold">
            Your video jobs
          </h2>
          {jobs.length ? (
            <ul className="mt-4 divide-y divide-rule border-y border-rule">
              {jobs.map((job) => (
                <li key={job.job_id}>
                  <Link
                    className="flex min-h-16 flex-wrap items-center justify-between gap-2 py-3 text-sm hover:text-teal"
                    href={`/video-detection/${job.job_id}`}
                  >
                    <span>{job.label}</span>
                    <span className="text-ink-muted">
                      {job.status.replaceAll("_", " ")}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-ink-muted">
              Submitted videos will appear here.
            </p>
          )}
        </section>

        <ResearchOnlyNotice />
      </div>
    </div>
  );
}

export function VideoDetectionJobScreen({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<DetectionJob | null>(null);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState(false);
  const [position, setPosition] = useState(0);
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const { job: nextJob } = await getDetection(jobId, abort.signal);
        if (abort.signal.aborted) return;

        setJob(nextJob);
        setResult(
          nextJob.status === "ready"
            ? await getDetectionResults(jobId, abort.signal)
            : null,
        );

        if (!["failed", "expired"].includes(nextJob.status)) {
          timer = setTimeout(poll, nextJob.status === "ready" ? 15_000 : 1_500);
        }
      } catch (error) {
        if (!abort.signal.aborted) {
          setError(
            error instanceof Error
              ? error.message
              : "The job could not be loaded.",
          );
        }
      }
    }

    void poll();
    return () => {
      abort.abort();
      clearTimeout(timer);
    };
  }, [jobId]);

  function seek(seconds: number) {
    if (!video.current) return;
    video.current.currentTime = seconds;
    setPosition(seconds);
    video.current.focus();
  }

  const duration = job?.duration_seconds || 1;

  return (
    <div className="page-frame">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/video-detection"
          className="text-sm text-teal hover:underline"
        >
          Video detection
        </Link>
        <h1 className="mt-5 text-3xl font-semibold tracking-tight">
          {job?.label ?? "Video review"}
        </h1>
        {error && (
          <p role="alert" className="mt-4 text-sm text-red">
            {error}
          </p>
        )}

        {!job ? (
          <p role="status" className="mt-6 text-sm">
            Loading video job…
          </p>
        ) : (
          <>
            <p role="status" className="mt-3 text-sm text-ink-muted">
              {stageNames[job.current_stage] ?? job.current_stage}
            </p>
            {job.error && (
              <p
                role="alert"
                className="mt-5 rounded-md border border-rule p-4 text-sm text-red"
              >
                {job.error}
              </p>
            )}
            {job.status === "expired" && (
              <p className="mt-5 text-sm">
                The retention period ended. Video and results have been removed.
              </p>
            )}

            <VideoReview
              job={job}
              jobId={jobId}
              playbackError={playbackError}
              video={video}
              onPlaybackError={() => {
                setPlaybackError(true);
                void getDetection(jobId).catch(() => {});
              }}
              onPositionChange={setPosition}
            />

            {result && (
              <>
                <PrivacyTreatment privacy={result.privacy} />
                <ScoreTimeline
                  result={result}
                  duration={duration}
                  position={position}
                />
                <FlaggedIntervals intervals={result.intervals} onSeek={seek} />
                <VideoEvidence
                  prediction={result.predictions.find(
                    (prediction) => prediction.model_evidence,
                  )}
                />
                <WindowScores predictions={result.predictions} onSeek={seek} />
                <ModelDetails model={result.model} />
              </>
            )}
          </>
        )}

        <ResearchOnlyNotice />
      </div>
    </div>
  );
}

function VideoReview({
  job,
  jobId,
  playbackError,
  video,
  onPlaybackError,
  onPositionChange,
}: {
  job: DetectionJob;
  jobId: string;
  playbackError: boolean;
  video: React.RefObject<HTMLVideoElement | null>;
  onPlaybackError: () => void;
  onPositionChange: (seconds: number) => void;
}) {
  if (!job.video_available || job.status !== "ready") return null;

  return (
    <section className="mt-7" aria-label="Private video review">
      <video
        ref={video}
        src={detectionVideoUrl(jobId) ?? undefined}
        crossOrigin="use-credentials"
        controls
        preload="metadata"
        muted
        playsInline
        aria-label="Patient video review"
        className="aspect-video w-full rounded-lg bg-black"
        onTimeUpdate={() => onPositionChange(video.current?.currentTime ?? 0)}
        onError={onPlaybackError}
      />
      {playbackError && (
        <p role="alert" className="mt-2 text-sm text-red">
          Playback is unavailable. Refresh to check your session and the video
          retention period.
        </p>
      )}
      <p className="mt-2 text-xs text-ink-muted">
        Face-redacted private review · Audio removed · Available until{" "}
        {new Date(job.retention_expires_at).toLocaleString()}
      </p>
    </section>
  );
}

function PrivacyTreatment({
  privacy,
}: {
  privacy: DetectionResult["privacy"];
}) {
  return (
    <section className="panel mt-6 p-5" aria-labelledby="video-privacy-heading">
      <h2 id="video-privacy-heading" className="text-base font-semibold">
        Privacy treatment
      </h2>
      {privacy ? (
        <>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Face redaction ran before pose extraction and VSViG scoring. The
            model and this review video use the protected frames; the source
            remains encrypted and is removed after processing.
          </p>
          {privacy.quality_flags.length ? (
            <p className="mt-3 rounded-md bg-amber-soft px-3 py-2 text-xs leading-5 text-amber">
              Face detection was intermittent, so full-frame blur protected
              affected frames. Review this result carefully before relying on
              it.
            </p>
          ) : (
            <p className="mt-3 text-xs text-ink-muted">
              Face redaction coverage:{" "}
              {Math.round(privacy.face_detection_coverage * 100)}%
            </p>
          )}
        </>
      ) : (
        <p className="mt-2 text-sm leading-6 text-amber">
          Privacy provenance is unavailable for this legacy job. Do not treat
          its review video as de-identified.
        </p>
      )}
    </section>
  );
}

function ScoreTimeline({
  result,
  duration,
  position,
}: {
  result: DetectionResult;
  duration: number;
  position: number;
}) {
  const { model, predictions } = result;
  const flaggedWindows = predictions.filter(
    (prediction) => prediction.seizure_detected,
  ).length;

  return (
    <section className="panel mt-6 p-5" aria-labelledby="score-heading">
      <h2 id="score-heading" className="text-base font-semibold">
        Uncalibrated model score
      </h2>
      <p className="mt-2 text-sm leading-6 text-ink-muted">
        Each point covers {(model.window_frames / model.sample_fps).toFixed(2)}{" "}
        seconds, stepping {(model.stride_frames / model.sample_fps).toFixed(2)}{" "}
        seconds. Scores are not calibrated probabilities.
      </p>
      <svg
        viewBox="0 0 900 190"
        role="img"
        aria-label={`Window scores from 0 to 1. Threshold ${model.threshold}.`}
        className="mt-4 w-full overflow-visible"
      >
        {[0, 0.5, 1].map((tick) => (
          <g key={tick}>
            <line
              x1="35"
              x2="875"
              y1={155 - tick * 130}
              y2={155 - tick * 130}
              stroke="currentColor"
              opacity="0.12"
            />
            <text x="0" y={160 - tick * 130} fontSize="12" fill="currentColor">
              {tick.toFixed(1)}
            </text>
          </g>
        ))}
        <line
          x1="35"
          x2="875"
          y1={155 - model.threshold * 130}
          y2={155 - model.threshold * 130}
          stroke="var(--color-amber, #8a5a00)"
          strokeDasharray="5 5"
        />
        <polyline
          fill="none"
          stroke="var(--color-teal, #0066cc)"
          strokeWidth="2"
          points={predictions
            .map(
              (prediction) =>
                `${35 + ((prediction.start_time + prediction.end_time) / 2 / duration) * 840},${155 - prediction.score * 130}`,
            )
            .join(" ")}
        />
        <line
          x1={35 + (position / duration) * 840}
          x2={35 + (position / duration) * 840}
          y1="20"
          y2="160"
          stroke="currentColor"
          opacity="0.6"
        />
        <text x="35" y="185" fontSize="12" fill="currentColor">
          0:00
        </text>
        <text
          x="875"
          y="185"
          textAnchor="end"
          fontSize="12"
          fill="currentColor"
        >
          {formatTime(duration)}
        </text>
      </svg>
      <p className="mt-2 text-xs text-ink-muted">
        Dashed line: research threshold {model.threshold.toFixed(2)} ·{" "}
        {flaggedWindows} of {predictions.length} windows flagged
      </p>
    </section>
  );
}

function FlaggedIntervals({
  intervals,
  onSeek,
}: {
  intervals: DetectionResult["intervals"];
  onSeek: (seconds: number) => void;
}) {
  return (
    <section className="mt-7" aria-labelledby="interval-heading">
      <h2 id="interval-heading" className="text-lg font-semibold">
        Flagged intervals
      </h2>
      <p className="mt-2 text-sm text-ink-muted">
        Select an interval to review the corresponding video.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        {intervals.length ? (
          intervals.map((interval, index) => (
            <Button
              variant="outline"
              key={interval.start_time}
              onClick={() => onSeek(interval.start_time)}
            >
              Event {index + 1} · {formatTime(interval.start_time)}–
              {formatTime(interval.end_time)}
            </Button>
          ))
        ) : (
          <p className="text-sm text-ink-muted">
            No windows crossed the configured threshold. This does not rule out
            a seizure.
          </p>
        )}
      </div>
    </section>
  );
}

function WindowScores({
  predictions,
  onSeek,
}: {
  predictions: DetectionResult["predictions"];
  onSeek: (seconds: number) => void;
}) {
  return (
    <details className="mt-7 border-y border-rule py-4">
      <summary className="cursor-pointer text-sm font-semibold">
        All window scores
      </summary>
      <div className="mt-4 max-h-72 overflow-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr>
              <th className="py-2">Window</th>
              <th>Score</th>
              <th>Flagged</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((prediction) => (
              <tr key={prediction.start_time} className="border-t border-rule">
                <td>
                  <button
                    className="min-h-11 text-teal hover:underline"
                    onClick={() => onSeek(prediction.start_time)}
                  >
                    {formatTime(prediction.start_time)}–
                    {formatTime(prediction.end_time)}
                  </button>
                </td>
                <td>{prediction.score.toFixed(3)}</td>
                <td>{prediction.seizure_detected ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function ModelDetails({ model }: { model: DetectionResult["model"] }) {
  const details = {
    Model: model.model_name,
    Version: model.model_version,
    Checkpoint: model.weights_hash,
    Preprocessing: model.preprocessing_version,
    Threshold: model.threshold,
  };

  return (
    <details className="mt-4 border-b border-rule pb-4">
      <summary className="cursor-pointer text-sm font-semibold">
        Model and processing details
      </summary>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-[160px_1fr]">
        {Object.entries(details).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-ink-muted">{key}</dt>
            <dd className="break-all">{value}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function VideoEvidence({
  prediction,
}: {
  prediction: DetectionResult["predictions"][number] | undefined;
}) {
  const evidence = prediction?.model_evidence;

  if (!evidence || !prediction) {
    return (
      <section
        className="panel mt-7 p-5"
        aria-labelledby="video-evidence-heading"
      >
        <h2 id="video-evidence-heading" className="text-base font-semibold">
          Model evidence
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          No input-sensitivity attribution is available because this result has
          no flagged window. Window scores and intervals remain available for
          review.
        </p>
      </section>
    );
  }

  const maxScoreChange = Math.max(
    ...evidence.patches.map((patch) => Math.abs(patch.score_change)),
    1e-9,
  );

  return (
    <section
      className="panel mt-7 p-5"
      aria-labelledby="video-evidence-heading"
    >
      <h2 id="video-evidence-heading" className="text-base font-semibold">
        Model evidence
      </h2>
      <p className="mt-2 text-sm leading-6 text-ink-muted">
        Sensitivity for the highest flagged window (
        {formatTime(prediction.start_time)}–{formatTime(prediction.end_time)}).
        Each anonymous VSViG input patch was neutralised once; a larger score
        change means the model relied on that patch more. This is not a clinical
        explanation.
      </p>
      <div className="mt-4 space-y-2">
        {evidence.patches.slice(0, 5).map((patch) => (
          <div
            className="grid grid-cols-[4.5rem_minmax(0,1fr)_4rem] items-center gap-3 text-xs"
            key={patch.patch_index}
          >
            <span className="font-mono text-ink-muted">
              Patch {patch.patch_index + 1}
            </span>
            <span className="h-2 rounded-full bg-surface-muted">
              <span
                className="block h-full rounded-full bg-teal"
                style={{
                  width: `${Math.max(4, (Math.abs(patch.score_change) / maxScoreChange) * 100)}%`,
                }}
              />
            </span>
            <span className="font-mono text-right tabular-nums text-ink-muted">
              {patch.score_change.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ResearchOnlyNotice() {
  return (
    <p className="mt-8 text-xs leading-5 text-ink-muted">
      VSViG · Research only · Not a diagnosis. Flagged intervals require human
      review.
    </p>
  );
}
