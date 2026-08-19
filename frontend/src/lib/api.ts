import type { AnalysisResult, ApiErrorPayload, Job, JobStatus, PrivacyMethod } from "./types";

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

function readStubJobs(): Job[] {
  if (typeof window === "undefined") return [];
  try { const raw = window.localStorage.getItem(JOBS_KEY); return raw ? (JSON.parse(raw) as Job[]) : []; } catch { return []; }
}

function writeStubJobs(jobs: Job[]): void { window.localStorage.setItem(JOBS_KEY, JSON.stringify(jobs)); }

function methodForId(methodId: string | undefined): PrivacyMethod {
  return PRIVACY_METHODS.find((item) => item.id === methodId) ?? { id: "server-configured", label: "Backend configuration", description: "Privacy configuration supplied by the analysis service." };
}

type BackendSession = {
  session_id: string;
  privacy_method: string;
  status: string;
  created_at: string;
  error_message?: string | null;
  recordings: BackendRecording[];
};

type BackendRecording = {
  record_id: string;
  sequence_index: number;
};

type BackendPredictionResponse = {
  model: { name: string; version: string } | null;
  predictions: Array<{ start_seconds: number; end_seconds: number; probability: number; seizure_detected: boolean }>;
};

type BackendSignalResponse = {
  samples: number[][];
};

type BackendExplanationResponse = {
  explanations: Array<{ is_clinical: boolean; data: unknown }>;
};

function publicJobStatus(status: string): JobStatus {
  if (status === "queued") return "queued";
  if (status === "completed" || status === "completed_with_errors") return "complete";
  if (status === "failed") return "failed";
  return "processing";
}

function advanceStubStatus(job: Job): Job {
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

function createStubResult(job: Job): AnalysisResult {
  const pointCount = 180;
  const timeSeries = Array.from({ length: pointCount }, (_, index) => {
    const base = Math.sin(index / 8) * 0.28 + Math.sin(index / 21) * 0.16;
    const event = index > 92 && index < 126 ? Math.sin(index * 1.35) * 0.32 : 0;
    return base + event + (seededNumber(job.jobId, index) - 0.5) * 0.06;
  });
  const attentionWeights = Array.from({ length: pointCount }, (_, index) => {
    const peak = Math.max(0, 1 - Math.abs(index - 110) / 38);
    return Math.min(1, peak * 0.7 + seededNumber(job.jobId, index + 80) * 0.25);
  });
  const seizure = seededNumber(job.jobId, 3) > 0.45;
  return {
    jobId: job.jobId,
    recordingLabel: job.recordingLabel,
    submittedAt: job.submittedAt,
    prediction: seizure ? "seizure" : "no-seizure",
    confidence: seizure ? 0.87 : 0.78,
    privacyMethod: job.privacyMethod,
    timeSeries,
    attentionWeights,
    explanationSummary: "The highlighted interval contributed most strongly to this development prediction. Treat the overlay as an inspection aid, not a clinical explanation.",
    modelName: "development-stub",
    modelVersion: "stub-0.1.0",
    nonClinical: true,
    signalPreviewAvailable: true,
  };
}

export async function getJobs(signal?: AbortSignal): Promise<Job[]> {
  if (USE_STUB) {
    await wait(180);
    if (signal?.aborted) throw new DOMException("Request aborted.", "AbortError");
    const jobs = readStubJobs().map(advanceStubStatus);
    writeStubJobs(jobs);
    return jobs.sort((left, right) => right.submittedAt.localeCompare(left.submittedAt));
  }
  const sessions = await getJson<BackendSession[]>("/api/sessions", signal);
  return sessions.map((session) => ({
    jobId: session.session_id,
    recordingLabel: "EEG session",
    submittedAt: session.created_at,
    status: publicJobStatus(session.status),
    privacyMethod: methodForId(session.privacy_method),
    errorMessage: session.error_message ?? undefined,
  }));
}

export async function submitAnalysis(file: File, privacyMethodId: string, onProgress: (progress: number) => void, signal?: AbortSignal): Promise<{ jobId: string }> {
  if (USE_STUB) {
    for (const progress of [18, 42, 68, 100]) {
      await wait(160);
      if (signal?.aborted) throw new DOMException("Upload aborted.", "AbortError");
      onProgress(progress);
    }
    const method = PRIVACY_METHODS.find((item) => item.id === privacyMethodId) ?? PRIVACY_METHODS[0];
    const jobNumber = readStubJobs().length + 1;
    const job: Job = { jobId: `MDS-${Date.now().toString(36).toUpperCase()}`, recordingLabel: `Recording ${String(jobNumber).padStart(2, "0")}`, submittedAt: new Date().toISOString(), status: "queued", privacyMethod: method };
    writeStubJobs([job, ...readStubJobs()]);
    return { jobId: job.jobId };
  }
  const formData = new FormData();
  formData.append("archive", file);
  formData.append("privacy_method", privacyMethodId);
  const response = await uploadJson<{ session_id: string }>("/api/sessions/upload", formData, onProgress, signal);
  return { jobId: response.session_id };
}

export async function getResult(jobId: string, signal?: AbortSignal): Promise<AnalysisResult> {
  if (USE_STUB) {
    await wait(220);
    if (signal?.aborted) throw new DOMException("Request aborted.", "AbortError");
    const job = readStubJobs().map(advanceStubStatus).find((item) => item.jobId === jobId);
    if (!job) throw new ApiError("This analysis could not be found.", 404);
    return createStubResult(job);
  }
  const session = await getJson<BackendSession>(`/api/sessions/${encodeURIComponent(jobId)}`, signal);
  const record = session.recordings[0];
  if (!record) throw new ApiError("This session has no available recording.", 404);
  const [predictionPayload, explanationPayload, signalPayload] = await Promise.all([
    getJson<BackendPredictionResponse>(`/api/recordings/${encodeURIComponent(record.record_id)}/prediction`, signal),
    getJson<BackendExplanationResponse>(`/api/recordings/${encodeURIComponent(record.record_id)}/explanation`, signal),
    SHOW_SIGNAL_PREVIEW ? getJson<BackendSignalResponse>(`/api/recordings/${encodeURIComponent(record.record_id)}/signal?duration_seconds=10&max_points=180`, signal) : Promise.resolve(null),
  ]);
  const predictions = predictionPayload.predictions;
  const strongest = predictions.reduce((current, item) => item.probability > current.probability ? item : current, predictions[0] ?? { probability: 0, seizure_detected: false, start_seconds: 0, end_seconds: 0 });
  const timeSeries = downsample(signalPayload?.samples[0] ?? [], 180);
  const attentionWeights = timeSeries.map((_, index) => {
    const seconds = (index / Math.max(timeSeries.length - 1, 1)) * 10;
    const window = predictions.find((item) => seconds >= item.start_seconds && seconds <= item.end_seconds);
    return window?.probability ?? 0.12;
  });
  return {
    jobId,
    recordingLabel: `Recording ${String(record.sequence_index).padStart(2, "0")}`,
    submittedAt: session.created_at,
    prediction: strongest.seizure_detected ? "seizure" : "no-seizure",
    confidence: strongest.probability,
    privacyMethod: methodForId(session.privacy_method),
    timeSeries,
    attentionWeights,
    explanationSummary: explanationPayload.explanations.length > 0 ? "The highlighted interval reflects the strongest model prediction window. Treat this overlay as an inspection aid, not a clinical explanation." : "No explanation artifact was returned for this recording.",
    modelName: predictionPayload.model?.name ?? "backend-model",
    modelVersion: predictionPayload.model?.version ?? "unknown",
    nonClinical: explanationPayload.explanations.every((item) => !item.is_clinical),
    signalPreviewAvailable: SHOW_SIGNAL_PREVIEW,
  };
}

function downsample(values: number[], maximum: number): number[] {
  if (values.length <= maximum) return values;
  return Array.from({ length: maximum }, (_, index) => values[Math.floor((index / (maximum - 1)) * (values.length - 1))]);
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal, headers: { Accept: "application/json" }, credentials: "omit", cache: "no-store" });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
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
