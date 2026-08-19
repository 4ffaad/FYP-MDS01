import type {
  AnalysisResult,
  ApiErrorPayload,
  DisplayStatus,
  Recording,
  RecordingStatus,
  ReferenceAnnotation,
  SignalPreview,
  Session,
  SessionProgress,
  SessionSummary,
  SessionStatus,
  PrivacyMethod,
} from "./types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const USE_STUB = process.env.NEXT_PUBLIC_USE_API_STUB !== "false";
const SHOW_SIGNAL_PREVIEW = USE_STUB || process.env.NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW === "true";
const JOBS_KEY = "mds01.jobs.v1";

export const PRIVACY_METHODS: PrivacyMethod[] = [
  { id: "control", label: "Control", description: "Removes EDF metadata; detector and privacy evaluation use the same preprocessed windows." },
  { id: "cancellable-signal-projection", label: "Cancellable signal projection", description: "Uses a keyed, lossy EEG transformation for both detection and privacy evaluation; it is not an anonymity guarantee." },
];

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) { super(message); this.name = "ApiError"; this.status = status; }
}

function wait(milliseconds: number): Promise<void> { return new Promise((resolve) => window.setTimeout(resolve, milliseconds)); }

type StubJob = {
  jobId: string;
  recordingLabel: string;
  submittedAt: string;
  status: "queued" | "processing" | "complete" | "failed";
  privacyMethod: PrivacyMethod;
  errorMessage?: string;
};

function readStubJobs(): StubJob[] {
  if (typeof window === "undefined") return [];
  try { const raw = window.localStorage.getItem(JOBS_KEY); return raw ? (JSON.parse(raw) as StubJob[]) : []; } catch { return []; }
}

function writeStubJobs(jobs: StubJob[]): void { window.localStorage.setItem(JOBS_KEY, JSON.stringify(jobs)); }

function methodForId(methodId: string | undefined): PrivacyMethod {
  return PRIVACY_METHODS.find((item) => item.id === methodId) ?? { id: "server-configured", label: "Backend configuration", description: "Privacy configuration supplied by the analysis service." };
}

type BackendSession = {
  session_id: string;
  privacy_method: string;
  status: string;
  current_stage: string | null;
  created_at: string;
  completed_at: string | null;
  error_message?: string | null;
  progress: { total_recordings: number; finished_recordings: number; completed_recordings: number; failed_recordings: number; percent: number };
  summary: { dataset_seizure_recordings: number | null; model_alert_recordings: number };
  recordings: BackendRecording[];
};

type BackendRecording = {
  record_id: string;
  sequence_index: number;
  status: RecordingStatus;
  source_filename: string;
  duration_seconds: number | null;
  sampling_rate: number | null;
  channel_count: number | null;
  reference_annotation: {
    source: string;
    intervals: Array<{ start_seconds: number; end_seconds: number }>;
  } | null;
  error_message?: string | null;
  model_alert_window_count?: number;
  session_id?: string;
  session_created_at?: string;
  privacy_method?: string;
};

type BackendPredictionResponse = {
  model: { name: string; version: string } | null;
  summary?: { window_count: number; flagged_window_count: number; flagged_window_fraction: number; peak_window_score: number };
  predictions: Array<{ start_seconds: number; end_seconds: number; probability: number; seizure_detected: boolean }>;
};

type BackendSignalResponse = {
  sampling_rate: number;
  channel_labels: string[];
  start_seconds: number;
  duration_seconds: number;
  samples: number[][];
};

function referenceAnnotationFromBackend(annotation: BackendRecording["reference_annotation"]): ReferenceAnnotation | null {
  if (!annotation) return null;
  return {
    source: annotation.source,
    intervals: annotation.intervals.map((interval) => ({
      startSeconds: interval.start_seconds,
      endSeconds: interval.end_seconds,
    })),
  };
}

type BackendExplanationResponse = {
  explanations: Array<{ is_clinical: boolean; data: unknown }>;
};

function publicSessionStatus(status: string): SessionStatus {
  if (status === "completed" || status === "completed_with_errors") return status;
  if (status === "failed") return "failed";
  if (status === "queued") return "queued";
  return status as SessionStatus;
}

export function toDisplayStatus(status: string): DisplayStatus {
  if (status === "completed" || status === "inferred") return "complete";
  if (status === "completed_with_errors") return "partial";
  if (status === "failed") return "failed";
  if (status === "queued" || status === "uploaded") return "queued";
  return "processing";
}

function recordingFromBackend(recording: BackendRecording, session?: BackendSession): Recording {
  return {
    recordId: recording.record_id,
    sequenceIndex: recording.sequence_index,
    displayName: recording.source_filename,
    status: recording.status,
    durationSeconds: recording.duration_seconds,
    samplingRate: recording.sampling_rate,
    channelCount: recording.channel_count,
    referenceAnnotation: referenceAnnotationFromBackend(recording.reference_annotation),
    modelAlertWindowCount: recording.model_alert_window_count ?? 0,
    errorMessage: recording.error_message ?? undefined,
    sessionId: recording.session_id ?? session?.session_id,
    sessionCreatedAt: recording.session_created_at ?? session?.created_at,
    privacyMethod: recording.privacy_method ? methodForId(recording.privacy_method) : session ? methodForId(session.privacy_method) : undefined,
  };
}

function sessionFromBackend(session: BackendSession): Session {
  return {
    sessionId: session.session_id,
    privacyMethod: methodForId(session.privacy_method),
    status: publicSessionStatus(session.status),
    currentStage: session.current_stage,
    createdAt: session.created_at,
    completedAt: session.completed_at,
    errorMessage: session.error_message ?? undefined,
    recordings: session.recordings.map((recording) => recordingFromBackend(recording, session)),
    progress: progressFromBackend(session.progress),
    summary: summaryFromBackend(session.summary),
  };
}

function progressFromBackend(progress: BackendSession["progress"]): SessionProgress {
  return {
    totalRecordings: progress.total_recordings,
    finishedRecordings: progress.finished_recordings,
    completedRecordings: progress.completed_recordings,
    failedRecordings: progress.failed_recordings,
    percent: progress.percent,
  };
}

function summaryFromBackend(summary: BackendSession["summary"]): SessionSummary {
  return {
    datasetSeizureRecordings: summary.dataset_seizure_recordings,
    modelAlertRecordings: summary.model_alert_recordings,
  };
}

function stubSessionFromJob(job: StubJob): Session {
  const status: SessionStatus = job.status === "complete" ? "completed" : job.status === "failed" ? "failed" : job.status === "processing" ? "preprocessing" : "queued";
  return {
    sessionId: job.jobId,
    privacyMethod: job.privacyMethod,
    status,
    currentStage: status === "queued" || status === "completed" || status === "failed" ? null : "processing",
    createdAt: job.submittedAt,
    completedAt: status === "completed" ? job.submittedAt : null,
    errorMessage: job.errorMessage,
    recordings: [{
      recordId: job.jobId,
      sequenceIndex: 1,
      displayName: job.recordingLabel,
      status: status === "completed" ? "inferred" : status === "failed" ? "failed" : "uploaded",
      durationSeconds: null,
      samplingRate: null,
      channelCount: null,
      referenceAnnotation: null,
      modelAlertWindowCount: 0,
      errorMessage: job.errorMessage,
      sessionId: job.jobId,
      sessionCreatedAt: job.submittedAt,
      privacyMethod: job.privacyMethod,
    }],
    progress: {
      totalRecordings: 1,
      finishedRecordings: status === "completed" || status === "failed" ? 1 : 0,
      completedRecordings: status === "completed" ? 1 : 0,
      failedRecordings: status === "failed" ? 1 : 0,
      percent: status === "completed" || status === "failed" ? 100 : 0,
    },
    summary: { datasetSeizureRecordings: null, modelAlertRecordings: 0 },
  };
}

function advanceStubStatus(job: StubJob): StubJob {
  const elapsed = Date.now() - new Date(job.submittedAt).getTime();
  if (job.status === "failed") return job;
  if (elapsed > 7000) return { ...job, status: "complete" };
  if (elapsed > 1800) return { ...job, status: "processing" };
  return { ...job, status: "queued" };
}

function seededNumber(seed: string, offset: number): number {
  let value = 0;
  for (let index = 0; index < seed.length; index += 1) value = (value * 31 + seed.charCodeAt(index)) % 997;
  return ((value + offset * 37) % 100) / 100;
}

function createStubResult(job: StubJob): AnalysisResult {
  const predictionWindows = Array.from({ length: 15 }, (_, index) => {
    const probability = seededNumber(job.jobId, index + 80);
    return { startSeconds: index * 4, endSeconds: index * 4 + 4, probability, seizureDetected: probability >= 0.5 };
  });
  const strongest = predictionWindows.reduce((current, item) => item.probability > current.probability ? item : current);
  return {
    recordId: job.jobId,
    sessionId: job.jobId,
    recordingLabel: job.recordingLabel,
    submittedAt: job.submittedAt,
    prediction: strongest.seizureDetected ? "seizure" : "no-seizure",
    peakWindowScore: strongest.probability,
    windowCount: predictionWindows.length,
    flaggedWindowCount: predictionWindows.filter((item) => item.seizureDetected).length,
    flaggedWindowFraction: predictionWindows.filter((item) => item.seizureDetected).length / predictionWindows.length,
    privacyMethod: job.privacyMethod,
    recordingDurationSeconds: 60,
    predictionWindows,
    referenceAnnotation: null,
    signalPreview: createStubSignal(job.jobId, Math.max(0, strongest.startSeconds - 3)),
    explanationSummary: "The color band shows the deterministic development-stub score for each prediction window. It is not attention or a clinical explanation.",
    modelName: "development-stub",
    modelVersion: "stub-0.1.0",
    nonClinical: true,
    signalPreviewAvailable: true,
  };
}

export async function getSessions(signal?: AbortSignal): Promise<Session[]> {
  if (USE_STUB) {
    await wait(180);
    if (signal?.aborted) throw new DOMException("Request aborted.", "AbortError");
    const jobs = readStubJobs().map(advanceStubStatus);
    writeStubJobs(jobs);
    return jobs
      .sort((left, right) => right.submittedAt.localeCompare(left.submittedAt))
      .map(stubSessionFromJob);
  }
  const sessions = await getJson<BackendSession[]>("/api/sessions", signal);
  return sessions.map(sessionFromBackend);
}

export async function getSession(sessionId: string, signal?: AbortSignal): Promise<Session> {
  if (USE_STUB) {
    const session = (await getSessions(signal)).find((item) => item.sessionId === sessionId);
    if (!session) throw new ApiError("This session could not be found.", 404);
    return session;
  }
  return sessionFromBackend(await getJson<BackendSession>(`/api/sessions/${encodeURIComponent(sessionId)}`, signal));
}

export async function deleteSession(sessionId: string, signal?: AbortSignal): Promise<void> {
  if (USE_STUB) {
    await wait(80);
    if (signal?.aborted) throw new DOMException("Delete aborted.", "AbortError");
    writeStubJobs(readStubJobs().filter((job) => job.jobId !== sessionId));
    return;
  }
  await requestWithoutBody(`/api/sessions/${encodeURIComponent(sessionId)}`, "DELETE", signal);
}

export async function getRecording(recordId: string, signal?: AbortSignal): Promise<Recording> {
  if (USE_STUB) {
    const session = (await getSessions(signal)).find((item) => item.recordings.some((recording) => recording.recordId === recordId));
    const recording = session?.recordings.find((item) => item.recordId === recordId);
    if (!recording) throw new ApiError("This recording could not be found.", 404);
    return recording;
  }
  return recordingFromBackend(await getJson<BackendRecording>(`/api/recordings/${encodeURIComponent(recordId)}`, signal));
}

export async function submitAnalysis(file: File, privacyMethodId: string, onProgress: (progress: number) => void, signal?: AbortSignal): Promise<{ sessionId: string }> {
  if (USE_STUB) {
    for (const progress of [18, 42, 68, 100]) {
      await wait(160);
      if (signal?.aborted) throw new DOMException("Upload aborted.", "AbortError");
      onProgress(progress);
    }
    const method = PRIVACY_METHODS.find((item) => item.id === privacyMethodId) ?? PRIVACY_METHODS[0];
    const jobNumber = readStubJobs().length + 1;
    const job: StubJob = { jobId: `MDS-${Date.now().toString(36).toUpperCase()}`, recordingLabel: `Recording ${String(jobNumber).padStart(2, "0")}`, submittedAt: new Date().toISOString(), status: "queued", privacyMethod: method };
    writeStubJobs([job, ...readStubJobs()]);
    return { sessionId: job.jobId };
  }
  const formData = new FormData();
  formData.append("archive", file);
  formData.append("privacy_method", privacyMethodId);
  const response = await uploadJson<{ session_id: string }>("/api/sessions/upload", formData, onProgress, signal);
  return { sessionId: response.session_id };
}

export async function getResult(recordId: string, signal?: AbortSignal): Promise<AnalysisResult> {
  if (USE_STUB) {
    await wait(220);
    if (signal?.aborted) throw new DOMException("Request aborted.", "AbortError");
    const job = readStubJobs().map(advanceStubStatus).find((item) => item.jobId === recordId);
    if (!job) throw new ApiError("This analysis could not be found.", 404);
    if (job.status === "failed") throw new ApiError(job.errorMessage ?? "This recording failed during processing.", 422);
    return createStubResult(job);
  }
  const record = await getRecording(recordId, signal);
  if (record.status === "failed") throw new ApiError(record.errorMessage ?? "This recording failed during processing.", 422);
  const [predictionPayload, explanationPayload] = await Promise.all([
    getJson<BackendPredictionResponse>(`/api/recordings/${encodeURIComponent(record.recordId)}/prediction`, signal),
    getJson<BackendExplanationResponse>(`/api/recordings/${encodeURIComponent(record.recordId)}/explanation`, signal),
  ]);
  const predictions = predictionPayload.predictions;
  const predictionSummary = predictionPayload.summary ?? {
    window_count: predictions.length,
    flagged_window_count: predictions.filter((item) => item.seizure_detected).length,
    flagged_window_fraction: predictions.length ? predictions.filter((item) => item.seizure_detected).length / predictions.length : 0,
    peak_window_score: Math.max(...predictions.map((item) => item.probability), 0),
  };
  const strongest = predictions.reduce((current, item) => item.probability > current.probability ? item : current, predictions[0] ?? { probability: 0, seizure_detected: false, start_seconds: 0, end_seconds: 0 });
  const firstReference = record.referenceAnnotation?.intervals[0];
  const previewStart = Math.max(0, (firstReference?.startSeconds ?? strongest.start_seconds) - 3);
  const signalPreview = await getSignalPreview(record.recordId, previewStart, signal);
  return {
    recordId,
    sessionId: record.sessionId ?? "unknown-session",
    recordingLabel: record.displayName,
    submittedAt: record.sessionCreatedAt ?? new Date().toISOString(),
    prediction: strongest.seizure_detected ? "seizure" : "no-seizure",
    peakWindowScore: predictionSummary.peak_window_score,
    windowCount: predictionSummary.window_count,
    flaggedWindowCount: predictionSummary.flagged_window_count,
    flaggedWindowFraction: predictionSummary.flagged_window_fraction,
    privacyMethod: record.privacyMethod ?? methodForId(undefined),
    recordingDurationSeconds: record.durationSeconds ?? predictions.at(-1)?.end_seconds ?? 0,
    predictionWindows: predictions.map((prediction) => ({
      startSeconds: prediction.start_seconds,
      endSeconds: prediction.end_seconds,
      probability: prediction.probability,
      seizureDetected: prediction.seizure_detected,
    })),
    referenceAnnotation: record.referenceAnnotation,
    signalPreview,
    explanationSummary: explanationPayload.explanations.length > 0 ? "The color band shows the development-stub score for each prediction window. It is not attention or a clinical explanation." : "No development explanation artifact was returned for this recording.",
    modelName: predictionPayload.model?.name ?? "backend-model",
    modelVersion: predictionPayload.model?.version ?? "unknown",
    nonClinical: explanationPayload.explanations.every((item) => !item.is_clinical),
    signalPreviewAvailable: signalPreview !== null,
  };
}

export async function getSignalPreview(recordId: string, startSeconds: number, signal?: AbortSignal): Promise<SignalPreview | null> {
  if (!SHOW_SIGNAL_PREVIEW) return null;
  if (USE_STUB) {
    await wait(80);
    if (signal?.aborted) throw new DOMException("Request aborted.", "AbortError");
    return createStubSignal(recordId, startSeconds);
  }
  try {
    const payload = await getJson<BackendSignalResponse>(`/api/recordings/${encodeURIComponent(recordId)}/signal?start_seconds=${startSeconds}&duration_seconds=10&max_points=600`, signal);
    return {
      channelLabels: payload.channel_labels,
      samples: payload.samples,
      samplingRate: payload.sampling_rate,
      startSeconds: payload.start_seconds,
      durationSeconds: payload.duration_seconds,
    };
  } catch (error) {
    if (error instanceof ApiError && [404, 409, 422].includes(error.status)) return null;
    throw error;
  }
}

function createStubSignal(seed: string, startSeconds: number): SignalPreview {
  const channelLabels = ["FP1-F7", "F7-T7", "T7-P7", "P7-O1", "FP1-F3", "F3-C3", "C3-P3", "P3-O1", "FP2-F4", "F4-C4", "C4-P4", "P4-O2", "FP2-F8", "F8-T8", "T8-P8", "P8-O2", "FZ-CZ", "CZ-PZ"];
  const pointCount = 360;
  return {
    channelLabels,
    samples: channelLabels.map((_, channel) => Array.from({ length: pointCount }, (_, index) => {
      const seconds = startSeconds + index / 36;
      return Math.sin(seconds * (2.4 + channel * 0.08)) * (0.45 + channel * 0.015) + (seededNumber(seed, index + channel * 17) - 0.5) * 0.08;
    })),
    samplingRate: 256,
    startSeconds,
    durationSeconds: 10,
  };
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal, headers: { Accept: "application/json" }, credentials: "omit", cache: "no-store" });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

async function requestWithoutBody(path: string, method: string, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    signal,
    headers: { Accept: "application/json" },
    credentials: "omit",
  });
  if (!response.ok) throw await readError(response);
}

async function readError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}.`;
  try { const payload = (await response.json()) as ApiErrorPayload; if (payload.detail) message = payload.detail; } catch { /* Keep the status message. */ }
  return new ApiError(message, response.status);
}

function uploadJson<T>(path: string, body: FormData, onProgress: (progress: number) => void, signal?: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}${path}`);
    request.responseType = "json";
    request.setRequestHeader("Accept", "application/json");
    request.upload.addEventListener("progress", (event) => { if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100)); });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) return resolve(request.response as T);
      const detail = (request.response as ApiErrorPayload | null)?.detail;
      reject(new ApiError(detail ?? `Upload failed with status ${request.status}.`, request.status));
    });
    request.addEventListener("error", () => reject(new ApiError("The analysis service could not be reached.")));
    request.addEventListener("abort", () => reject(new DOMException("Upload aborted.", "AbortError")));
    if (signal) { if (signal.aborted) request.abort(); signal.addEventListener("abort", () => request.abort(), { once: true }); }
    request.send(body);
  });
}
