"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
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
  listDetections,
  uploadDetection,
  type DetectionJob,
  type DetectionResult,
} from "@/lib/video-detection";
import { VideoReviewPanel } from "@/components/VideoReviewPanel";

function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

function formatPrivacyQualityFlag(flag: string) {
  return flag === "intermittent_detection"
    ? "The detector reported exactly one face in only some frames."
    : flag === "no_detection"
      ? "The detector did not report exactly one face in any frame."
      : flag.replaceAll("_", " ");
}

function formatFaceDetectionCoverage(coverage: number) {
  return new Intl.NumberFormat(undefined, {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(coverage);
}

function formatRetentionExpiry(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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
          Video seizure review
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">
          Upload one video to review privacy diagnostics, VSViG model scores,
          and possible event intervals. Detection exposes no preview or
          playback; its privacy-safe validation visualization is transient and
          deleted. A separate video-privacy workflow may retain its own
          protected preview.
        </p>

        <form onSubmit={submit} className="panel mt-8 max-w-2xl space-y-5 p-6">
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
              AVI, MP4, MOV or WebM showing one patient. The pinned contract
              requires 1920×1080 input. The local H5 profile experimentally
              upscales smaller clips into a 1920×1080 frame while preserving
              aspect ratio, with black padding when needed. Upscaling adds no
              captured detail and is not validated as equivalent to
              native-resolution input. Use a readable constant-frame-rate clip
              of at least five seconds where possible; low-quality or incomplete
              pose can still fail closed. Lightweight OpenPose and VSViG use the
              same full-frame-blurred protected model-input frames. Audio is
              excluded from the visual model input. Your account owns this
              upload.
            </p>
            <input
              id="detection-video"
              aria-describedby="video-help"
              className="mt-4 block w-full text-sm file:mr-4 file:rounded-md file:border file:border-rule file:bg-surface-soft file:px-4 file:py-2"
              type="file"
              accept=".avi,.mp4,.mov,.webm"
              disabled={busy}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </div>

          <p className="text-sm leading-6 text-ink-muted">
            The browser sends the upload over this computer’s local connection;
            the API encrypts it as it streams into private storage before
            background processing begins. This local HTTP connection has no TLS
            and must not be exposed to a network. A queued source may still
            contain audio temporarily; it is excluded from the visual model and
            retained outputs, then deleted during cleanup. One shared pose pass
            feeds the VSViG model and a temporary privacy-safe visualization
            used for validation. The visualization, original, and temporary
            model-input files are deleted after processing; only encrypted
            predictions and provenance are retained until the displayed expiry.
          </p>
          {error && (
            <div
              role="alert"
              className="rounded-md border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
            >
              {error}
            </div>
          )}
          {busy && <VideoUploadStatus progress={progress} />}

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
        <Link
          href="/video-detection"
          className="text-sm text-teal hover:underline"
        >
          Video review
        </Link>
        <h1 className="mt-5 text-3xl font-semibold tracking-tight">
          {job?.label ?? "Video review"}
        </h1>
        {job?.retention_expires_at && (
          <p className="mt-2 text-xs leading-5 text-ink-muted">
            Encrypted prediction retention ends{" "}
            {formatRetentionExpiry(job.retention_expires_at)}. Source and
            temporary model-input video are removed after processing.
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
                The retention period ended. Encrypted prediction data, source
                video, and the temporary model input have been removed.
              </p>
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
                      This lower-resolution clip was resized to 1920×1080 while
                      preserving its aspect ratio; black padding was added only
                      where needed. The adaptation adds no captured detail and
                      has not been validated as equivalent to native-resolution
                      input. Treat its scores as research-only and review the
                      time-aligned model evidence.
                    </p>
                  </section>
                )}
                {result.privacy?.review_required && (
                  <section
                    className="mt-6 rounded-lg border border-amber/40 bg-amber-soft px-5 py-4"
                    role="status"
                    aria-live="polite"
                    aria-labelledby="privacy-quality-heading"
                  >
                    <h2
                      id="privacy-quality-heading"
                      className="text-sm font-bold text-ink"
                    >
                      Privacy quality needs review
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-ink-muted">
                      One or more privacy-quality checks need review. This does
                      not change the full-frame blur, which is applied to every
                      frame. Treat flagged windows as uncertain and review them
                      with the appropriate context.
                    </p>
                    {result.privacy.quality_flags.length > 0 && (
                      <ul className="mt-2 list-disc pl-5 text-xs leading-5 text-ink-muted">
                        {result.privacy.quality_flags.map((flag) => (
                          <li key={flag}>{formatPrivacyQualityFlag(flag)}</li>
                        ))}
                      </ul>
                    )}
                  </section>
                )}
                {typeof result.privacy?.face_detection_coverage === "number" &&
                  Number.isFinite(result.privacy.face_detection_coverage) &&
                  result.privacy.face_detection_coverage >= 0 &&
                  result.privacy.face_detection_coverage <= 1 && (
                    <section
                      className="mt-4 rounded-lg border border-rule bg-surface-soft px-5 py-4"
                      aria-labelledby="face-detection-coverage-heading"
                    >
                      <h2
                        id="face-detection-coverage-heading"
                        className="text-sm font-bold text-ink"
                      >
                        De-identification diagnostic
                      </h2>
                      <p className="mt-2 text-sm leading-6 text-ink-muted">
                        OpenCV Haar reported exactly one face in{" "}
                        {formatFaceDetectionCoverage(
                          result.privacy.face_detection_coverage,
                        )}{" "}
                        of frames. Full-frame blur was applied to every frame,
                        independent of detection. This coverage signal does not
                        guarantee anonymity.
                      </p>
                    </section>
                  )}
                <VideoReviewPanel result={result} duration={duration} />
                <VideoEvidence
                  prediction={result.predictions.find(
                    (prediction) => prediction.model_evidence,
                  )}
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
        Each VSViG input patch was neutralised once; a larger score change means
        the model relied on that input region more. Labels identify the pose
        keypoint region, not a clinical explanation.
      </p>
      <div className="mt-4 space-y-2">
        {evidence.patches.slice(0, 5).map((patch) => (
          <div
            className="grid grid-cols-[8rem_minmax(0,1fr)_4rem] items-center gap-3 text-xs"
            key={patch.patch_index}
          >
            <span className="font-mono text-ink-muted">
              {patch.component ?? `Patch ${patch.patch_index + 1}`}
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
