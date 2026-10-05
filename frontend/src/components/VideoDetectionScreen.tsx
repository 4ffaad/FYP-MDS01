"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { pollRetryDelay, shouldRetryRequest } from "@/lib/api";
import {
  VideoJobLoadingState,
  VideoProcessingStatus,
  VideoUploadStatus,
} from "@/components/VideoProcessingStatus";
import {
  getDetection,
  getDetectionResults,
  uploadDetection,
  detectionVisualizationUrl,
  type DetectionJob,
  type DetectionResult,
  videoJobFailureMessage,
} from "@/lib/video-detection";
import { VideoReviewPanel } from "@/components/VideoReviewPanel";
import { VideoBlurStrengthControl } from "@/components/VideoBlurStrengthControl";
import { ModalityWorkspaceTabs } from "./ModalityWorkspaceTabs";

function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

function formatRetentionExpiry(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function VideoDetectionUploadScreen() {
  const [file, setFile] = useState<File | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadPhase, setUploadPhase] = useState<"uploading" | "checking-pose">(
    "uploading",
  );
  const [error, setError] = useState<string | null>(null);
  const [blurStrengthPercent, setBlurStrengthPercent] = useState(100);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;

    setBusy(true);
    setProgress(0);
    setUploadPhase("uploading");
    setError(null);

    try {
      const { job } = await uploadDetection(
        file,
        (value) => {
          setProgress(value);
          if (value >= 100) setUploadPhase("checking-pose");
        },
        undefined,
        undefined,
        blurStrengthPercent,
      );
      setSubmittedJobId(job.job_id);
      setFile(null);
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
        <p className="eyebrow">Video workspace</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Video</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
          Upload a clip once. MDS01 scores movement and creates a face-blurred
          review copy automatically.
        </p>
        <ModalityWorkspaceTabs modality="video" active="upload" />

        {submittedJobId && (
          <p
            className="mt-5 rounded-lg border border-teal/30 bg-teal-soft/40 px-4 py-3 text-sm"
            role="status"
          >
            Video processing started. You can stay here;{" "}
            <Link
              className="font-semibold text-teal-dark underline underline-offset-4"
              href={`/video-detection/${encodeURIComponent(submittedJobId)}`}
            >
              open its review when you’re ready
            </Link>
            .
          </p>
        )}

        <form onSubmit={submit} className="panel mt-6 max-w-2xl space-y-5 p-6">
          <div>
            <label
              htmlFor="detection-video"
              className="block text-sm font-semibold"
            >
              Video
            </label>
            <p
              id="video-help"
              className="mt-2 text-sm leading-6 text-ink-muted"
            >
              MP4, MOV, AVI, or WebM · one person visible · 5 seconds or longer
              · 1920×1080 preferred.
            </p>
            <input
              id="detection-video"
              aria-describedby="video-help"
              className="mt-4 block w-full text-sm file:mr-4 file:rounded-md file:border file:border-rule file:bg-surface-soft file:px-4 file:py-2"
              type="file"
              accept=".avi,.mp4,.mov,.webm"
              disabled={busy}
              onChange={(event) => {
                setSubmittedJobId(null);
                setFile(event.target.files?.[0] ?? null);
              }}
            />
            <VideoBlurStrengthControl
              value={blurStrengthPercent}
              onChange={setBlurStrengthPercent}
              disabled={busy}
            />
          </div>

          <details className="rounded-lg border border-rule px-4 py-3 text-sm">
            <summary className="cursor-pointer font-semibold text-ink">
              Privacy and model details
            </summary>
            <p className="mt-3 leading-6 text-ink-muted">
              VSViG receives pose coordinates and 15 blurred patches. The review
              copy blurs the tracked face; uncertain detection falls back to
              full-frame blur.
            </p>
          </details>
          {error && (
            <div
              role="alert"
              className="rounded-md border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
            >
              {error}
            </div>
          )}
          {busy && (
            <VideoUploadStatus progress={progress} phase={uploadPhase} />
          )}

          <Button disabled={!file || busy} type="submit">
            <Icon
              name={busy ? "spinner" : "activity"}
              className={`size-4 ${busy ? "animate-spin" : ""}`}
            />
            {busy
              ? uploadPhase === "checking-pose"
                ? "Checking pose…"
                : "Submitting…"
              : "Upload video"}
          </Button>
        </form>
        <ResearchOnlyNotice />
      </div>
    </div>
  );
}

export function VideoDetectionJobScreen({
  jobId,
  initialVideoTimeSeconds,
}: {
  jobId: string;
  initialVideoTimeSeconds?: number;
}) {
  const [job, setJob] = useState<DetectionJob | null>(null);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultRetryKey, setResultRetryKey] = useState(0);

  useEffect(() => {
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let retryAttempt = 0;

    async function poll() {
      try {
        const { job: nextJob } = await getDetection(jobId, abort.signal);
        if (abort.signal.aborted) return;

        setJob(nextJob);
        if (nextJob.status === "ready") {
          try {
            const nextResult = await getDetectionResults(jobId, abort.signal);
            if (abort.signal.aborted) return;
            setResult(nextResult);
            setError(null);
            retryAttempt = 0;
          } catch (resultError) {
            if (abort.signal.aborted) return;
            setError(
              resultError instanceof Error
                ? resultError.message
                : "The job result could not be loaded.",
            );
            if (shouldRetryRequest(resultError)) {
              retryAttempt += 1;
              timer = setTimeout(poll, pollRetryDelay(retryAttempt, 1_500));
            }
            return;
          }
        } else {
          retryAttempt = 0;
          setResult(null);
        }
        setError(null);

        if (!["failed", "expired"].includes(nextJob.status)) {
          timer = setTimeout(poll, nextJob.status === "ready" ? 15_000 : 1_500);
        }
      } catch (error) {
        if (!abort.signal.aborted && shouldRetryRequest(error)) {
          retryAttempt += 1;
          timer = setTimeout(poll, pollRetryDelay(retryAttempt, 1_500));
        } else if (!abort.signal.aborted) {
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
  }, [jobId, resultRetryKey]);

  const duration = job?.duration_seconds || 1;

  return (
    <div className="page-frame">
      <div className="mx-auto max-w-5xl">
        <ModalityWorkspaceTabs modality="video" active="reviews" />
        <h1 className="mt-5 text-3xl font-semibold tracking-tight">
          {job?.label ?? "Video review"}
        </h1>
        {job?.retention_expires_at && (
          <p className="mt-2 text-xs leading-5 text-ink-muted">
            Encrypted result expires{" "}
            {formatRetentionExpiry(job.retention_expires_at)}.
          </p>
        )}
        {error && (
          <div
            role="alert"
            className="mt-4 flex flex-wrap items-center gap-3 rounded-md border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
          >
            <span className="min-w-0 flex-1">{error}</span>
            {(!job || (job.status === "ready" && !result)) && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  setError(null);
                  setResultRetryKey((key) => key + 1);
                }}
              >
                {job ? "Retry result" : "Retry job"}
              </Button>
            )}
          </div>
        )}

        {!job ? (
          <VideoJobLoadingState />
        ) : (
          <>
            <VideoProcessingStatus job={job} />
            <p className="mt-3 text-sm text-ink-muted">
              VSViG patch-blur setting: {job.blur_strength_percent}%.
            </p>
            {job.error && (
              <p
                role="alert"
                className="mt-5 rounded-md border border-rule p-4 text-sm text-red"
              >
                {videoJobFailureMessage(
                  job.status === "expired" ? "expired" : "failed",
                  job.error,
                )}
              </p>
            )}
            {job.status === "expired" && (
              <p className="mt-5 text-sm">
                The retention period ended. Encrypted predictions and review
                video have been removed.
              </p>
            )}

            {job.status === "failed" && job.video_available && (
              <section className="panel mt-6 overflow-hidden p-5 sm:p-6">
                <div>
                  <h2 className="text-lg font-semibold">
                    Privacy-safe video review
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-ink-muted">
                    VSViG did not produce a score for this clip. You can still
                    review its timing alongside the EEG. The retained video
                    blurs the face; the viewer can also show the 15 model
                    patches and their Grad-CAM evidence.
                  </p>
                </div>
                <video
                  className="mt-4 aspect-video w-full rounded-xl bg-black object-contain"
                  src={detectionVisualizationUrl(jobId)}
                  controls
                  playsInline
                  preload="metadata"
                  crossOrigin="use-credentials"
                  aria-label="Privacy-safe video review without a VSViG score"
                  onLoadedMetadata={(event) => {
                    if (
                      typeof initialVideoTimeSeconds === "number" &&
                      Number.isFinite(initialVideoTimeSeconds)
                    ) {
                      event.currentTarget.currentTime = Math.max(
                        0,
                        Math.min(
                          event.currentTarget.duration,
                          initialVideoTimeSeconds,
                        ),
                      );
                    }
                  }}
                >
                  Your browser cannot play this review video.
                </video>
              </section>
            )}

            {result && (
              <>
                {result.privacy?.model_input_adaptation === "letterbox" && (
                  <section
                    className="mt-6 rounded-lg border border-amber/40 bg-amber-soft px-5 py-4"
                    role="status"
                    aria-labelledby="video-adaptation-heading"
                  >
                    <h2
                      id="video-adaptation-heading"
                      className="text-sm font-bold text-ink"
                    >
                      Experimental input adaptation
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-ink-muted">
                      This lower-resolution clip was resized and padded to
                      1920×1080. That adds no detail and is not validated as
                      equivalent to native-resolution input.
                    </p>
                  </section>
                )}
                <VideoReviewPanel
                  result={result}
                  duration={duration}
                  videoAvailable={job.video_available}
                  videoUrl={detectionVisualizationUrl(jobId)}
                  initialTimeSeconds={initialVideoTimeSeconds}
                />
                <VideoGradCamSummary
                  prediction={result.predictions.find(
                    (prediction) => prediction.model_evidence,
                  )}
                  patchLabels={result.model.patch_labels ?? []}
                />
                <WindowScores predictions={result.predictions} />
                <ModelDetails model={result.model} privacy={result.privacy} />
              </>
            )}
          </>
        )}

        <ResearchOnlyNotice />
      </div>
    </div>
  );
}

function WindowScores({
  predictions,
}: {
  predictions: DetectionResult["predictions"];
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
                  <span className="text-ink-muted">
                    {formatTime(prediction.start_time)}–
                    {formatTime(prediction.end_time)}
                  </span>
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

function ModelDetails({
  model,
  privacy,
}: {
  model: DetectionResult["model"];
  privacy?: DetectionResult["privacy"];
}) {
  const sourceResolution = privacy?.source_resolution;
  const modelResolution = privacy?.model_resolution;
  const details = {
    Model: model.model_name,
    Version: model.model_version,
    Checkpoint: model.weights_hash,
    "Pose model": model.pose_model,
    "Pose checkpoint": model.pose_weights_hash,
    "Dynamic partitions": model.partition_hash,
    Preprocessing: model.preprocessing_version,
    Input: model.input_resolution
      ? `${model.input_resolution.width}×${model.input_resolution.height} · ${model.window_frames} frames @ ${model.sample_fps} fps`
      : `${model.window_frames} frames @ ${model.sample_fps} fps`,
    "Source geometry": sourceResolution
      ? `${sourceResolution[0]}×${sourceResolution[1]} → ${privacy?.model_input_adaptation ?? "adaptation not reported"} → ${modelResolution ? `${modelResolution[0]}×${modelResolution[1]}` : "model geometry not reported"}`
      : "Not reported",
    "VSViG patch blur":
      typeof privacy?.blur_strength_percent === "number"
        ? `${privacy.blur_strength_percent}% of default strength`
        : "Not reported",
    "Letterbox padding (L/T/R/B)":
      privacy?.model_input_adaptation === "letterbox" &&
      privacy.model_input_padding_ltrb
        ? `${privacy.model_input_padding_ltrb.join(" / ")} px`
        : "None",
    Threshold: model.threshold,
    Postprocessing: model.postprocessing,
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

function VideoGradCamSummary({
  prediction,
  patchLabels,
}: {
  prediction: DetectionResult["predictions"][number] | undefined;
  patchLabels: string[];
}) {
  const evidence = prediction?.model_evidence;
  const samples = evidence?.gradcam_samples ?? [];
  const patchRelevance = new Map<number, number>();
  for (const sample of samples) {
    for (const patch of sample.patches) {
      patchRelevance.set(
        patch.patch_index,
        Math.max(patchRelevance.get(patch.patch_index) ?? 0, patch.relevance),
      );
    }
  }
  const strongestPatches = [...patchRelevance.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5);

  if (!evidence || !prediction || evidence.method !== "vsvig-graph-grad-cam") {
    return (
      <section
        className="panel mt-7 p-5"
        aria-labelledby="video-evidence-heading"
      >
        <h2 id="video-evidence-heading" className="text-base font-semibold">
          VSViG Grad-CAM
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          {evidence
            ? "This older result has patch-sensitivity data but no Grad-CAM."
            : "No Grad-CAM evidence was returned. Window scores and intervals remain available."}
        </p>
      </section>
    );
  }

  return (
    <section
      className="panel mt-7 p-5"
      aria-labelledby="video-evidence-heading"
    >
      <h2 id="video-evidence-heading" className="text-base font-semibold">
        VSViG Grad-CAM
      </h2>
      <p className="mt-2 text-xs text-ink-muted">
        Strongest-scoring window · {formatTime(prediction.start_time)}–
        {formatTime(prediction.end_time)}
      </p>
      <p className="mt-1 text-xs text-ink-muted">
        Relative contribution across time and the 15 keypoint patches.
      </p>
      {strongestPatches.length > 0 ? (
        <ol className="mt-4 grid gap-3 sm:grid-cols-2">
          {strongestPatches.map(([patchIndex, relevance]) => (
            <li
              className="rounded-lg border border-rule bg-surface-soft px-3 py-2"
              key={patchIndex}
            >
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="font-medium text-ink">
                  {patchLabels[patchIndex] ?? `Patch ${patchIndex + 1}`}
                </span>
                <span className="font-mono tabular-nums text-ink-muted">
                  {relevance.toFixed(2)}
                </span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-rule"
                role="img"
                aria-label={`${patchLabels[patchIndex] ?? `Patch ${patchIndex + 1}`} relative Grad-CAM relevance ${relevance.toFixed(2)}; normalized within this window`}
              >
                <span
                  className="block h-full rounded-full bg-gradient-to-r from-amber to-red"
                  style={{ width: `${Math.round(relevance * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-sm text-ink-muted">
          No patch contribution values were returned.
        </p>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        Relative model evidence · not a diagnosis
      </p>
    </section>
  );
}

function ResearchOnlyNotice() {
  return (
    <p className="mt-8 text-xs leading-5 text-ink-muted">
      VSViG research output · not a diagnosis.
    </p>
  );
}
