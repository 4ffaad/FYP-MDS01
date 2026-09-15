"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import {
  deleteUploadDraft,
  finalizeUploadDraft,
  getUploadDraft,
  PRIVACY_METHODS,
  stageUpload,
} from "@/lib/api";
import { uploadDetection } from "@/lib/video-detection";
import type { UploadDraft } from "@/lib/types";
import { formatBytes } from "@/lib/format";
import { Icon } from "./Icon";
import { PrivacyPreview } from "./PrivacyPreview";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const LiquidSignal = dynamic(
  () => import("./LiquidSignal").then((module) => module.LiquidSignal),
  { ssr: false },
);

const DRAFT_STORAGE_KEY = "mds01.active-upload-draft";

type UploadStep = "select" | "staging" | "configure";

/** Join the two modality upload paths without creating a second backend workflow. */
export function UploadScreen() {
  const router = useRouter();
  const eegInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<UploadStep>("select");
  const [draft, setDraft] = useState<UploadDraft | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [eegSize, setEegSize] = useState<number | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [signalObfuscation, setSignalObfuscation] = useState(false);
  const [progress, setProgress] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [partialSessionId, setPartialSessionId] = useState<string | null>(null);

  const hasData = Boolean(draft || videoFile);
  const selectedMethod = signalObfuscation
    ? PRIVACY_METHODS[1]
    : PRIVACY_METHODS[0];

  useEffect(() => {
    const saved = window.sessionStorage.getItem(DRAFT_STORAGE_KEY);
    if (!saved) return;
    let mounted = true;
    void Promise.resolve().then(async () => {
      try {
        const parsed = JSON.parse(saved) as {
          draftId: string;
          fileSize?: number;
        };
        const activeDraft = await getUploadDraft(parsed.draftId);
        if (!mounted) return;
        setDraft(activeDraft);
        setEegSize(parsed.fileSize ?? null);
        setStep("configure");
      } catch {
        if (mounted) window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  async function stageEegFile(file: File) {
    setStep("staging");
    setProgress(0);
    setEegSize(file.size);
    setError(null);
    try {
      const nextDraft = await stageUpload(file, setProgress);
      setDraft(nextDraft);
      window.sessionStorage.setItem(
        DRAFT_STORAGE_KEY,
        JSON.stringify({ draftId: nextDraft.draftId, fileSize: file.size }),
      );
      setStep("configure");
    } catch (uploadError) {
      if (eegInputRef.current) eegInputRef.current.value = "";
      setStep(videoFile ? "configure" : "select");
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "The VEEG archive could not be secured.",
      );
    }
  }

  async function handleEegChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (file) await stageEegFile(file);
  }

  function selectVideoFile(file: File | null) {
    if (!file) return;
    setVideoFile(file);
    setError(null);
    if (step !== "staging") setStep("configure");
  }

  function handleVideoChange(event: ChangeEvent<HTMLInputElement>) {
    selectVideoFile(event.target.files?.[0] ?? null);
  }

  async function handleReset() {
    if (draft) {
      try {
        await deleteUploadDraft(draft.draftId);
      } catch {
        // The temporary draft may already have expired.
      }
    }
    window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
    if (eegInputRef.current) eegInputRef.current.value = "";
    setDraft(null);
    setCaseId(null);
    setEegSize(null);
    setVideoFile(null);
    setProgress(0);
    setError(null);
    setPartialSessionId(null);
    setStep("select");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasData || step === "staging") {
      setError(
        "Choose a VEEG archive, a patient video, or both before continuing.",
      );
      return;
    }

    setSubmitting(true);
    setError(null);
    setPartialSessionId(null);
    let sessionId: string | null = null;
    let videoJobId: string | null = null;
    let analysisCaseId = caseId;

    try {
      if (draft) {
        const result = await finalizeUploadDraft(
          draft.draftId,
          signalObfuscation
            ? ["metadata-scrub", "signal-obfuscation"]
            : ["metadata-scrub"],
          analysisCaseId ?? undefined,
        );
        sessionId = result.sessionId;
        analysisCaseId = result.caseId;
      }

      if (videoFile) {
        setProgress(0);
        const result = await uploadDetection(
          videoFile,
          setProgress,
          analysisCaseId ?? undefined,
        );
        videoJobId = result.job.job_id;
        analysisCaseId = result.job.case_id ?? analysisCaseId;
      }

      setCaseId(analysisCaseId);

      window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
      if (sessionId && videoJobId) {
        router.push(
          `/analysis?sessionId=${encodeURIComponent(sessionId)}&videoJobId=${encodeURIComponent(videoJobId)}`,
        );
      } else if (sessionId) {
        router.push(`/sessions/${encodeURIComponent(sessionId)}`);
      } else if (videoJobId) {
        router.push(`/video-detection/${encodeURIComponent(videoJobId)}`);
      }
    } catch (submissionError) {
      if (sessionId) setPartialSessionId(sessionId);
      setSubmitting(false);
      setError(
        sessionId
          ? "The VEEG analysis was submitted, but the video could not be started. You can still review the VEEG below."
          : submissionError instanceof Error
            ? submissionError.message
            : "The analysis could not be submitted.",
      );
    }
  }

  if (step === "select" || step === "staging") {
    return (
      <div className="page-frame">
        <div className="animate-enter-up">
          <SetupSteps current="upload" />
          <div className="mt-7 max-w-3xl">
            <p className="eyebrow">New review</p>
            <h1 className="mt-3 text-[clamp(2rem,5vw,2.8rem)] font-semibold leading-[1.06] tracking-[-0.045em] text-ink">
              Start a VEEG analysis
            </h1>
            <p className="mt-4 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">
              Select one input or pair both. VEEG and video stay on separate
              privacy-first paths, then return as one review.
            </p>
          </div>

          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            <ModalityPicker
              id="eeg-file"
              title="VEEG archive"
              eyebrow="Required"
              description="A ZIP containing EDF recordings. The archive is encrypted and staged before you choose the signal treatment."
              accept=".zip,application/zip"
              icon="activity"
              busy={step === "staging"}
              selected={Boolean(draft) || step === "staging"}
              selectedLabel={
                step === "staging"
                  ? "Securing archive…"
                  : "Archive staged privately"
              }
              inputRef={eegInputRef}
              onChange={(event) => void handleEegChange(event)}
              onFile={stageEegFile}
            />
            <ModalityPicker
              id="video-file"
              title="Patient video"
              eyebrow="Optional"
              description="An MP4, MOV, or WebM clip. Face redaction runs before VSViG pose extraction and visual scoring."
              accept=".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm"
              icon="video"
              busy={step === "staging"}
              selected={Boolean(videoFile)}
              selectedLabel="Video ready to submit"
              onChange={handleVideoChange}
              onFile={selectVideoFile}
            />
          </div>

          {step === "staging" && (
            <div className="mt-6 max-w-xl" aria-live="polite">
              <div className="flex justify-between text-xs text-ink-muted">
                <span>Securing temporary VEEG upload</span>
                <span className="font-mono tabular-nums">{progress}%</span>
              </div>
              <Progress
                value={progress}
                className="mt-2 h-1.5 bg-surface-muted [&_[data-slot=progress-indicator]]:bg-teal"
                aria-label="Archive encryption progress"
              />
            </div>
          )}
          {error && <ErrorNotice message={error} />}
          <PipelinePreview />
        </div>
      </div>
    );
  }

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <button
          className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
          type="button"
          onClick={() => void handleReset()}
        >
          <Icon name="back" className="size-4" />
          Choose different data
        </button>
        <div className="mt-5 max-w-3xl">
          <SetupSteps current="privacy" />
          <p className="eyebrow mt-7">Review the pipeline</p>
          <h1 className="mt-3 text-[clamp(2rem,5vw,2.8rem)] font-semibold leading-[1.06] tracking-[-0.045em] text-ink">
            Set privacy before processing
          </h1>
          <p className="mt-4 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">
            The selected modality determines the privacy treatment and model
            path. A combined upload creates one review page with separate VEEG
            and video status.
          </p>
        </div>

        <form
          className="mt-10 grid items-start gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]"
          onSubmit={(event) => void handleSubmit(event)}
        >
          <section
            className="panel glass-panel overflow-hidden"
            aria-labelledby="pipeline-heading"
          >
            <div className="border-b border-rule px-5 py-5 sm:px-7">
              <h2 id="pipeline-heading" className="text-base font-bold">
                Selected pipelines
              </h2>
              <p className="mt-1 text-sm leading-6 text-ink-muted">
                Privacy runs before model input for both modalities.
              </p>
            </div>
            <div className="space-y-3 px-5 py-6 sm:px-7">
              {draft && !videoFile && (
                <AdditionalPicker
                  id="video-file"
                  label="Add patient video"
                  accept=".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm"
                  onChange={handleVideoChange}
                />
              )}
              {videoFile && !draft && (
                <AdditionalPicker
                  id="eeg-file"
                  label="Add VEEG archive"
                  accept=".zip,application/zip"
                  inputRef={eegInputRef}
                  onChange={(event) => void handleEegChange(event)}
                />
              )}
              {draft && (
                <div className="rounded-xl border border-teal bg-teal-soft/40 px-4 py-4">
                  <PipelineRow
                    icon="activity"
                    title="VEEG analysis"
                    detail={`Encrypt → metadata scrub${signalObfuscation ? " → signal obfuscation" : ""} → H5 model → report`}
                  />
                  <p className="mt-2 pl-8 text-xs font-semibold text-teal-dark">
                    Required baseline
                  </p>
                </div>
              )}
              {videoFile && (
                <div className="rounded-xl border border-cyan/40 bg-cyan-soft/40 px-4 py-4">
                  <PipelineRow
                    icon="activity"
                    title="Video seizure review"
                    detail="Encrypt → face redaction → VSViG model → evidence timeline"
                  />
                  <p className="mt-3 pl-8 text-xs leading-5 text-ink-muted">
                    Audio is excluded from this visual-only detection workflow.
                  </p>
                </div>
              )}
              {draft && (
                <label
                  className={`block cursor-pointer rounded-xl border px-4 py-4 transition-colors ${signalObfuscation ? "border-teal bg-teal-soft/50" : "border-rule bg-surface hover:border-rule-strong"}`}
                >
                  <span className="flex items-start gap-3">
                    <input
                      className="mt-1 size-4 accent-teal"
                      type="checkbox"
                      name="signal-obfuscation"
                      checked={signalObfuscation}
                      onChange={(event) =>
                        setSignalObfuscation(event.target.checked)
                      }
                    />
                    <span>
                      <span className="block text-sm font-bold text-ink">
                        Signal obfuscation
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-ink-muted">
                        {PRIVACY_METHODS[1].description}
                      </span>
                    </span>
                  </span>
                </label>
              )}
              {error && <ErrorNotice message={error} />}
            </div>
            <div className="border-t border-rule bg-surface-soft px-5 py-5 sm:px-7">
              <div className="flex items-start gap-3 text-xs leading-5 text-ink-muted">
                <Icon
                  name="lock"
                  className="mt-0.5 size-4 shrink-0 text-teal"
                />
                <p>
                  <span className="font-semibold text-ink">
                    {draft
                      ? `${formatBytes(eegSize ?? 0)} VEEG archive staged`
                      : "Video selected"}
                    .
                  </span>{" "}
                  Files remain owner-scoped.
                </p>
              </div>
              {partialSessionId && (
                <Link
                  className="mt-3 block text-sm font-semibold text-teal-dark underline underline-offset-4"
                  href={`/sessions/${encodeURIComponent(partialSessionId)}`}
                >
                  Open the submitted VEEG analysis
                </Link>
              )}
              <Button
                className="mt-5 w-full"
                size="lg"
                type="submit"
                disabled={submitting}
              >
                {submitting ? (
                  <Icon name="spinner" className="size-4 animate-spin" />
                ) : (
                  <Icon name="arrow" className="size-4" />
                )}
                {submitting ? "Starting analysis…" : "Submit for analysis"}
              </Button>
            </div>
          </section>

          {draft && (
            <div className="min-w-0 [&_.overflow-x-auto]:overflow-x-hidden [&_.overflow-x-auto>div]:!min-w-0">
              <PrivacyPreview method={selectedMethod} />
            </div>
          )}
          {videoFile && !draft && <VideoPrivacySummary />}
        </form>
      </div>
    </div>
  );
}

function ModalityPicker({
  id,
  title,
  eyebrow,
  description,
  accept,
  icon,
  busy,
  selected,
  selectedLabel,
  inputRef,
  onChange,
  onFile,
}: {
  id: string;
  title: string;
  eyebrow: "Required" | "Optional";
  description: string;
  accept: string;
  icon: "activity" | "video";
  busy: boolean;
  selected: boolean;
  selectedLabel: string;
  inputRef?: React.RefObject<HTMLInputElement | null>;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onFile: (file: File) => void | Promise<void>;
}) {
  const [dragging, setDragging] = useState(false);

  return (
    <section
      className={`upload-lane glass-panel rounded-2xl border p-5 transition-all sm:p-6 ${selected ? "is-selected border-teal bg-teal-soft/35" : "border-rule bg-surface/80 hover:-translate-y-0.5 hover:border-teal/40"}`}
      aria-labelledby={`${id}-heading`}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-ink text-white shadow-sm">
          <Icon name={icon} className="size-6" weight="bold" />
        </span>
        <span className={`upload-badge ${selected ? "is-selected" : ""}`}>
          {selected ? "Ready" : eyebrow}
        </span>
      </div>
      <div className="mt-5 min-w-0">
        <h2
          id={`${id}-heading`}
          className="text-lg font-bold tracking-[-0.02em]"
        >
          {title}
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">{description}</p>
      </div>
      <label
        className={`upload-dropzone mt-6 flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-5 py-6 text-center outline-none transition-all focus-within:border-teal focus-within:ring-4 focus-within:ring-teal/20 ${dragging ? "is-dragging border-teal bg-teal-soft/60" : "border-rule-strong bg-surface-soft hover:border-teal hover:bg-teal-soft/35"}`}
        htmlFor={id}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file) void onFile(file);
        }}
      >
        <Icon
          name={busy ? "spinner" : selected ? "check" : "upload"}
          className={`size-7 text-teal ${busy ? "animate-spin" : selected ? "upload-check-pop" : ""}`}
          weight="bold"
        />
        <span className="mt-3 text-sm font-bold text-ink">
          {selected ? selectedLabel : "Drop here or browse"}
        </span>
        <span className="mt-1 text-xs text-ink-muted">
          {selected
            ? "Ready for the next step"
            : "Your local filename is not shown in the workspace"}
        </span>
        <input
          ref={inputRef}
          className="sr-only"
          id={id}
          aria-label={title}
          type="file"
          accept={accept}
          onChange={onChange}
          disabled={busy}
        />
      </label>
    </section>
  );
}

function AdditionalPicker({
  id,
  label,
  accept,
  inputRef,
  onChange,
}: {
  id: string;
  label: string;
  accept: string;
  inputRef?: React.RefObject<HTMLInputElement | null>;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label
      className="flex min-h-12 cursor-pointer items-center justify-between gap-4 rounded-xl border border-dashed border-rule-strong bg-surface-soft px-4 py-3 text-sm font-semibold text-teal-dark transition-colors hover:border-teal hover:bg-teal-soft/35 focus-within:ring-4 focus-within:ring-teal/20"
      htmlFor={id}
    >
      <span className="flex items-center gap-2">
        <Icon name="upload" className="size-4" />
        {label}
      </span>
      <span className="rounded-full bg-surface px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-[0.08em] text-ink-faint">
        Optional
      </span>
      <input
        ref={inputRef}
        className="sr-only"
        id={id}
        aria-label={label}
        type="file"
        accept={accept}
        onChange={onChange}
      />
    </label>
  );
}

function PipelinePreview() {
  return (
    <section
      className="liquid-surface glass-panel relative mt-8 overflow-hidden rounded-2xl border border-rule px-5 py-5 sm:px-6"
      aria-labelledby="pipeline-preview-heading"
    >
      <div className="relative z-10 flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">At a glance</p>
          <h2
            id="pipeline-preview-heading"
            className="mt-1 text-base font-bold"
          >
            One upload, two protected paths
          </h2>
        </div>
        <LiquidSignal />
      </div>
      <div className="relative z-10 mt-5 grid gap-3 text-xs font-semibold text-ink-muted sm:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] sm:items-center">
        {(["Upload", "Privacy", "Model", "Review"] as const).map(
          (label, index) => (
            <span key={label} className="contents">
              <span className="rounded-lg bg-surface-soft px-3 py-2 text-center text-ink">
                {label}
              </span>
              {index < 3 && (
                <span className="hidden text-center text-teal sm:block">→</span>
              )}
            </span>
          ),
        )}
      </div>
      <p className="mt-4 text-xs leading-5 text-ink-muted">
        VEEG uses the reviewed H5 contract. Video uses face-redacted frames with
        a separate VSViG review output. Both remain research-only.
      </p>
    </section>
  );
}

function PipelineRow({
  icon,
  title,
  detail,
}: {
  icon: "activity";
  title: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon
        name={icon}
        className="mt-0.5 size-5 shrink-0 text-teal-dark"
        weight="bold"
      />
      <div>
        <p className="text-sm font-bold text-ink">{title}</p>
        <p className="mt-1 text-xs leading-5 text-ink-muted">{detail}</p>
      </div>
    </div>
  );
}

function VideoPrivacySummary() {
  return (
    <section
      className="panel glass-panel p-6"
      aria-labelledby="video-privacy-summary-heading"
    >
      <div className="flex items-start gap-3">
        <Icon
          name="shield"
          className="size-6 shrink-0 text-teal-dark"
          weight="bold"
        />
        <div>
          <h2
            id="video-privacy-summary-heading"
            className="text-base font-bold"
          >
            Video privacy is fixed for detection
          </h2>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            The detector receives face-redacted frames. Audio is excluded, and
            the output is labeled as an uncalibrated model score until a video
            calibration process is validated.
          </p>
        </div>
      </div>
    </section>
  );
}

function ErrorNotice({ message }: { message: string }) {
  return (
    <div
      className="mt-5 flex items-start gap-2.5 rounded-xl border border-red/30 bg-red-soft px-3.5 py-3 text-sm leading-5 text-red"
      role="alert"
    >
      <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

function SetupSteps({ current }: { current: "upload" | "privacy" }) {
  return (
    <ol
      className="flex max-w-md items-center gap-3 text-xs font-semibold"
      aria-label="Analysis setup progress"
    >
      <li className="flex items-center gap-2 text-teal-dark">
        <span className="grid size-6 place-items-center rounded-full bg-teal text-white">
          {current === "privacy" ? (
            <Icon name="check" className="size-3.5" weight="bold" />
          ) : (
            "1"
          )}
        </span>
        Data
      </li>
      <li className="h-px flex-1 bg-rule" aria-hidden="true" />
      <li
        className={`flex items-center gap-2 ${current === "privacy" ? "text-teal-dark" : "text-ink-muted"}`}
      >
        <span
          className={`grid size-6 place-items-center rounded-full ${current === "privacy" ? "bg-teal text-white" : "border border-rule-strong bg-surface"}`}
        >
          2
        </span>
        Privacy
      </li>
      <li className="h-px flex-1 bg-rule" aria-hidden="true" />
      <li className="flex items-center gap-2 text-ink-muted">
        <span className="grid size-6 place-items-center rounded-full border border-rule-strong bg-surface">
          3
        </span>
        Review
      </li>
    </ol>
  );
}
