"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { deleteUploadDraft, finalizeUploadDraft, getUploadDraft, PRIVACY_METHODS, stageUpload } from "@/lib/api";
import type { UploadDraft } from "@/lib/types";
import { Icon } from "./Icon";
import { PrivacyPreview } from "./PrivacyPreview";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const DRAFT_STORAGE_KEY = "mds01.active-upload-draft";

type UploadStep = "select" | "staging" | "configure";

/** Render the staged-upload and privacy-selection workflow. */
export function UploadScreen() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<UploadStep>("select");
  const [draft, setDraft] = useState<UploadDraft | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [signalObfuscation, setSignalObfuscation] = useState(false);
  const [progress, setProgress] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedMethod = signalObfuscation ? PRIVACY_METHODS[1] : PRIVACY_METHODS[0];

  useEffect(() => {
    const saved = window.sessionStorage.getItem(DRAFT_STORAGE_KEY);
    if (!saved) return;
    let mounted = true;
    void Promise.resolve().then(async () => {
      if (!mounted) return;
      try {
        const parsed = JSON.parse(saved) as { draftId: string; fileSize?: number };
        setStep("staging");
        setFileSize(parsed.fileSize ?? null);
        const activeDraft = await getUploadDraft(parsed.draftId);
        if (!mounted) return;
        setDraft(activeDraft);
        setStep("configure");
      } catch {
        if (!mounted) return;
        window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
        setStep("select");
      }
    });
    return () => { mounted = false; };
  }, []);

  /** Encrypt the selected ZIP into a temporary backend draft. */
  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    if (!nextFile) return;
    setStep("staging");
    setProgress(0);
    setFileSize(nextFile.size);
    setDraft(null);
    setError(null);
    try {
      const nextDraft = await stageUpload(nextFile, setProgress);
      setDraft(nextDraft);
      window.sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify({ draftId: nextDraft.draftId, fileSize: nextFile.size }));
      setStep("configure");
    } catch (stagingError) {
      if (fileInputRef.current) fileInputRef.current.value = "";
      setStep("select");
      setError(stagingError instanceof Error ? stagingError.message : "The archive could not be secured.");
    }
  }

  /** Remove the staged archive and return to the single-card upload state. */
  async function handleReset() {
    if (draft) {
      try { await deleteUploadDraft(draft.draftId); } catch { /* The draft may already have expired. */ }
    }
    window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setDraft(null);
    setFileSize(null);
    setProgress(0);
    setError(null);
    setStep("select");
  }

  /** Finalize the selected privacy method and open the processing session. */
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) {
      setError("Secure an EEG ZIP archive before choosing a privacy method.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await finalizeUploadDraft(draft.draftId, signalObfuscation ? ["metadata-scrub", "signal-obfuscation"] : ["metadata-scrub"]);
      window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
      router.push(`/sessions/${encodeURIComponent(result.sessionId)}`);
    } catch (submissionError) {
      setSubmitting(false);
      setError(submissionError instanceof Error ? submissionError.message : "The analysis could not be submitted.");
    }
  }

  if (step === "select" || step === "staging") {
    return (
      <div className="page-frame">
        <div className="mx-auto max-w-2xl animate-enter-up">
          <h1 className="text-[clamp(2rem,5vw,3.4rem)] font-semibold leading-[1.05] tracking-[-0.055em] text-ink">Start with one EEG archive.</h1>
          <p className="mt-5 max-w-xl text-[0.98rem] leading-7 text-ink-muted">The archive is encrypted and staged privately first. You will choose how the analysis should handle the signal next.</p>

          <section className="panel mt-10 overflow-hidden" aria-labelledby="upload-heading">
            <div className="px-5 py-7 sm:px-8 sm:py-9">
              <div className="flex items-start gap-4">
                <span className="grid size-11 shrink-0 place-items-center rounded-md bg-teal-soft text-teal"><Icon name="upload" className="size-5" weight="bold" /></span>
                <div>
                  <h2 id="upload-heading" className="text-lg font-bold tracking-[-0.02em]">Secure an EEG ZIP archive</h2>
                  <p className="mt-2 text-sm leading-6 text-ink-muted">Choose one ZIP containing the EDF recordings for this analysis session.</p>
                </div>
              </div>

              <label className="mt-8 flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-rule-strong bg-surface-soft px-6 py-8 text-center outline-none transition-colors hover:border-teal hover:bg-teal-soft/40 focus-within:border-teal focus-within:ring-4 focus-within:ring-teal/20" htmlFor="eeg-file">
                <Icon name={step === "staging" ? "spinner" : "file"} className={`size-8 text-teal ${step === "staging" ? "animate-spin" : ""}`} />
                <span className="mt-4 text-sm font-bold text-ink">{step === "staging" ? "Encrypting archive…" : "Choose an EEG ZIP archive"}</span>
                <span className="mt-1 text-xs text-ink-muted">Original filenames are not shown in this workspace.</span>
                <Button asChild size="sm" className="mt-5 rounded-full bg-teal px-4 py-2 text-xs font-bold text-white hover:bg-teal-dark"><span>Browse files</span></Button>
                <input ref={fileInputRef} className="sr-only" id="eeg-file" aria-label="EEG ZIP archive" type="file" accept=".zip,application/zip" onChange={(event) => void handleFileChange(event)} disabled={step === "staging"} />
              </label>

              {step === "staging" && <div className="mt-6" aria-live="polite"><div className="flex justify-between text-xs text-ink-muted"><span>Securing temporary upload</span><span className="font-mono tabular-nums">{progress}%</span></div><Progress value={progress} className="mt-2 h-1.5 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal" aria-label="Archive encryption progress" /></div>}
              {error && <div className="mt-6 flex items-start gap-2.5 rounded-md border border-red/30 bg-red-soft px-3.5 py-3 text-sm text-red" role="alert"><Icon name="alert" className="mt-0.5 size-4 shrink-0" /><span>{error}</span></div>}
            </div>
            <div className="flex items-start gap-3 border-t border-rule bg-surface-soft px-5 py-5 text-xs leading-5 text-ink-muted sm:px-8"><Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" /><p><span className="font-semibold text-ink">Private staging.</span> The ZIP is encrypted before the backend waits for your privacy selection.</p></div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <button className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" type="button" onClick={() => void handleReset()}><Icon name="back" className="size-4" />Choose a different archive</button>
        <div className="mt-5 max-w-3xl"><h1 className="text-[clamp(2rem,5vw,3.4rem)] font-semibold leading-[1.05] tracking-[-0.055em] text-ink">Choose the privacy treatment.</h1><p className="mt-5 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">Metadata protection is always on. Add signal obfuscation when you want an additional transformation before model scoring.</p></div>

        <form className="mt-10 grid items-start gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]" onSubmit={(event) => void handleSubmit(event)}>
          <section className="panel overflow-hidden" aria-labelledby="privacy-heading">
            <div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="privacy-heading" className="text-base font-bold">Privacy configuration</h2><p className="mt-1 text-sm leading-6 text-ink-muted">The selected configuration is applied before the model receives the data.</p></div>
            <div className="space-y-3 px-5 py-6 sm:px-7">
              <div className="rounded-lg border border-teal bg-teal-soft/40 px-4 py-4">
                <div className="flex items-start gap-3"><Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal-dark" /><div><p className="text-sm font-bold text-ink">Metadata scrub <span className="ml-1 text-xs font-semibold text-teal-dark">Required baseline</span></p><p className="mt-1 text-xs leading-5 text-ink-muted">Identifying EDF header fields are removed. The waveform shape is preserved.</p></div></div>
              </div>
              <label className={`block cursor-pointer rounded-lg border px-4 py-4 transition-colors ${signalObfuscation ? "border-teal bg-teal-soft/50" : "border-rule bg-surface hover:border-rule-strong"}`}>
                <span className="flex items-start gap-3"><input className="mt-1 size-4 accent-teal" type="checkbox" name="signal-obfuscation" checked={signalObfuscation} onChange={(event) => setSignalObfuscation(event.target.checked)} /><span><span className="block text-sm font-bold text-ink">Signal obfuscation</span><span className="mt-1 block text-xs leading-5 text-ink-muted">{PRIVACY_METHODS[1].description}</span></span></span>
              </label>
              <p className="rounded-md bg-surface-soft px-3 py-2 text-xs leading-5 text-ink-muted"><span className="font-semibold text-ink">Selected pipeline:</span> metadata scrub → {signalObfuscation ? "signal obfuscation (Apply both)" : "no additional transformation"}.</p>
              {error && <div className="flex items-start gap-2.5 rounded-md border border-red/30 bg-red-soft px-3.5 py-3 text-sm text-red" role="alert"><Icon name="alert" className="mt-0.5 size-4 shrink-0" /><span>{error}</span></div>}
            </div>
            <div className="border-t border-rule bg-surface-soft px-5 py-5 sm:px-7"><div className="flex items-start gap-3 text-xs leading-5 text-ink-muted"><Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" /><p><span className="font-semibold text-ink">{fileSize === null ? "Archive staged" : `${formatBytes(fileSize)} staged privately`}.</span> Draft expires {formatExpiry(draft?.expiresAt)}.</p></div><Button className="button-primary mt-5 h-auto w-full border-0" type="submit" disabled={submitting || !selectedMethod}>{submitting ? <Icon name="spinner" className="size-4 animate-spin" /> : <Icon name="arrow" className="size-4" />}{submitting ? "Starting analysis…" : "Submit for analysis"}</Button></div>
          </section>

          {selectedMethod && <div className="min-w-0 [&_.overflow-x-auto]:overflow-x-hidden [&_.overflow-x-auto>div]:!min-w-0"><PrivacyPreview method={selectedMethod} /></div>}
        </form>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatExpiry(value?: string): string {
  if (!value) return "soon";
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}
