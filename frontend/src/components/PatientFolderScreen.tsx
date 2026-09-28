"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { MotionConfig, motion } from "motion/react";
import {
  ApiError,
  API_STUB_ENABLED,
  deleteUploadDraft,
  finalizeUploadDraft,
  pollRetryDelay,
  PRIVACY_METHODS,
  savePatientProfile,
  stageUpload,
  shouldRetryRequest,
} from "@/lib/api";

import {
  buildEegArchive,
  classifyPatientFolder,
  type PatientFolderSelection,
} from "@/lib/patient-folder";
import { Icon } from "./Icon";
import { LoadingOrb } from "./LoadingOrb";
import {
  PatientDetailsEditor,
  type PatientDetailDraft,
} from "./PatientDetailsEditor";
import { PatientFolderMediaStep } from "./PatientFolderMediaStep";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { getDetection, uploadDetection } from "@/lib/video-detection";

const REPORT_ENDPOINT = "/api/patient-report";
const MAX_JOB_STATUS_RETRIES = 4;

interface VideoUploadIssue {
  message: string;
  retryable: boolean;
  disposition: "not-accepted" | "status-unconfirmed";
}

function throwIfAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    throw (
      signal.reason ??
      new DOMException("The intake was canceled.", "AbortError")
    );
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

function waitForSignal(milliseconds: number, signal?: AbortSignal) {
  throwIfAborted(signal);
  return new Promise<void>((resolve, reject) => {
    let timer: number | undefined;
    const cleanup = () => {
      if (timer !== undefined) window.clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    };
    const onAbort = () => {
      cleanup();
      reject(
        signal?.reason ??
          new DOMException("The intake was canceled.", "AbortError"),
      );
    };
    timer = window.setTimeout(() => {
      cleanup();
      resolve();
    }, milliseconds);
    signal?.addEventListener("abort", onAbort, { once: true });
    if (signal?.aborted) onAbort();
  });
}

async function waitForJob<T extends { status: string }>(
  read: () => Promise<T>,
  terminalStatuses: readonly string[],
  onUpdate: (job: T) => void,
  signal?: AbortSignal,
): Promise<T> {
  let retryAttempt = 0;
  while (true) {
    throwIfAborted(signal);
    try {
      const job = await read();
      throwIfAborted(signal);
      onUpdate(job);
      if (terminalStatuses.includes(job.status)) return job;
      retryAttempt = 0;
    } catch (error) {
      if (signal?.aborted || isAbortError(error)) throw error;
      if (!shouldRetryRequest(error)) throw error;
      retryAttempt += 1;
      if (retryAttempt > MAX_JOB_STATUS_RETRIES) {
        throw new Error(
          `Could not confirm the video job status after ${MAX_JOB_STATUS_RETRIES} retries. Check Patient History before retrying.`,
        );
      }
      await waitForSignal(pollRetryDelay(retryAttempt), signal);
      continue;
    }
    await waitForSignal(1500, signal);
  }
}

function jobStatusLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Queued";
    case "ready":
      return "Complete";
    case "needs_review":
      return "Needs review";
    case "failed":
      return "Failed";
    case "expired":
      return "Expired";
    default:
      return "Processing";
  }
}

function videoUploadIssue(
  error: unknown,
  acceptedJob = false,
): VideoUploadIssue {
  if (acceptedJob) {
    return {
      message:
        "The video job was accepted, but its status could not be confirmed. Check Patient History before retrying.",
      retryable: false,
      disposition: "status-unconfirmed",
    };
  }
  if (error instanceof ApiError) {
    switch (error.status) {
      case 409:
        return {
          message:
            "Another video analysis is active. This clip was not queued.",
          retryable: true,
          disposition: "not-accepted",
        };
      case 413:
        return {
          message:
            "This clip exceeds the configured video size or duration limit.",
          retryable: false,
          disposition: "not-accepted",
        };
      case 415:
        return {
          message:
            "This video format is not supported by the active model runtime.",
          retryable: false,
          disposition: "not-accepted",
        };
      case 422:
        return {
          message:
            "This clip does not meet the active VSViG input contract. No video inference result was produced.",
          retryable: false,
          disposition: "not-accepted",
        };
      case 503:
        return {
          message: "Video detection is unavailable in this runtime.",
          retryable: true,
          disposition: "not-accepted",
        };
      default:
        return {
          message: "The video was not accepted by the detection service.",
          retryable: false,
          disposition:
            error.status >= 400 && error.status < 500
              ? "not-accepted"
              : "status-unconfirmed",
        };
    }
  }
  return {
    message:
      "The upload outcome could not be confirmed. Check Patient History before retrying to avoid duplicate work.",
    retryable: false,
    disposition: "status-unconfirmed",
  };
}

/** One-folder intake that keeps EEG and video policy visible side by side. */
export function PatientFolderScreen() {
  const router = useRouter();
  const folderInput = useRef<HTMLInputElement>(null);
  const selectionGeneration = useRef(0);
  const reportAbortController = useRef<AbortController | null>(null);
  const workflowAbortController = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const detailsStepRef = useRef<HTMLDivElement>(null);
  const previousIntakeStep = useRef<"media" | "details">("media");
  const [selection, setSelection] = useState<PatientFolderSelection | null>(
    null,
  );
  const [intakeStep, setIntakeStep] = useState<"media" | "details">("media");
  const [patientDetails, setPatientDetails] = useState<PatientDetailDraft[]>(
    [],
  );
  const [reportTruncated, setReportTruncated] = useState(false);
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const [signalObfuscation, setSignalObfuscation] = useState(false);
  const [videoDetectionErrors, setVideoDetectionErrors] = useState<
    Record<number, VideoUploadIssue>
  >({});
  const [videoDetectionJobIds, setVideoDetectionJobIds] = useState<
    Record<number, string>
  >({});

  const [step, setStep] = useState("Select one patient folder");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [profileSaved, setProfileSaved] = useState(false);
  const detailId = useRef(0);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      selectionGeneration.current += 1;
      reportAbortController.current?.abort();
      workflowAbortController.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (previousIntakeStep.current !== intakeStep && intakeStep === "details") {
      const target = detailsStepRef.current;
      if (target) {
        target.scrollIntoView({
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "auto"
            : "smooth",
          block: "start",
        });
        target.focus({ preventScroll: true });
      }
    }
    previousIntakeStep.current = intakeStep;
  }, [intakeStep]);

  const onFolderInput = (element: HTMLInputElement | null) => {
    folderInput.current = element;
    element?.setAttribute("webkitdirectory", "");
  };

  async function handleFolderChange(event: ChangeEvent<HTMLInputElement>) {
    const generation = ++selectionGeneration.current;
    reportAbortController.current?.abort();
    reportAbortController.current = null;
    if (draftId && !sessionId) {
      void deleteUploadDraft(draftId).catch(() => undefined);
    }
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    const nextSelection = classifyPatientFolder(files);
    setSelection(nextSelection);
    setIntakeStep("media");
    setDraftId(null);
    setPatientDetails([]);
    setReportTruncated(false);
    setReportMessage(null);
    setVideoDetectionErrors({});
    setVideoDetectionJobIds({});

    setProgress(0);
    setError(null);

    if (!nextSelection.report) return;
    setReportMessage("Reading the report on this device…");
    const controller = new AbortController();
    reportAbortController.current = controller;
    try {
      const body = new FormData();
      const reportExtension = nextSelection.report.name
        .split(".")
        .pop()
        ?.toLocaleLowerCase("en-US");
      body.append(
        "report",
        nextSelection.report,
        reportExtension === "docx"
          ? "patient-report.docx"
          : "patient-report.doc",
      );
      const response = await fetch(REPORT_ENDPOINT, {
        method: "POST",
        body,
        signal: controller.signal,
        credentials: "same-origin",
        cache: "no-store",
      });
      const payload = (await response.json()) as {
        draft?: {
          details?: Array<{ label: string; value: string }>;
          truncated?: boolean;
        };
        detail?: string;
      };
      if (
        generation !== selectionGeneration.current ||
        controller.signal.aborted
      ) {
        return;
      }
      if (!response.ok || !payload.draft) {
        throw new Error(
          payload.detail ?? "The report could not be read locally.",
        );
      }
      setPatientDetails(
        (payload.draft.details ?? []).map((detail) => ({
          ...detail,
          id: `report-${detailId.current++}`,
          included: false,
        })),
      );
      setReportTruncated(payload.draft.truncated ?? false);
      setReportMessage(null);
    } catch (readError) {
      if (
        generation !== selectionGeneration.current ||
        controller.signal.aborted
      ) {
        return;
      }
      setReportMessage(
        readError instanceof Error
          ? readError.message
          : "The report could not be read locally. Select a readable report to include its details.",
      );
    } finally {
      if (reportAbortController.current === controller) {
        reportAbortController.current = null;
      }
    }
  }

  function togglePatientDetail(id: string, included: boolean) {
    setPatientDetails((current) =>
      current.map((detail) =>
        detail.id === id ? { ...detail, included } : detail,
      ),
    );
  }

  function changePatientDetail(
    id: string,
    key: "label" | "value",
    value: string,
  ) {
    setPatientDetails((current) =>
      current.map((detail) =>
        detail.id === id ? { ...detail, [key]: value } : detail,
      ),
    );
  }

  function addManualPatientDetail() {
    setPatientDetails((current) => [
      ...current,
      {
        id: `manual-${detailId.current++}`,
        label: "",
        value: "",
        included: false,
        manual: true,
      },
    ]);
  }

  function removeManualPatientDetail(id: string) {
    setPatientDetails((current) =>
      current.filter((detail) => detail.id !== id),
    );
  }

  async function submitReview(retryVideoIndexes?: number[]) {
    const selectedEegBundles = selection?.eegCandidates ?? [];
    const selectedDetails = patientDetails
      .filter(
        (detail) =>
          detail.included && detail.label.trim() && detail.value.trim(),
      )
      .map(({ label, value }) => ({
        label: label.trim(),
        value: value.trim(),
      }));
    if (
      !selection ||
      selection.errors.length > 0 ||
      selectedEegBundles.length === 0
    ) {
      setError("Select one or more EEG recordings and one report folder.");
      return;
    }
    if (!identityReady) {
      setError("Add at least one report detail before creating the case.");
      return;
    }
    if (API_STUB_ENABLED) {
      setError("Connect the local API to create a patient review.");
      return;
    }
    const controller = new AbortController();
    workflowAbortController.current = controller;
    const signal = controller.signal;
    setBusy(true);
    setError(null);
    let pendingDraftId = draftId;
    let activeSessionId = sessionId;
    let activeCaseId = caseId;
    let videoIds = videoDetectionJobIds;
    const videoIssues = { ...videoDetectionErrors };
    try {
      if (!activeSessionId) {
        if (!pendingDraftId) {
          setStep(`Preparing ${selectedEegBundles.length} EEG recordings`);
          const archive = await buildEegArchive(selectedEegBundles, (value) => {
            if (mounted.current && !signal.aborted)
              setProgress(Math.round(value * 0.15));
          });
          throwIfAborted(signal);
          setStep("Encrypting the EEG upload");
          const draft = await stageUpload(
            archive,
            (value) => {
              if (mounted.current && !signal.aborted)
                setProgress(15 + Math.round(value * 0.65));
            },
            signal,
          );
          throwIfAborted(signal);
          pendingDraftId = draft.draftId;
          setDraftId(pendingDraftId);
        }
        setStep("Creating the EEG session");
        const finalized = await finalizeUploadDraft(
          pendingDraftId,
          signalObfuscation
            ? ["metadata-scrub", "signal-obfuscation"]
            : ["metadata-scrub"],
          undefined,
          signal,
        );
        throwIfAborted(signal);
        activeSessionId = finalized.sessionId;
        activeCaseId = finalized.caseId;
        if (!activeCaseId)
          throw new Error(
            "The backend did not return an opaque case reference.",
          );
        setSessionId(activeSessionId);
        setCaseId(activeCaseId);
        setDraftId(null);
        pendingDraftId = null;
      }

      if (!profileSaved) {
        if (!activeCaseId)
          throw new Error(
            "The backend did not return an opaque case reference.",
          );
        setStep("Saving the reviewed patient details");
        await savePatientProfile(activeCaseId!, selectedDetails, signal);
        throwIfAborted(signal);
        setProfileSaved(true);
      }

      if (selection.videos.length > 0) {
        const indexes =
          retryVideoIndexes ?? selection.videos.map((_, index) => index);
        for (const [position, index] of indexes.entries()) {
          const videoFile = selection.videos[index];
          let jobId = videoIds[index];
          delete videoIssues[index];
          setVideoDetectionErrors({ ...videoIssues });
          try {
            if (!jobId) {
              setStep(
                `Uploading video analysis ${position + 1} of ${indexes.length}`,
              );
              const { job } = await uploadDetection(
                videoFile,
                (value) => {
                  if (mounted.current && !signal.aborted) {
                    setProgress(
                      Math.round(
                        ((position + value / 100) / indexes.length) * 100,
                      ),
                    );
                  }
                },
                activeCaseId!,
                signal,
              );
              throwIfAborted(signal);
              jobId = job.job_id;
              videoIds = { ...videoIds, [index]: jobId };
              setVideoDetectionJobIds(videoIds);
            }
            setStep(
              `Processing video analysis ${position + 1} of ${indexes.length}`,
            );
            const completedJob = await waitForJob(
              () =>
                getDetection(jobId!, signal).then((response) => response.job),
              ["ready", "failed", "expired"],
              (job) => {
                const status = jobStatusLabel(job.status);
                setStep(
                  `Video analysis ${position + 1} of ${indexes.length}: ${status}`,
                );
              },
              signal,
            );
            setProgress(Math.round(((position + 1) / indexes.length) * 100));
          } catch (videoError) {
            if (signal.aborted || !mounted.current || isAbortError(videoError))
              throw videoError;
            videoIssues[index] = videoUploadIssue(videoError, Boolean(jobId));
            setVideoDetectionErrors({ ...videoIssues });
            if (
              !(videoError instanceof ApiError) ||
              ![413, 415, 422].includes(videoError.status)
            ) {
              for (const remainingIndex of indexes.slice(position + 1)) {
                videoIssues[remainingIndex] = {
                  message:
                    "This clip was not submitted because the previous video job could not be confirmed.",
                  retryable: false,
                  disposition: "not-accepted",
                };
              }
              setVideoDetectionErrors({ ...videoIssues });
              break;
            }
          }
        }
        if (Object.keys(videoIssues).length > 0) {
          const failedVideoCount = Object.keys(videoIssues).length;
          const label =
            failedVideoCount === 1 ? "video clip needs" : "video clips need";
          setError(
            `${failedVideoCount} ${label} attention. ${Object.values(videoIssues)[0]?.message ?? "No video result was produced."}`,
          );
          return;
        }
      }

      if (!mounted.current || signal.aborted) return;
      setStep("Opening the patient case");
      router.push(`/cases/${encodeURIComponent(activeCaseId!)}`);
    } catch (submitError) {
      if (!mounted.current) return;
      if (pendingDraftId && !activeSessionId) setDraftId(pendingDraftId);
      if (signal.aborted || isAbortError(submitError)) {
        setError(
          "Intake canceled. Upload and status checks stopped on this device. Work already accepted by the service may continue; check patient history later.",
        );
      } else {
        setError(
          submitError instanceof Error
            ? submitError.message
            : "The patient review could not be created.",
        );
      }
      if (draftId && !sessionId) {
        // Keep the encrypted draft for retry; it expires through the backend retention sweep.
        setDraftId(draftId);
      }
    } finally {
      if (workflowAbortController.current === controller)
        workflowAbortController.current = null;
      if (mounted.current) {
        setBusy(false);
        setProgress(0);
      }
    }
  }

  const includedPatientDetails = patientDetails.filter(
    (detail) => detail.included && detail.label.trim() && detail.value.trim(),
  );
  const identityReady = includedPatientDetails.length > 0;
  const selectedEegBundles = selection?.eegCandidates ?? [];
  const canContinue = Boolean(
    selection &&
      selection.errors.length === 0 &&
      selectedEegBundles.length > 0 &&
      reportMessage !== "Reading the report on this device…" &&
      !busy,
  );
  const canSubmit = Boolean(
    selection &&
      selection.errors.length === 0 &&
      selectedEegBundles.length > 0 &&
      identityReady &&
      intakeStep === "details" &&
      !API_STUB_ENABLED &&
      !busy,
  );
  const videoAttentionCount = Object.keys(videoDetectionErrors).length;
  const videoRejectedCount = Object.values(videoDetectionErrors).filter(
    (issue) => issue.disposition === "not-accepted",
  ).length;
  const videoUnconfirmedCount = videoAttentionCount - videoRejectedCount;
  const retryableVideoIndexes = Object.entries(videoDetectionErrors)
    .filter(([, issue]) => issue.retryable)
    .map(([index]) => Number(index));

  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame">
        <motion.main
          className="mx-auto max-w-6xl"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <header className="max-w-3xl">
            <p className="eyebrow">New patient review</p>
            <h1 className="mt-3 text-[clamp(2rem,5vw,2.8rem)] font-semibold leading-[1.06] tracking-[-0.045em] text-ink">
              Add a patient recording
            </h1>
            <p className="mt-4 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">
              Keep one patient&apos;s report, multiple EEG recordings, and video
              clips together in one review.
            </p>
            <ol
              className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-b border-rule pb-4 text-xs font-semibold text-ink-muted"
              aria-label="Review steps"
            >
              <li
                className={
                  !selection || intakeStep === "media"
                    ? "rounded-full bg-teal-soft px-3 py-1 text-teal-dark"
                    : "px-3 py-1 text-ink-faint"
                }
                aria-current={
                  !selection || intakeStep === "media" ? "step" : undefined
                }
              >
                01&nbsp; Media
              </li>
              <li
                className={
                  selection && intakeStep === "details" && !sessionId
                    ? "rounded-full bg-teal-soft px-3 py-1 text-teal-dark"
                    : "px-3 py-1 text-ink-faint"
                }
                aria-current={
                  selection && intakeStep === "details" && !sessionId
                    ? "step"
                    : undefined
                }
              >
                02&nbsp; Patient details
              </li>
              <li
                className={
                  sessionId
                    ? "rounded-full bg-teal-soft px-3 py-1 text-teal-dark"
                    : "px-3 py-1 text-ink-faint"
                }
                aria-current={sessionId ? "step" : undefined}
              >
                03&nbsp; Processing
              </li>
            </ol>
          </header>

          {intakeStep === "media" && (
            <section
              className="panel mt-8 p-5 sm:p-7"
              aria-labelledby="folder-heading"
            >
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="eyebrow">Patient recording</p>
                  <h2 id="folder-heading" className="mt-2 text-lg font-bold">
                    Choose one patient folder
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
                    One folder creates one case. Include the report, as many EEG
                    recordings as needed, and the related video clips.
                  </p>
                </div>
                <Button
                  type="button"
                  size="lg"
                  onClick={() => folderInput.current?.click()}
                  disabled={busy || Boolean(sessionId)}
                >
                  <Icon name="file" className="size-4" />
                  Choose patient folder
                </Button>
                <input
                  ref={onFolderInput}
                  className="hidden"
                  type="file"
                  multiple
                  aria-hidden="true"
                  tabIndex={-1}
                  disabled={busy || Boolean(sessionId)}
                  onChange={(event) => void handleFolderChange(event)}
                />
              </div>
              {selection && (
                <div
                  className="mt-5 space-y-3 border-t border-rule pt-5"
                  aria-live="polite"
                >
                  {selection.ignoredCount > 0 && (
                    <p className="text-xs text-ink-muted">
                      {selection.ignoredCount} unsupported file(s) were not
                      added.
                    </p>
                  )}
                  {selection.errors.length > 0 && (
                    <div
                      className="rounded-lg border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
                      role="alert"
                    >
                      <ul className="list-disc space-y-1 pl-5">
                        {selection.errors.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}

          {selection && (
            <>
              {intakeStep === "media" ? (
                <PatientFolderMediaStep
                  eegCount={selectedEegBundles.length}
                  videoCount={selection.videos.length}
                  signalObfuscation={signalObfuscation}
                  signalDescription={PRIVACY_METHODS[1].description}
                  canContinue={canContinue}
                  onSignalObfuscationChange={setSignalObfuscation}
                  onContinue={() => {
                    setError(null);
                    setIntakeStep("details");
                  }}
                />
              ) : (
                <div
                  id="patient-details-step"
                  ref={detailsStepRef}
                  className="mt-6 max-w-3xl scroll-mt-24 space-y-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal"
                  tabIndex={-1}
                >
                  {reportMessage === "Reading the report on this device…" ? (
                    <LoadingOrb
                      className="px-1"
                      label={reportMessage}
                      state="searching"
                      size={20}
                    />
                  ) : reportMessage ? (
                    <p className="px-1 text-xs text-ink-muted" role="status">
                      {reportMessage}
                    </p>
                  ) : null}
                  <PatientDetailsEditor
                    fields={patientDetails}
                    truncated={reportTruncated}
                    readOnly={busy || Boolean(sessionId)}
                    onToggle={togglePatientDetail}
                    onChange={changePatientDetail}
                    onAddManualField={addManualPatientDetail}
                    onRemoveManualField={removeManualPatientDetail}
                  />
                </div>
              )}

              {error && (
                <div
                  className="mt-5 rounded-xl border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
                  role="alert"
                >
                  {error}
                </div>
              )}
              {intakeStep === "details" && (
                <>
                  <div className="mt-6 flex flex-col gap-3 border-t border-rule pt-5 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-xs leading-5 text-ink-muted">
                      {sessionId
                        ? videoAttentionCount > 0
                          ? `EEG session created. ${videoAttentionCount} video clips need attention.`
                          : "EEG session created. Continue to finish this patient review."
                        : `${selectedEegBundles.length} EEG recordings and ${selection.videos.length} video clips will be processed together.`}
                      {API_STUB_ENABLED && (
                        <span className="mt-1 block">
                          Connect the local API to create a review.
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      <Button
                        type="button"
                        size="lg"
                        variant="outline"
                        disabled={busy || Boolean(sessionId)}
                        onClick={() => {
                          setError(null);
                          setIntakeStep("media");
                        }}
                      >
                        Back to media and privacy
                      </Button>
                      {(!videoAttentionCount ||
                        retryableVideoIndexes.length > 0) && (
                        <Button
                          type="button"
                          size="lg"
                          onClick={() =>
                            void submitReview(
                              videoAttentionCount
                                ? retryableVideoIndexes
                                : undefined,
                            )
                          }
                          disabled={!canSubmit}
                        >
                          {!busy ? (
                            <Icon name="arrow" className="size-4" />
                          ) : null}
                          {busy
                            ? "Processing…"
                            : videoAttentionCount
                              ? "Retry eligible video uploads"
                              : sessionId
                                ? "Continue review"
                                : "Create patient review"}
                        </Button>
                      )}
                      {!busy &&
                        sessionId &&
                        caseId &&
                        videoAttentionCount > 0 && (
                          <Button
                            type="button"
                            size="lg"
                            variant="outline"
                            onClick={() =>
                              router.push(
                                `/cases/${encodeURIComponent(caseId)}?video_rejected_count=${videoRejectedCount}&video_unconfirmed_count=${videoUnconfirmedCount}`,
                              )
                            }
                          >
                            Continue to case with video warning
                          </Button>
                        )}
                    </div>
                  </div>
                  {busy && (
                    <div className="mt-4 space-y-3 border-t border-rule pt-4">
                      <LoadingOrb label={step} state="working" size={32} />
                      <Progress
                        value={progress}
                        className="h-1.5"
                        aria-label="Creating patient review"
                      />
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="max-w-xl text-xs leading-5 text-ink-muted">
                          Cancel stops uploads and status checks on this device.
                          A job already accepted by the service may continue.
                        </p>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() =>
                            workflowAbortController.current?.abort()
                          }
                        >
                          Cancel intake
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </motion.main>
      </div>
    </MotionConfig>
  );
}
