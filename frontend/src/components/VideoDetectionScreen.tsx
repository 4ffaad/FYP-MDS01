"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { detectionVideoUrl, getDetection, getDetectionResults, listDetections, uploadDetection, type DetectionJob, type DetectionResult } from "@/lib/video-detection";

const time = (seconds: number) => `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
const stageNames: Record<string, string> = { preflight: "Checking video", "pose-and-inference": "Extracting poses and scoring windows", "review-video": "Preparing review video", complete: "Ready for review", failed: "Processing stopped", expired: "Retention expired" };

export function VideoDetectionUploadScreen() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<DetectionJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const abort = new AbortController();
    listDetections(abort.signal).then(({ jobs }) => setJobs(jobs)).catch((e) => { if (!abort.signal.aborted) setError(e.message); });
    return () => abort.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true); setError(null);
    try {
      const { job } = await uploadDetection(file, setProgress);
      router.push(`/video-detection/${encodeURIComponent(job.job_id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The video could not be submitted.");
      setBusy(false);
    }
  }

  return <div className="page-frame"><div className="mx-auto max-w-5xl">
    <h1 className="text-3xl font-semibold tracking-tight">Video seizure detection</h1>
    <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">Upload a patient clip to review movement-based model scores and possible event intervals.</p>
    <form onSubmit={submit} className="panel mt-8 max-w-2xl space-y-5 p-6">
      <div><label htmlFor="detection-video" className="block text-sm font-semibold">Patient video</label>
        <p id="video-help" className="mt-2 text-sm leading-6 text-ink-muted">MP4, MOV or WebM. Use a clip showing one patient. Audio is excluded from review playback. Your account owns this upload.</p>
        <input id="detection-video" aria-describedby="video-help" className="mt-4 block w-full text-sm file:mr-4 file:rounded-md file:border file:border-rule file:bg-surface-soft file:px-4 file:py-2" type="file" accept=".mp4,.mov,.webm" disabled={busy} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </div>
      <p className="text-sm leading-6 text-ink-muted">This workflow retains patient appearance for private review. It does not apply face blurring or de-identification.</p>
      {error && <p role="alert" className="text-sm text-red">{error}</p>}
      {busy && <p role="status" className="text-sm text-ink-muted">{progress < 100 ? `Uploading ${progress}%` : "Validating and securing video…"}</p>}
      <Button disabled={!file || busy} type="submit"><Icon name={busy ? "spinner" : "activity"} className={`size-4 ${busy ? "animate-spin" : ""}`} />{busy ? "Submitting…" : "Start detection"}</Button>
    </form>
    <section className="mt-10" aria-labelledby="recent-detections"><h2 id="recent-detections" className="text-lg font-semibold">Your video jobs</h2>
      {jobs.length ? <ul className="mt-4 divide-y divide-rule border-y border-rule">{jobs.map((job) => <li key={job.job_id}><Link className="flex min-h-16 flex-wrap items-center justify-between gap-2 py-3 text-sm hover:text-teal" href={`/video-detection/${job.job_id}`}><span>{job.label}</span><span className="text-ink-muted">{job.status.replaceAll("_", " ")}</span></Link></li>)}</ul> : <p className="mt-3 text-sm text-ink-muted">Submitted videos will appear here.</p>}
    </section>
    <p className="mt-8 text-xs leading-5 text-ink-muted">Research only · Not a diagnosis. Model scores require human review.</p>
  </div></div>;
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
        const { job: next } = await getDetection(jobId, abort.signal);
        if (abort.signal.aborted) return;
        setJob(next);
        if (next.status === "ready") setResult(await getDetectionResults(jobId, abort.signal));
        else setResult(null);
        if (!["failed", "expired"].includes(next.status)) timer = setTimeout(poll, next.status === "ready" ? 15000 : 1500);
      } catch (e) { if (!abort.signal.aborted) setError(e instanceof Error ? e.message : "The job could not be loaded."); }
    }
    void poll();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [jobId]);

  function seek(seconds: number) {
    if (video.current) { video.current.currentTime = seconds; setPosition(seconds); video.current.focus(); }
  }
  const duration = job?.duration_seconds || 1;
  return <div className="page-frame"><div className="mx-auto max-w-5xl">
    <Link href="/video-detection" className="text-sm text-teal hover:underline">Video detection</Link>
    <h1 className="mt-5 text-3xl font-semibold tracking-tight">{job?.label ?? "Video review"}</h1>
    {error && <p role="alert" className="mt-4 text-sm text-red">{error}</p>}
    {!job ? <p role="status" className="mt-6 text-sm">Loading video job…</p> : <>
      <p role="status" className="mt-3 text-sm text-ink-muted">{stageNames[job.current_stage] ?? job.current_stage}</p>
      {job.error && <p role="alert" className="mt-5 rounded-md border border-rule p-4 text-sm text-red">{job.error}</p>}
      {job.status === "expired" && <p className="mt-5 text-sm">The retention period ended. Video and results have been removed.</p>}
      {job.video_available && job.status === "ready" && <section className="mt-7" aria-label="Private video review">
        <video ref={video} src={detectionVideoUrl(jobId) ?? undefined} crossOrigin="use-credentials" controls preload="metadata" muted playsInline aria-label="Patient video review" className="aspect-video w-full rounded-lg bg-black" onTimeUpdate={() => setPosition(video.current?.currentTime ?? 0)} onError={() => { setPlaybackError(true); void getDetection(jobId).catch(() => {}); }} />
        {playbackError && <p role="alert" className="mt-2 text-sm text-red">Playback is unavailable. Refresh to check your session and the video retention period.</p>}
        <p className="mt-2 text-xs text-ink-muted">Private patient video · Audio removed · Available until {new Date(job.retention_expires_at).toLocaleString()}</p>
      </section>}
      {result && <>
        <section className="panel mt-6 p-5" aria-labelledby="score-heading">
          <h2 id="score-heading" className="text-base font-semibold">Uncalibrated model score</h2>
          <p className="mt-2 text-sm leading-6 text-ink-muted">Each point covers {(result.model.window_frames / result.model.sample_fps).toFixed(2)} seconds, stepping {(result.model.stride_frames / result.model.sample_fps).toFixed(2)} seconds. Scores are not calibrated probabilities.</p>
          <svg viewBox="0 0 900 190" role="img" aria-label={`Window scores from 0 to 1. Threshold ${result.model.threshold}.`} className="mt-4 w-full overflow-visible">
            {[0, 0.5, 1].map((tick) => <g key={tick}><line x1="35" x2="875" y1={155 - tick * 130} y2={155 - tick * 130} stroke="currentColor" opacity="0.12" /><text x="0" y={160 - tick * 130} fontSize="12" fill="currentColor">{tick.toFixed(1)}</text></g>)}
            <line x1="35" x2="875" y1={155 - result.model.threshold * 130} y2={155 - result.model.threshold * 130} stroke="var(--color-amber, #8a5a00)" strokeDasharray="5 5" />
            <polyline fill="none" stroke="var(--color-teal, #0066cc)" strokeWidth="2" points={result.predictions.map((p) => `${35 + ((p.start_time + p.end_time) / 2 / duration) * 840},${155 - p.score * 130}`).join(" ")} />
            <line x1={35 + position / duration * 840} x2={35 + position / duration * 840} y1="20" y2="160" stroke="currentColor" opacity="0.6" />
            <text x="35" y="185" fontSize="12" fill="currentColor">0:00</text><text x="875" y="185" textAnchor="end" fontSize="12" fill="currentColor">{time(duration)}</text>
          </svg>
          <p className="mt-2 text-xs text-ink-muted">Dashed line: research threshold {result.model.threshold.toFixed(2)} · {result.predictions.filter((p) => p.seizure_detected).length} of {result.predictions.length} windows flagged</p>
        </section>
        <section className="mt-7" aria-labelledby="interval-heading"><h2 id="interval-heading" className="text-lg font-semibold">Flagged intervals</h2>
          <p className="mt-2 text-sm text-ink-muted">Select an interval to review the corresponding video.</p>
          <div className="mt-4 flex flex-wrap gap-3">{result.intervals.length ? result.intervals.map((interval, i) => <Button variant="outline" key={interval.start_time} onClick={() => seek(interval.start_time)}>Event {i + 1} · {time(interval.start_time)}–{time(interval.end_time)}</Button>) : <p className="text-sm text-ink-muted">No windows crossed the configured threshold. This does not rule out a seizure.</p>}</div>
        </section>
        <details className="mt-7 border-y border-rule py-4"><summary className="cursor-pointer text-sm font-semibold">All window scores</summary><div className="mt-4 max-h-72 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th className="py-2">Window</th><th>Score</th><th>Flagged</th></tr></thead><tbody>{result.predictions.map((p) => <tr key={p.start_time} className="border-t border-rule"><td><button className="min-h-11 text-teal hover:underline" onClick={() => seek(p.start_time)}>{time(p.start_time)}–{time(p.end_time)}</button></td><td>{p.score.toFixed(3)}</td><td>{p.seizure_detected ? "Yes" : "No"}</td></tr>)}</tbody></table></div></details>
        <details className="mt-4 border-b border-rule pb-4"><summary className="cursor-pointer text-sm font-semibold">Model and processing details</summary><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-[160px_1fr]">{Object.entries({ Model: result.model.model_name, Version: result.model.model_version, Checkpoint: result.model.weights_hash, Preprocessing: result.model.preprocessing_version, Threshold: result.model.threshold }).map(([key, value]) => <div key={key} className="contents"><dt className="text-ink-muted">{key}</dt><dd className="break-all">{value}</dd></div>)}</dl></details>
      </>}
    </>}
    <p className="mt-8 text-xs leading-5 text-ink-muted">VSViG · Research only · Not a diagnosis. Flagged intervals require human review.</p>
  </div></div>;
}
