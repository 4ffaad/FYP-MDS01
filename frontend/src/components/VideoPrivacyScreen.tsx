"use client";
/* eslint-disable @next/next/no-img-element */

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { acknowledgeVideoPrivacyJob, getVideoPrivacyJob, submitVideoPrivacy } from "@/lib/api";
import type { VideoPrivacyJob, VideoPrivacyProfile } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Icon } from "./Icon";

const PROFILES: Array<{ id: VideoPrivacyProfile; title: string; description: string; detail: string }> = [
  { id: "face-redacted", title: "Face redaction", description: "Blur detected faces and keep the surrounding scene visible.", detail: "Useful when reviewers need to see scene context." },
  { id: "pose-only", title: "Pose-only", description: "Replace the scene with pose landmarks on a non-identifying background.", detail: "Useful when movement is the only visual evidence needed." },
];

const STAGE_LABELS: Record<string, string> = {
  preflight: "Preflight",
  "privacy-transform": "Privacy transform",
  "output-validation": "Output validation",
  cleanup: "Cleanup",
};

export function VideoPrivacyUploadScreen() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<VideoPrivacyProfile>("face-redacted");
  const [progress, setProgress] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a video before starting the privacy transform.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const job = await submitVideoPrivacy(file, profile, setProgress);
      router.push(`/video-privacy/${encodeURIComponent(job.jobId)}`);
    } catch (submissionError) {
      setSubmitting(false);
      setError(submissionError instanceof Error ? submissionError.message : "The video could not be secured.");
    }
  }

  return (
    <div className="page-frame">
      <div className="mx-auto max-w-4xl animate-enter-up">
        <div className="max-w-3xl">
          <div className="flex items-center gap-3 text-sm font-semibold text-teal-dark"><span className="grid size-9 place-items-center rounded-lg bg-teal-soft"><Icon name="shield" className="size-5" /></span>Video privacy</div>
          <h1 className="mt-5 text-[clamp(2rem,5vw,2.25rem)] font-semibold leading-[1.08] tracking-[-0.03em] text-ink">Protect a patient video before review</h1>
          <p className="mt-5 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">Choose one privacy profile. The video is transformed here as a standalone privacy workflow.</p>
        </div>

        <form className="mt-10 grid items-start gap-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]" onSubmit={(event) => void handleSubmit(event)}>
          <section className="panel overflow-hidden" aria-labelledby="video-upload-heading">
            <div className="border-b border-rule px-5 py-5 sm:px-7">
              <h2 id="video-upload-heading" className="text-base font-bold">Add a video</h2>
              <p className="mt-1 text-sm leading-6 text-ink-muted">Supported inputs: MP4, MOV, or WebM. Up to 512 MB; duration is checked before processing. The original is encrypted before processing.</p>
            </div>
            <div className="px-5 py-6 sm:px-7">
              <label className="flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-rule-strong bg-surface-soft px-6 py-7 text-center outline-none transition-colors hover:border-teal hover:bg-teal-soft/40 focus-within:border-teal focus-within:ring-4 focus-within:ring-teal/20" htmlFor="video-file">
                <Icon name={submitting ? "spinner" : "file"} className={`size-8 text-teal ${submitting ? "animate-spin" : ""}`} />
                <span className="mt-4 text-sm font-bold text-ink">{file ? "Video selected" : "Choose a patient video"}</span>
                <span className="mt-1 text-xs text-ink-muted">Client filenames are not shown after submission.</span>
                <Button asChild size="sm" className="mt-5"><span>Browse files</span></Button>
                <input ref={inputRef} className="sr-only" id="video-file" aria-label="Patient video" type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" onChange={handleFile} disabled={submitting} />
              </label>
              {file && <p className="mt-4 rounded-md bg-surface-soft px-3 py-2 text-xs leading-5 text-ink-muted" aria-live="polite">Ready to secure {formatBytes(file.size)}. The generated job label will be shown instead of this filename.</p>}
              {submitting && <div className="mt-5" aria-live="polite"><div className="flex justify-between text-xs text-ink-muted"><span>Securing video</span><span className="font-mono tabular-nums">{progress}%</span></div><Progress value={progress} className="mt-2 h-1.5 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal" aria-label="Video upload progress" /></div>}
              {error && <div className="mt-5 flex items-start gap-2.5 rounded-md border border-red/30 bg-red-soft px-3.5 py-3 text-sm text-red" role="alert"><Icon name="alert" className="mt-0.5 size-4 shrink-0" /><span>{error}</span></div>}
            </div>
            <div className="flex items-start gap-3 border-t border-rule bg-surface-soft px-5 py-5 text-xs leading-5 text-ink-muted sm:px-7"><Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" /><p><span className="font-semibold text-ink">Private handling.</span> Only encrypted transformed artifacts are retained after processing.</p></div>
          </section>

          <section className="panel overflow-hidden" aria-labelledby="profile-heading">
            <div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="profile-heading" className="text-base font-bold">Choose a privacy profile</h2><p className="mt-1 text-sm leading-6 text-ink-muted">Select one transform for this job.</p></div>
            <div className="space-y-3 px-5 py-6 sm:px-7" role="radiogroup" aria-labelledby="profile-heading">
              {PROFILES.map((item) => {
                const selected = profile === item.id;
                return <label key={item.id} className={`block cursor-pointer rounded-lg border px-4 py-4 transition-colors ${selected ? "border-teal bg-teal-soft/50" : "border-rule bg-surface hover:border-rule-strong"}`}>
                  <span className="flex items-start gap-3"><input className="mt-1 size-4 accent-teal" type="radio" name="video-privacy-profile" value={item.id} checked={selected} onChange={() => setProfile(item.id)} /><span><span className="block text-sm font-bold text-ink">{item.title}</span><span className="mt-1 block text-xs leading-5 text-ink-muted">{item.description}</span><span className="mt-2 block text-xs font-semibold text-teal-dark">{item.detail}</span></span></span>
                </label>;
              })}
              <div className="rounded-md border border-amber/30 bg-amber-soft px-3.5 py-3 text-xs leading-5 text-ink-muted"><span className="font-semibold text-ink">Important:</span> this is a research privacy transform, not a guarantee of anonymity.</div>
              <Button className="mt-2 w-full" size="lg" type="submit" disabled={submitting || !file}>{submitting ? <Icon name="spinner" className="size-4 animate-spin" /> : <Icon name="arrow" className="size-4" />}{submitting ? "Starting privacy transform…" : "Start privacy transform"}</Button>
            </div>
          </section>
        </form>
      </div>
    </div>
  );
}

export function VideoPrivacyJobScreen({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<VideoPrivacyJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acknowledging, setAcknowledging] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    const load = async () => {
      try {
        const next = await getVideoPrivacyJob(jobId, controller.signal);
        if (!mounted) return;
        setJob(next);
        if (["ready", "needs_review", "failed", "expired"].includes(next.status)) return;
        window.setTimeout(() => void load(), 700);
      } catch (loadError) {
        if (mounted && (loadError as Error).name !== "AbortError") setError(loadError instanceof Error ? loadError.message : "This privacy job could not be loaded.");
      }
    };
    void load();
    return () => { mounted = false; controller.abort(); };
  }, [jobId]);

  async function acknowledge() {
    setAcknowledging(true);
    try {
      setJob(await acknowledgeVideoPrivacyJob(jobId));
    } catch (acknowledgeError) {
      setError(acknowledgeError instanceof Error ? acknowledgeError.message : "The quality acknowledgement could not be recorded.");
    } finally { setAcknowledging(false); }
  }

  if (error && !job) return <UnavailableState message={error} />;
  if (!job) return <div className="page-frame"><div className="mx-auto flex max-w-3xl items-center gap-4" aria-live="polite"><span className="grid size-11 place-items-center rounded-lg bg-teal-soft text-teal-dark"><Icon name="spinner" className="size-5 animate-spin" /></span><div><h1 className="text-xl font-semibold text-ink">Loading protected job</h1><p className="mt-1 text-sm text-ink-muted">Checking the privacy transform status…</p></div></div></div>;

  const complete = job.status === "ready" || job.status === "needs_review";
  return <div className="page-frame">
    <div className="mx-auto max-w-5xl animate-enter-up">
      <button className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" type="button" onClick={() => router.push("/video-privacy")}><Icon name="back" className="size-4" />Start another privacy job</button>
      <div className="mt-6 flex flex-wrap items-end justify-between gap-4"><div><div className="flex items-center gap-2 text-sm font-semibold text-teal-dark"><Icon name="shield" className="size-5" />Protected video</div><h1 className="mt-3 text-[clamp(2rem,5vw,2.25rem)] font-semibold leading-[1.08] tracking-[-0.03em] text-ink">{job.label}</h1><p className="mt-4 max-w-2xl text-sm leading-6 text-ink-muted">{job.profileLabel} · {statusLabel(job.status)}</p></div><StatusPill status={job.status} /></div>

      <section className="panel mt-8 overflow-hidden" aria-labelledby="stages-heading" aria-live="polite">
        <div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="stages-heading" className="text-base font-bold">Privacy processing</h2><p className="mt-1 text-sm leading-6 text-ink-muted">Only privacy, output validation, and cleanup stages are shown here.</p></div>
        <ol className="grid gap-px bg-rule sm:grid-cols-4">{job.stages.map((stage) => <li key={stage.id} className="bg-surface px-4 py-5 sm:px-5"><div className="flex items-center gap-2">{stage.status === "complete" ? <Icon name="check" className="size-4 text-teal" weight="bold" /> : stage.status === "active" ? <Icon name="spinner" className="size-4 animate-spin text-teal" /> : <Icon name="clock" className="size-4 text-ink-muted" />}<span className="text-xs font-bold text-ink">{STAGE_LABELS[stage.id]}</span></div><p className="mt-2 text-xs text-ink-muted">{stage.status === "complete" ? "Complete" : stage.status === "active" ? "In progress" : "Waiting"}</p></li>)}</ol>
      </section>

      {job.status === "failed" ? <div className="mt-6 flex items-start gap-3 rounded-lg border border-red/30 bg-red-soft px-4 py-4 text-sm text-red" role="alert"><Icon name="alert" className="mt-0.5 size-5 shrink-0" /><div><p className="font-bold">Privacy transform unavailable</p><p className="mt-1 leading-6">{job.error ?? "The video could not be transformed safely."} No protected output is available.</p></div></div> : complete && <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <section className="panel overflow-hidden" aria-labelledby="preview-heading"><div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="preview-heading" className="text-base font-bold">Protected preview frame</h2><p className="mt-1 text-sm leading-6 text-ink-muted">This frame is generated from the transformed output. The original is never previewed here.</p></div><div className="bg-surface-soft p-5 sm:p-7">{job.previewUrl ? <img className="aspect-video w-full rounded-lg border border-rule bg-black object-contain" src={job.previewUrl} alt="Representative frame from the protected video" /> : <div className="grid aspect-video place-items-center rounded-lg border border-rule bg-surface-muted text-center"><div><Icon name="shield" className="mx-auto size-9 text-teal" /><p className="mt-3 text-sm font-bold text-ink">Protected preview frame</p><p className="mt-1 text-xs text-ink-muted">Preview is available from the transformed artifact.</p></div></div>}</div></section>
        <section className="space-y-6"><div className="panel overflow-hidden"><div className="border-b border-rule px-5 py-5"><h2 className="text-base font-bold">Output policy</h2><p className="mt-1 text-sm leading-6 text-ink-muted">{job.profileDescription}</p></div><div className="space-y-3 px-5 py-5 text-sm"><PolicyRow label="Audio" value="Removed" /><PolicyRow label="Metadata" value="Scrubbed" /><PolicyRow label="Retention" value={formatExpiry(job.retentionExpiresAt)} /><PolicyRow label="Output" value={job.outputUsable ? "Validated for review" : "Not available"} /></div>{job.downloadAvailable && job.downloadUrl && <div className="border-t border-rule px-5 py-5"><Button asChild className="w-full" size="lg"><a href={job.downloadUrl} download><Icon name="arrow" className="size-4" />Download protected video</a></Button></div>}</div>
          {job.requiresAcknowledgement && <div className="rounded-lg border border-amber/40 bg-amber-soft px-5 py-5"><h2 className="text-sm font-bold text-ink">Privacy quality needs review</h2><p className="mt-2 text-sm leading-6 text-ink-muted">The transform is usable, but detection was intermittent. Review the protected preview and acknowledge this caveat before downloading.</p><Button className="mt-4 h-auto border-0 bg-amber text-white hover:bg-amber/90" type="button" onClick={() => void acknowledge()} disabled={acknowledging}>{acknowledging ? "Recording acknowledgement…" : "Acknowledge and enable download"}</Button></div>}
          {job.qualityFlags.length > 0 && <div className="rounded-lg border border-rule bg-surface px-5 py-5"><h2 className="text-sm font-bold text-ink">Quality notes</h2><ul className="mt-2 space-y-1 text-sm leading-6 text-ink-muted">{job.qualityFlags.map((flag) => <li key={flag}>• {formatQualityFlag(flag)}</li>)}</ul></div>}
        </section>
      </div>}
      <div className="mt-6 flex items-start gap-3 rounded-lg border border-rule bg-surface-soft px-4 py-4 text-xs leading-5 text-ink-muted"><Icon name="info" className="mt-0.5 size-4 shrink-0 text-amber" /><p><span className="font-semibold text-ink">Research privacy transform.</span> The output is not guaranteed anonymous. Use only with approved, consented data and review the protected output before reuse.</p></div>
    </div>
  </div>;
}

function PolicyRow({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-4 border-b border-rule pb-3 last:border-0 last:pb-0"><span className="text-ink-muted">{label}</span><span className="text-right font-semibold text-ink">{value}</span></div>; }
function StatusPill({ status }: { status: VideoPrivacyJob["status"] }) { const tone = status === "ready" ? "border-teal/30 bg-teal-soft text-teal-dark" : status === "failed" || status === "expired" ? "border-red/30 bg-red-soft text-red" : status === "needs_review" ? "border-amber/40 bg-amber-soft text-ink" : "border-rule-strong bg-surface-soft text-ink-muted"; return <span className={`inline-flex min-h-8 items-center rounded-full border px-3 text-xs font-bold ${tone}`}>{statusLabel(status)}</span>; }
function statusLabel(status: VideoPrivacyJob["status"]): string { return ({ queued: "Queued", preflight: "Preflight", processing: "Transforming", validating: "Validating output", ready: "Ready for review", needs_review: "Needs review", failed: "Unavailable", expired: "Expired" })[status]; }
function formatQualityFlag(flag: string): string { return flag === "no_detection" ? "No detection was recorded; the transform failed closed." : flag === "intermittent_detection" ? "Detection was intermittent across the video." : flag.replaceAll("_", " "); }
function formatExpiry(value: string | null): string { if (!value) return "Policy unavailable"; return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
function formatBytes(bytes: number): string { if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`; return `${(bytes / (1024 * 1024)).toFixed(1)} MB`; }
function UnavailableState({ message }: { message: string }) { return <div className="page-frame"><div className="mx-auto max-w-2xl rounded-xl border border-red/30 bg-red-soft px-5 py-6" role="alert"><span className="grid size-10 place-items-center rounded-lg bg-surface text-red"><Icon name="alert" className="size-5" /></span><h1 className="mt-4 text-2xl font-semibold tracking-[-0.02em] text-ink">Protected job unavailable</h1><p className="mt-3 text-sm leading-6 text-red">{message}</p><Button asChild variant="outline" className="mt-6"><Link href="/video-privacy">Return to video privacy</Link></Button></div></div>; }
