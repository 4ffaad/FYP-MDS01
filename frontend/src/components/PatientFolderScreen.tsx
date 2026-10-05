"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { MotionConfig, motion } from "motion/react";
import {
  ApiError,
  API_STUB_ENABLED,
  deleteUploadDraft,
  finalizeUploadDraft,
  getSession,
  pollRetryDelay,
  PRIVACY_METHODS,
  saveExtractedPatientProfile,
  stageUpload,
  shouldRetryRequest,
} from "@/lib/api";
import type { Session } from "@/lib/types";

import {
  buildEegArchive,
  classifyPatientFolder,
  type PatientFolderSelection,
} from "@/lib/patient-folder";
import { Icon } from "./Icon";

import { type PatientDetailDraft } from "./PatientDetailsEditor";
import { PatientFolderMediaStep } from "./PatientFolderMediaStep";
import {
  PatientProcessingProgress,
  type VideoPipelineProgressEntry,
} from "./PatientProcessingProgress";
import { Button } from "@/components/ui/button";
import { ModalityWorkspaceTabs } from "./ModalityWorkspaceTabs";
import {
  getDetection,
  finalizeVideoSyncGroup,
  uploadDetection,
  videoJobFailureMessage,
} from "@/lib/video-detection";

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

function videoSourceDirectory(file: File): string | null {
  const relativePath = file.webkitRelativePath.replaceAll("\\", "/");
  const separator = relativePath.lastIndexOf("/");
  if (separator < 0) return null;
  return relativePath.slice(0, separator).toLocaleLowerCase("en-US");
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
  pollIntervalMs = 1500,
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
          `Could not confirm the video job status after ${MAX_JOB_STATUS_RETRIES} retries. Check the patient review before retrying.`,
        );
      }
      await waitForSignal(pollRetryDelay(retryAttempt), signal);
      continue;
    }
    await waitForSignal(pollIntervalMs, signal);
  }
}

function jobStatusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "Pending upload";
    case "queued":
      return "Queued by service";
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
        "The video job was accepted, but its status could not be confirmed. Check the patient review before retrying.",
      retryable: false,
      disposition: "status-unconfirmed",
    };
  }
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return {
          message:
            "Your sign-in expired. Sign in again before retrying; this clip was not accepted.",
          retryable: false,
          disposition: "not-accepted",
        };
      case 403:
        return {
          message:
            "The signed-in account cannot access this patient case. Reopen the patient review; no video result was produced.",
          retryable: false,
          disposition: "not-accepted",
        };
      case 409:
        return {
          message: "The patient review changed. This clip was not accepted.",
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
      case 429:
        return {
          message:
            "The video queue is busy. This clip was not queued; wait for the active video job before retrying.",
          retryable: true,
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
      "The upload outcome could not be confirmed. Check the patient review before retrying to avoid duplicate work.",
    retryable: false,
    disposition: "status-unconfirmed",
  };
}

/** One-folder intake that keeps EEG and video policy visible side by side. */
export function PatientFolderScreen({
  mode = "combined",
}: {
  mode?: "combined" | "eeg-only";
}) {
  const eegOnly = mode === "eeg-only";
  const folderInput = useRef<HTMLInputElement>(null);
  const singleEegInput = useRef<HTMLInputElement>(null);
  const selectionGeneration = useRef(0);
  const videoSyncGroups = useRef(new Map<string, string>());
  const reportAbortController = useRef<AbortController | null>(null);
  const workflowAbortController = useRef<AbortController | null>(null);
  const videoProgressRef = useRef<VideoPipelineProgressEntry[]>([]);
  const activeWorkflowRef = useRef<{
    sessionId: string | null;
    caseId: string | null;
  }>({ sessionId: null, caseId: null });
  const videoIssuesRef = useRef<Record<number, VideoUploadIssue>>({});
  const mounted = useRef(false);
  const [selection, setSelection] = useState<PatientFolderSelection | null>(
    null,
  );
  const [intakeStep, setIntakeStep] = useState<"media" | "processing">("media");
  const [patientDetails, setPatientDetails] = useState<PatientDetailDraft[]>(
    [],
  );
  const [reportTruncated, setReportTruncated] = useState(false);
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const [reportReading, setReportReading] = useState(false);
  const [signalObfuscation, setSignalObfuscation] = useState(false);
  const [videoBlurStrengthPercent, setVideoBlurStrengthPercent] = useState(100);
  const [videoDetectionErrors, setVideoDetectionErrors] = useState<
    Record<number, VideoUploadIssue>
  >({});
  const [videoDetectionJobIds, setVideoDetectionJobIds] = useState<
    Record<number, string>
  >({});
  const [videoProgress, setVideoProgress] = useState<
    VideoPipelineProgressEntry[]
  >([]);
  const [eegSession, setEegSession] = useState<Session | null>(null);
  const [processingFinished, setProcessingFinished] = useState(false);

  const [step, setStep] = useState(
    eegOnly ? "Select an EEG recording" : "Select one patient folder",
  );
  const [eegUploadPercent, setEegUploadPercent] = useState<number | null>(null);
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
    if (intakeStep === "processing") {
      const heading = document.getElementById("patient-processing-heading");
      if (!heading) return;
      heading.focus({ preventScroll: true });
      heading.scrollIntoView({ block: "start" });
    }
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
    videoSyncGroups.current.clear();
    event.target.value = "";
    const nextSelection = classifyPatientFolder(files, {
      requireReport: !eegOnly,
      includeVideos: !eegOnly,
    });
    setSelection(nextSelection);
    setVideoBlurStrengthPercent(100);
    setIntakeStep("media");
    setDraftId(null);
    setPatientDetails([]);
    setReportTruncated(false);
    setReportMessage(null);
    setReportReading(false);
    setVideoDetectionErrors({});
    videoIssuesRef.current = {};
    setVideoDetectionJobIds({});
    setVideoProgress([]);
    videoProgressRef.current = [];
    setEegSession(null);
    setProcessingFinished(false);
    setSessionId(null);
    setCaseId(null);
    setProfileSaved(false);
    activeWorkflowRef.current = { sessionId: null, caseId: null };

    setEegUploadPercent(null);
    setError(null);

    if (!nextSelection.report) return;
    setReportReading(true);
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
        setReportReading(false);
      }
    }
  }

  async function submitReview(retryVideoIndexes?: number[]) {
    const selectedEegBundles = selection?.eegCandidates ?? [];
    const selectedDetails = patientDetails
      .filter((detail) => detail.label.trim() && detail.value.trim())
      .map(({ label, value }) => ({
        label: label.trim(),
        value: value.trim(),
      }));
    if (
      !selection ||
      selection.errors.length > 0 ||
      selectedEegBundles.length === 0
    ) {
      setError(
        eegOnly
          ? "Select one or more supported EEG recordings."
          : "Select one or more EEG recordings and one report folder.",
      );
      return;
    }

    if (reportReading) {
      setError("Wait for local report extraction to finish before processing.");
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
    setIntakeStep("processing");
    setProcessingFinished(false);
    const initialVideoProgress = retryVideoIndexes
      ? videoProgress.map((item) =>
          retryVideoIndexes.includes(item.index)
            ? {
                ...item,
                status: "pending" as const,
                uploadPercent: 0,
                stage: null,
                error: null,
              }
            : item,
        )
      : selection.videos.map((_, index) => {
          const existing = videoProgress.find((item) => item.index === index);
          if (videoDetectionErrors[index] && !videoDetectionJobIds[index]) {
            return (
              existing ?? {
                index,
                status:
                  videoDetectionErrors[index].disposition ===
                  "status-unconfirmed"
                    ? ("unconfirmed" as const)
                    : ("not-submitted" as const),
                uploadPercent: 0,
                stage: null,
                error: videoDetectionErrors[index].message,
              }
            );
          }
          return {
            index,
            status: "pending" as const,
            uploadPercent: 0,
            stage: null,
            error: null,
          };
        });
    videoProgressRef.current = initialVideoProgress;
    setVideoProgress(initialVideoProgress);
    const updateVideoProgress = (
      index: number,
      update: Partial<VideoPipelineProgressEntry>,
    ) => {
      videoProgressRef.current = videoProgressRef.current.map((item) =>
        item.index === index ? { ...item, ...update } : item,
      );
      if (mounted.current) setVideoProgress(videoProgressRef.current);
    };
    let pendingDraftId = draftId;
    activeWorkflowRef.current = { sessionId, caseId };
    let videoIds = videoDetectionJobIds;
    videoIssuesRef.current = { ...videoDetectionErrors };
    try {
      if (!activeWorkflowRef.current.sessionId) {
        if (!pendingDraftId) {
          setStep(`Preparing ${selectedEegBundles.length} EEG recordings`);
          const archive = await buildEegArchive(selectedEegBundles);
          throwIfAborted(signal);
          setStep("Encrypting the EEG upload");
          const draft = await stageUpload(
            archive,
            (value) => {
              if (mounted.current && !signal.aborted)
                setEegUploadPercent(value);
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
        activeWorkflowRef.current = {
          sessionId: finalized.sessionId,
          caseId: finalized.caseId,
        };
        if (!activeWorkflowRef.current.caseId)
          throw new Error(
            "The backend did not return an opaque case reference.",
          );
        setSessionId(finalized.sessionId);
        setCaseId(finalized.caseId);
        setDraftId(null);
        pendingDraftId = null;
      }

      const activeSessionId = activeWorkflowRef.current.sessionId;
      const activeCaseId = activeWorkflowRef.current.caseId;
      if (!activeSessionId || !activeCaseId)
        throw new Error(
          "The EEG session or patient case reference is unavailable.",
        );
      if (!profileSaved) {
        setStep("Saving all extracted patient details");
        if (selectedDetails.length > 0) {
          await saveExtractedPatientProfile(
            activeCaseId,
            selectedDetails,
            signal,
          );
        }
        throwIfAborted(signal);
        setProfileSaved(true);
      }

      if (!activeSessionId)
        throw new Error("The EEG session reference is unavailable.");
      setStep("EEG and video processing are running independently");
      const eegCompletion = waitForJob(
        () => getSession(activeSessionId!, signal),
        ["completed", "completed_with_errors", "failed"],
        (currentSession) => {
          if (mounted.current && !signal.aborted) {
            setEegSession(currentSession);
            const { completedRecordings, failedRecordings, totalRecordings } =
              currentSession.progress;
            setStep(
              `EEG processing: ${completedRecordings} of ${totalRecordings} recordings complete${failedRecordings ? `; ${failedRecordings} failed` : ""}`,
            );
          }
        },
        signal,
      ).then(
        (completedSession) => {
          setEegSession(completedSession);
          return { session: completedSession, error: null };
        },
        (eegError: unknown) => ({ session: null, error: eegError }),
      );

      if (selection.videos.length > 0) {
        const indexes =
          retryVideoIndexes ??
          selection.videos
            .map((_, index) => index)
            .filter(
              (index) =>
                Boolean(videoIds[index]) || !videoIssuesRef.current[index],
            );
        const acceptedJobs: Array<{ index: number; jobId: string }> = [];
        const canReadNicoletSync = selection.eegCandidates.some(
          (bundle) => bundle.format === "nicolet-e",
        );
        const syncGroupByIndex = new Map<number, string>();
        const syncGroupIndexes = new Map<string, number[]>();
        const syncGroupNames = new Map<string, string[]>();
        if (canReadNicoletSync) {
          for (const [index, videoFile] of selection.videos.entries()) {
            const sourceDirectory = videoSourceDirectory(videoFile);
            if (sourceDirectory === null) continue;
            let groupId = videoSyncGroups.current.get(sourceDirectory);
            if (!groupId) {
              groupId = crypto.randomUUID();
              videoSyncGroups.current.set(sourceDirectory, groupId);
            }
            syncGroupByIndex.set(index, groupId);
            syncGroupIndexes.set(groupId, [
              ...(syncGroupIndexes.get(groupId) ?? []),
              index,
            ]);
            syncGroupNames.set(groupId, [
              ...(syncGroupNames.get(groupId) ?? []),
              videoFile.name,
            ]);
          }
        }
        let syncResolutionFailed = false;
        const trackAcceptedJob = async ({
          index,
          jobId,
        }: {
          index: number;
          jobId: string;
        }) => {
          try {
            await waitForJob(
              () =>
                getDetection(jobId, signal).then((response) => response.job),
              ["ready", "failed", "expired"],
              (job) => {
                updateVideoProgress(index, {
                  status:
                    job.status === "ready"
                      ? "complete"
                      : job.status === "expired"
                        ? "expired"
                        : job.status === "failed"
                          ? "failed"
                          : job.status === "queued"
                            ? "queued"
                            : "processing",
                  stage: job.current_stage,
                  error:
                    job.status === "failed" || job.status === "expired"
                      ? videoJobFailureMessage(job.status, job.error)
                      : null,
                });
              },
              signal,
              5000,
            );
            return true;
          } catch (videoError) {
            if (signal.aborted || isAbortError(videoError)) throw videoError;
            if (!mounted.current) return false;
            videoIssuesRef.current[index] = videoUploadIssue(videoError, true);
            updateVideoProgress(index, {
              status: "unconfirmed",
              error: videoIssuesRef.current[index].message,
            });
            setVideoDetectionErrors({ ...videoIssuesRef.current });
            return false;
          }
        };
        let stopSubmittingVideos = false;
        for (const [position, index] of indexes.entries()) {
          const videoFile = selection.videos[index];
          const sourceGroupId = syncGroupByIndex.get(index);
          let jobId = videoIds[index];
          updateVideoProgress(index, {
            status: jobId ? "processing" : "uploading",
            uploadPercent: 0,
            error: null,
          });
          delete videoIssuesRef.current[index];
          setVideoDetectionErrors({ ...videoIssuesRef.current });
          try {
            if (!jobId) {
              setStep(
                `Uploading video analysis ${position + 1} of ${indexes.length}`,
              );
              while (!jobId) {
                try {
                  const { job } = await uploadDetection(
                    videoFile,
                    (value) => {
                      if (mounted.current && !signal.aborted) {
                        updateVideoProgress(index, {
                          status: "uploading",
                          uploadPercent: value,
                        });
                      }
                    },
                    activeCaseId!,
                    signal,
                    videoBlurStrengthPercent,
                    sourceGroupId
                      ? { sourceName: videoFile.name, groupId: sourceGroupId }
                      : undefined,
                  );
                  jobId = job.job_id;
                  videoIds = { ...videoIds, [index]: jobId };
                  setVideoDetectionJobIds(videoIds);
                  updateVideoProgress(index, {
                    status: job.status === "queued" ? "queued" : "processing",
                    stage: job.current_stage,
                    error: null,
                  });
                  throwIfAborted(signal);
                } catch (uploadError) {
                  if (
                    !(uploadError instanceof ApiError) ||
                    uploadError.status !== 429 ||
                    acceptedJobs.length === 0
                  ) {
                    throw uploadError;
                  }
                  const activeJob = acceptedJobs.shift()!;
                  setStep(
                    `Waiting for video ${activeJob.index + 1} to finish before submitting the next clip`,
                  );
                  if (!(await trackAcceptedJob(activeJob))) {
                    videoIssuesRef.current[index] = {
                      message:
                        "This clip was not submitted because an earlier video job's status could not be confirmed.",
                      retryable: false,
                      disposition: "not-accepted",
                    };
                    updateVideoProgress(index, {
                      status: "not-submitted",
                      error: videoIssuesRef.current[index].message,
                    });
                    for (const remainingIndex of indexes.slice(position + 1)) {
                      videoIssuesRef.current[remainingIndex] = {
                        message:
                          "This clip was not submitted because an earlier video job's status could not be confirmed.",
                        retryable: false,
                        disposition: "not-accepted",
                      };
                      updateVideoProgress(remainingIndex, {
                        status: "not-submitted",
                        error: videoIssuesRef.current[remainingIndex].message,
                      });
                    }
                    setVideoDetectionErrors({ ...videoIssuesRef.current });
                    stopSubmittingVideos = true;
                    break;
                  }
                }
              }
              if (stopSubmittingVideos) break;
            }
            acceptedJobs.push({ index, jobId: jobId! });
          } catch (videoError) {
            if (signal.aborted || isAbortError(videoError)) {
              if (mounted.current) {
                videoIssuesRef.current[index] = videoUploadIssue(
                  videoError,
                  Boolean(jobId),
                );
                updateVideoProgress(index, {
                  status: "unconfirmed",
                  error: videoIssuesRef.current[index].message,
                });
                setVideoDetectionErrors({ ...videoIssuesRef.current });
                setStep(
                  "Video status is unconfirmed. Check the patient review before retrying.",
                );
              }
              throw videoError;
            }
            if (!mounted.current) throw videoError;
            videoIssuesRef.current[index] = videoUploadIssue(
              videoError,
              Boolean(jobId),
            );
            updateVideoProgress(index, {
              status:
                videoIssuesRef.current[index].disposition ===
                "status-unconfirmed"
                  ? "unconfirmed"
                  : "not-submitted",
              error: videoIssuesRef.current[index].message,
            });
            setVideoDetectionErrors({ ...videoIssuesRef.current });
            if (
              !(videoError instanceof ApiError) ||
              ![413, 415, 422].includes(videoError.status)
            ) {
              const blockedClipIssue = videoIssuesRef.current[index];
              const retryBlockedClips =
                blockedClipIssue.retryable &&
                blockedClipIssue.disposition === "not-accepted";
              for (const remainingIndex of indexes.slice(position + 1)) {
                videoIssuesRef.current[remainingIndex] = {
                  message: retryBlockedClips
                    ? "This clip was not submitted. It will be included in the next retry."
                    : "This clip was not submitted because the previous video job could not be confirmed.",
                  retryable: retryBlockedClips,
                  disposition: "not-accepted",
                };
                updateVideoProgress(remainingIndex, {
                  status: "not-submitted",
                  error: videoIssuesRef.current[remainingIndex].message,
                });
              }
              setVideoDetectionErrors({ ...videoIssuesRef.current });
              break;
            }
          }
        }
        for (const [groupId, groupIndexes] of syncGroupIndexes) {
          if (!groupIndexes.every((index) => Boolean(videoIds[index])))
            continue;
          try {
            setStep("Checking EEG and video timestamps");
            await finalizeVideoSyncGroup(
              activeCaseId!,
              groupId,
              syncGroupNames.get(groupId) ?? [],
              signal,
            );
          } catch (syncError) {
            if (signal.aborted || isAbortError(syncError)) throw syncError;
            syncResolutionFailed = true;
          }
        }
        if (stopSubmittingVideos) {
          setStep(
            "Video submission stopped because an accepted job needs status review.",
          );
        }
        if (acceptedJobs.length > 0) {
          await Promise.all(acceptedJobs.map(trackAcceptedJob));
          throwIfAborted(signal);
        }
        if (Object.keys(videoIssuesRef.current).length > 0) {
          const failedVideoCount = Object.keys(videoIssuesRef.current).length;
          const label =
            failedVideoCount === 1 ? "video clip needs" : "video clips need";
          setError(`${failedVideoCount} ${label} attention.`);
        }
        if (syncResolutionFailed) {
          setError(
            "The uploads are saved, but EEG and video timestamps could not be verified. They remain separate until synchronization is retried.",
          );
        }
      }

      const eegOutcome = await eegCompletion;
      if (eegOutcome.error) throw eegOutcome.error;

      if (!mounted.current || signal.aborted) return;
      const videoOutcomesConfirmed = videoProgressRef.current.every((item) =>
        ["complete", "failed", "expired", "not-submitted"].includes(
          item.status,
        ),
      );
      const hasUnconfirmedOutcome = Object.values(videoIssuesRef.current).some(
        (issue) => issue.disposition === "status-unconfirmed",
      );
      const hasRetryableOutcome = Object.values(videoIssuesRef.current).some(
        (issue) => issue.retryable,
      );
      setProcessingFinished(videoOutcomesConfirmed);
      if (!videoOutcomesConfirmed) {
        setStep(
          hasUnconfirmedOutcome
            ? "A video status is unconfirmed. Check the patient review before retrying."
            : hasRetryableOutcome
              ? "Some video clips were not submitted. Retry eligible uploads to continue."
              : "Video processing remains pending. Recheck processing status to continue.",
        );
      }
    } catch (submitError) {
      if (!mounted.current) return;
      if (pendingDraftId && !activeWorkflowRef.current.sessionId)
        setDraftId(pendingDraftId);
      if (signal.aborted || isAbortError(submitError)) {
        setStep("Intake canceled; accepted work may continue.");
        setError(
          "Intake canceled. Upload and status checks stopped on this device. Work already accepted by the service may continue; check the patient review later.",
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
      }
    }
  }

  const selectedEegBundles = selection?.eegCandidates ?? [];
  const canContinue = Boolean(
    selection &&
      selection.errors.length === 0 &&
      selectedEegBundles.length > 0 &&
      !reportReading &&
      !API_STUB_ENABLED &&
      !sessionId &&
      !busy,
  );
  const videoAttentionCount = Object.keys(videoDetectionErrors).length;
  const retryableVideoIndexes = Object.entries(videoDetectionErrors)
    .filter(([, issue]) => issue.retryable)
    .map(([index]) => Number(index));
  const hasUnconfirmedVideoOutcome = Object.values(videoDetectionErrors).some(
    (issue) => issue.disposition === "status-unconfirmed",
  );
  const hasKnownVideoJobs = Object.keys(videoDetectionJobIds).length > 0;
  const hasSafeQueuedVideos = videoProgress.some(
    (item) =>
      ["pending", "queued"].includes(item.status) &&
      !videoDetectionErrors[item.index],
  );
  const hasPendingEegSession =
    Boolean(sessionId) &&
    (!eegSession ||
      !["completed", "completed_with_errors", "failed"].includes(
        eegSession.status,
      ));
  const canRecheckProcessing =
    hasKnownVideoJobs ||
    hasSafeQueuedVideos ||
    hasPendingEegSession ||
    (!sessionId && !hasUnconfirmedVideoOutcome);

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
            <p className="eyebrow">
              {eegOnly ? "New EEG analysis" : "New patient review"}
            </p>
            <h1 className="mt-3 text-[clamp(2rem,5vw,2.8rem)] font-semibold leading-[1.06] tracking-[-0.045em] text-ink">
              {eegOnly ? "Add EEG recordings" : "Add a patient recording"}
            </h1>
            <p className="mt-4 max-w-2xl text-[0.98rem] leading-7 text-ink-muted">
              {eegOnly
                ? "Analyze EEG recordings on their own. A report is optional; video files in the selected folder are ignored."
                : "Keep one patient&apos;s report, multiple EEG recordings, and video clips together in one review."}
            </p>
            {eegOnly && (
              <ModalityWorkspaceTabs modality="eeg" active="upload" />
            )}
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
                01&nbsp; Media &amp; privacy
              </li>
              <li
                className={
                  intakeStep === "processing"
                    ? "rounded-full bg-teal-soft px-3 py-1 text-teal-dark"
                    : "px-3 py-1 text-ink-faint"
                }
                aria-current={intakeStep === "processing" ? "step" : undefined}
              >
                02&nbsp; Processing
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
                  <p className="eyebrow">
                    {eegOnly ? "EEG recording" : "Patient recording"}
                  </p>
                  <h2 id="folder-heading" className="mt-2 text-lg font-bold">
                    {eegOnly
                      ? "Add an EEG recording"
                      : "Choose one patient folder"}
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
                    {eegOnly
                      ? "Choose one .e or .edf recording, or a folder for multiple recordings or a .data/.head pair. A report is optional."
                      : "One folder creates one case. Include the report, as many EEG recordings as needed, and the related video clips."}
                  </p>
                </div>
                {eegOnly ? (
                  <div className="flex flex-col gap-2 sm:items-end">
                    <Button
                      type="button"
                      size="lg"
                      onClick={() => singleEegInput.current?.click()}
                      disabled={busy || Boolean(sessionId)}
                    >
                      <Icon name="file" className="size-4" />
                      Choose one EEG file
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => folderInput.current?.click()}
                      disabled={busy || Boolean(sessionId)}
                    >
                      Choose EEG folder
                    </Button>
                  </div>
                ) : (
                  <Button
                    type="button"
                    size="lg"
                    onClick={() => folderInput.current?.click()}
                    disabled={busy || Boolean(sessionId)}
                  >
                    <Icon name="file" className="size-4" />
                    Choose patient folder
                  </Button>
                )}
                {eegOnly && (
                  <input
                    ref={singleEegInput}
                    className="hidden"
                    type="file"
                    accept=".e,.edf,.edf+"
                    aria-label="Choose one EEG recording"
                    disabled={busy || Boolean(sessionId)}
                    onChange={(event) => void handleFolderChange(event)}
                  />
                )}
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

          {selection &&
            (intakeStep === "media" ? (
              <>
                <PatientFolderMediaStep
                  eegCount={selectedEegBundles.length}
                  videoCount={selection.videos.length}
                  showVideoInput={!eegOnly}
                  showPatientDetails={Boolean(selection.report)}
                  signalObfuscation={signalObfuscation}
                  videoBlurStrengthPercent={videoBlurStrengthPercent}
                  signalDescription={PRIVACY_METHODS[1].description}
                  patientDetails={patientDetails}
                  reportTruncated={reportTruncated}
                  reportMessage={reportMessage}
                  reportReading={reportReading}
                  canContinue={canContinue}
                  onSignalObfuscationChange={setSignalObfuscation}
                  onVideoBlurStrengthChange={setVideoBlurStrengthPercent}
                  onContinue={() => void submitReview()}
                />
                {API_STUB_ENABLED && (
                  <p className="mt-3 text-xs text-ink-muted" role="status">
                    Connect the local API to create a patient review.
                  </p>
                )}
              </>
            ) : (
              <>
                <PatientProcessingProgress
                  session={eegSession}
                  eegCount={selectedEegBundles.length}
                  uploadPercent={eegUploadPercent}
                  step={step}
                  videos={videoProgress}
                  videoCount={selection.videos.length}
                  busy={busy}
                  finished={processingFinished}
                  videoEnabled={!eegOnly}
                  caseId={caseId}
                  error={error}
                />
                {busy ? (
                  <div className="mt-4 flex justify-end border-t border-rule pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => workflowAbortController.current?.abort()}
                    >
                      Cancel intake
                    </Button>
                  </div>
                ) : null}
                {!busy &&
                (error || videoAttentionCount > 0) &&
                (!processingFinished || retryableVideoIndexes.length > 0) &&
                (canRecheckProcessing || retryableVideoIndexes.length > 0) ? (
                  <div className="mt-4 flex justify-end border-t border-rule pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() =>
                        void submitReview(
                          retryableVideoIndexes.length > 0
                            ? retryableVideoIndexes
                            : undefined,
                        )
                      }
                    >
                      {retryableVideoIndexes.length > 0
                        ? "Retry eligible video uploads"
                        : hasUnconfirmedVideoOutcome
                          ? "Continue safe processing"
                          : "Recheck processing status"}
                    </Button>
                  </div>
                ) : null}
              </>
            ))}
        </motion.main>
      </div>
    </MotionConfig>
  );
}
