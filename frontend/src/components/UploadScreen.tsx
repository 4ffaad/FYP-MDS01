"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { PRIVACY_METHODS, submitAnalysis } from "@/lib/api";
import type { PrivacyMethod } from "@/lib/types";
import { Icon } from "./Icon";

/** Render the single-screen upload and privacy configuration workflow. */
export function UploadScreen() {
  const router = useRouter();
  const privacyMethods = PRIVACY_METHODS;
  const [file, setFile] = useState<File | null>(null);
  const [methodId, setMethodId] = useState(privacyMethods[0]?.id ?? "");
  const [progress, setProgress] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedMethod = privacyMethods.find((method) => method.id === methodId);

  /** Keep the selected upload local until the clinician submits the form. */
  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setError(null);
  }

  /** Validate the form, submit it through the data adapter, and open the run list. */
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose an EEG archive before submitting.");
      return;
    }
    setSubmitting(true);
    setProgress(0);
    setError(null);
    try {
      const result = await submitAnalysis(file, methodId, setProgress);
      router.push(`/dashboard?submitted=${encodeURIComponent(result.jobId)}`);
    } catch (submissionError) {
      if (submissionError instanceof DOMException && submissionError.name === "AbortError") return;
      setError(submissionError instanceof Error ? submissionError.message : "The analysis could not be submitted.");
      setSubmitting(false);
    }
  }

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <div className="max-w-3xl">
          <p className="eyebrow">New analysis</p>
          <h1 className="mt-3 max-w-2xl text-[clamp(2.25rem,5vw,3.65rem)] font-semibold leading-[1.04] tracking-[-0.055em] text-ink">Submit an EEG recording for analysis.</h1>
          <p className="mt-5 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">Upload a recording, choose the privacy configuration, and send it into the protected analysis workflow.</p>
        </div>

        <div className="mt-10 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_330px]">
          <form className="panel overflow-hidden" onSubmit={handleSubmit}>
            <div className="border-b border-rule px-5 py-5 sm:px-7">
              <div className="flex items-start justify-between gap-5">
                <div>
                  <h2 className="text-base font-bold tracking-[-0.015em]">Recording and privacy method</h2>
                  <p className="mt-1 text-sm text-ink-muted">The upload is validated before any downstream processing begins.</p>
                </div>
                <Icon name="file" className="size-5 shrink-0 text-teal" />
              </div>
            </div>

            <div className="space-y-8 px-5 py-6 sm:px-7 sm:py-7">
              <div>
                <label className="text-sm font-bold text-ink" htmlFor="eeg-file">EEG recording</label>
                <p className="mt-1 text-sm text-ink-muted">Choose one ZIP archive containing one or more EDF recordings.</p>
                <label className="mt-4 flex min-h-32 cursor-pointer items-center justify-between gap-4 rounded-lg border border-dashed border-rule-strong bg-surface-soft px-5 py-5 transition-colors hover:border-teal hover:bg-teal-soft/40" htmlFor="eeg-file">
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-md bg-teal-soft text-teal-dark"><Icon name="upload" className="size-5" /></span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-ink">{file ? "Archive selected" : "Choose an EEG ZIP archive"}</span>
                      <span className="mt-1 block truncate text-xs text-ink-muted">{file ? `${file.size > 0 ? "Ready to submit" : "Selected file"}` : "EDF files are checked before processing."}</span>
                    </span>
                  </span>
                  <span className="shrink-0 rounded-md border border-rule-strong bg-surface px-3 py-2 text-xs font-bold text-teal-dark">Browse</span>
                  <input className="sr-only" id="eeg-file" type="file" accept=".zip,application/zip" onChange={handleFileChange} />
                </label>
                {file && <p className="mt-2 font-mono text-[0.68rem] text-ink-faint" aria-live="polite">ZIP archive ready · original filename hidden</p>}
              </div>

              <fieldset>
                <legend className="text-sm font-bold text-ink">Requested privacy configuration</legend>
                <p className="mt-1 text-sm text-ink-muted">Record the configuration requested for this analysis run.</p>
                <div className="mt-4 grid gap-2" role="radiogroup" aria-label="Requested privacy configuration">
                  {privacyMethods.map((method) => (
                    <PrivacyOption key={method.id} method={method} selected={method.id === methodId} onSelect={setMethodId} />
                  ))}
                </div>
                {selectedMethod && <p className="mt-3 rounded-md bg-surface-soft px-3 py-2.5 text-xs leading-5 text-ink-muted">{selectedMethod.description}</p>}
                <p className="mt-3 text-xs leading-5 text-ink-muted" role="note">Every upload receives EDF metadata de-identification. Other requested configurations are recorded for the run, not applied as processing modes in this prototype.</p>
              </fieldset>

              {error && <div className="flex items-start gap-2.5 rounded-md border border-red/30 bg-red-soft px-3.5 py-3 text-sm text-red" role="alert"><Icon name="alert" className="mt-0.5 size-4 shrink-0" /><span>{error}</span></div>}

              {submitting && <div aria-live="polite"><div className="mb-2 flex justify-between text-xs text-ink-muted"><span>Preparing submission</span><span className="font-mono tabular-nums">{progress}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress"><div className="h-full bg-teal transition-[width] duration-300" style={{ width: `${progress}%` }} /></div></div>}
            </div>

            <div className="flex flex-col gap-3 border-t border-rule bg-surface-soft px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
              <p className="text-xs leading-5 text-ink-muted">You can submit another recording while this run processes.</p>
              <button className="button-primary w-full sm:w-auto" type="submit" disabled={submitting}>
                {submitting ? <Icon name="spinner" className="size-4 animate-spin" /> : <Icon name="arrow" className="size-4" />}
                {submitting ? "Submitting…" : "Submit for Analysis"}
              </button>
            </div>
          </form>

          <aside className="panel overflow-hidden">
            <div className="border-b border-rule px-5 py-5">
              <div className="flex items-center gap-2 text-sm font-bold"><Icon name="shield" className="size-5 text-teal" />What happens next</div>
              <p className="mt-2 text-sm leading-6 text-ink-muted">The run moves through a small, inspectable sequence after you submit it.</p>
            </div>
            <ol className="divide-y divide-rule">
              <ProcessStep number="01" title="Stored privately" description="The original archive is retained inside protected session storage." />
              <ProcessStep number="02" title="De-identified" description="Patient-identifying EDF metadata is removed before analysis." />
              <ProcessStep number="03" title="Analysed" description="The pipeline prepares the signal and produces a development result." />
            </ol>
            <div className="border-t border-rule bg-amber-soft px-5 py-4 text-xs leading-5 text-amber"><span className="font-bold">Review boundary.</span> The development model and attention overlay are non-clinical.</div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function PrivacyOption({ method, selected, onSelect }: { method: PrivacyMethod; selected: boolean; onSelect: (id: string) => void }) {
  return (
    <label className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3.5 py-3 transition-colors ${selected ? "border-teal bg-teal-soft/50" : "border-rule bg-surface hover:border-rule-strong"}`}>
      <input className="mt-1 size-4 accent-teal" type="radio" name="privacy-method" value={method.id} checked={selected} onChange={() => onSelect(method.id)} />
      <span className="min-w-0"><span className="block text-sm font-semibold text-ink">{method.label}</span><span className="mt-0.5 block text-xs leading-5 text-ink-muted">{method.description}</span></span>
    </label>
  );
}

function ProcessStep({ number, title, description }: { number: string; title: string; description: string }) {
  return <li className="flex gap-3.5 px-5 py-4"><span className="font-mono text-[0.68rem] font-bold text-teal">{number}</span><span><span className="block text-sm font-semibold text-ink">{title}</span><span className="mt-1 block text-xs leading-5 text-ink-muted">{description}</span></span></li>;
}
