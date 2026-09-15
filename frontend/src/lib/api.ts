import type {
  AnalysisResult,
  CaseSummary,
  CaseDetail,
  CaseAnalysis,
  AuthUser,
  ApiErrorPayload,
  DisplayStatus,
  Recording,
  RecordingStatus,
  Session,
  SessionProgress,
  SessionSummary,
  SessionStatus,
  PrivacyMethod,
  ResearchAttribution,
  SignalPreview,
  UploadDraft,
  VideoPrivacyJob,
  VideoPrivacyProfile,
  VideoPrivacyStage,
} from "./types";

function defaultApiBaseUrl(): string {
  // Local accounts use a SameSite=Lax cookie. Keep the UI and API on the same
  // hostname so both http://localhost and http://127.0.0.1 work in a browser.
  const hostname =
    typeof window === "undefined" ? "127.0.0.1" : window.location.hostname;
  return `http://${hostname}:8000`;
}

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBaseUrl()
).replace(/\/$/, "");
const REQUEST_CREDENTIALS: RequestCredentials = "include";
const USE_STUB = process.env.NEXT_PUBLIC_USE_API_STUB === "true";
export const AUTH_MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "backend";
export const ENABLE_SIGNAL_PREVIEW =
  process.env.NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW === "true";
export const ENABLE_FULL_SIGNAL_PREVIEW =
  ENABLE_SIGNAL_PREVIEW &&
  process.env.NEXT_PUBLIC_ENABLE_FULL_SIGNAL_PREVIEW === "true";
const JOBS_KEY = "mds01.jobs.v1";
const DRAFTS_KEY = "mds01.upload-drafts.v1";
const VIDEO_JOBS_KEY = "mds01.video-privacy.v1";
/** Exact channel order required by the backend model contract. */
export const PRIVACY_SIGNAL_CHANNELS = [
  "FP1-F7",
  "F7-T7",
  "T7-P7",
  "P7-O1",
  "FP1-F3",
  "F3-C3",
  "C3-P3",
  "P3-O1",
  "FP2-F4",
  "F4-C4",
  "C4-P4",
  "P4-O2",
  "FP2-F8",
  "F8-T8",
  "T8-P8",
  "P8-O2",
  "FZ-CZ",
  "CZ-PZ",
] as const;

export const PRIVACY_METHODS: PrivacyMethod[] = [
  {
    id: "metadata-scrub",
    label: "Metadata scrub",
    description:
      "Required baseline. Removes identifying EDF metadata while preserving waveform values.",
    previewTitle: "Waveform preserved",
    previewDescription:
      "The waveform stays the same. Identifying EDF header fields are removed before analysis.",
    required: true,
  },
  {
    id: "signal-obfuscation",
    label: "Signal obfuscation",
    description:
      "Optional keyed signal transformation. It reduces detail before model scoring and privacy evaluation.",
    previewTitle: "Signal detail reduced",
    previewDescription:
      "The transformed signal is sent to both model scoring and privacy evaluation. This is experimental risk reduction, not guaranteed anonymity.",
  },
];

/** Return the ordered methods represented by a user-facing selection. */
export function normalizePrivacySelection(
  selection: string | string[],
): string[] {
  const values = Array.isArray(selection) ? selection : [selection];
  const obfuscation = values.some(
    (value) =>
      value === "signal-obfuscation" ||
      value === "metadata-scrub+signal-obfuscation",
  );
  return obfuscation
    ? ["metadata-scrub", "signal-obfuscation"]
    : ["metadata-scrub"];
}

/** Describe the canonical profile stored by the backend. */
export function privacyProfileForSelection(
  selection: string | string[],
): PrivacyMethod {
  const methods = normalizePrivacySelection(selection);
  if (methods.includes("signal-obfuscation")) {
    return {
      id: "metadata-scrub+signal-obfuscation",
      label: "Metadata scrub + signal obfuscation",
      description:
        "The required metadata baseline is combined with the optional signal transformation.",
    };
  }
  return PRIVACY_METHODS[0];
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

type StubJob = {
  jobId: string;
  recordingLabel: string;
  submittedAt: string;
  status: "queued" | "processing" | "complete" | "failed";
  privacyMethod: PrivacyMethod;
  errorMessage?: string;
};

type StubDraft = UploadDraft & { fileSize: number };

type StubVideoJob = { job: VideoPrivacyJob; submittedAt: string };

type BackendAuthResponse = {
  authenticated: boolean;
  mode: string;
  user: { id: string; email: string; display_name: string } | null;
};

function authUserFromBackend(
  user: BackendAuthResponse["user"],
): AuthUser | null {
  return user
    ? { id: user.id, email: user.email, displayName: user.display_name }
    : null;
}

/** Read the backend-owned session state; no browser storage is used for auth. */
export async function getCurrentUser(): Promise<AuthUser | null> {
  if (AUTH_MODE === "stub")
    return {
      id: "USR-STUB",
      email: "demo@mds01.local",
      displayName: "Demo user",
    };
  const response = await fetch(`${API_BASE_URL}/api/auth/session`, {
    headers: { Accept: "application/json" },
    credentials: REQUEST_CREDENTIALS,
    cache: "no-store",
  });
  if (response.status === 401) return null;
  if (!response.ok) throw await readError(response, false);
  const payload = (await response.json()) as BackendAuthResponse;
  return payload.authenticated ? authUserFromBackend(payload.user) : null;
}

/** Register one local account and accept the HttpOnly cookie set by the API. */
export async function registerAccount(
  email: string,
  password: string,
): Promise<AuthUser> {
  const response = await postJson<BackendAuthResponse>("/api/auth/register", {
    email,
    password,
  });
  const user = authUserFromBackend(response.user);
  if (!user) throw new ApiError("The account could not be created.");
  return user;
}

/** Sign in through the backend session endpoint. */
export async function loginAccount(
  email: string,
  password: string,
): Promise<AuthUser> {
  const response = await postJson<BackendAuthResponse>("/api/auth/login", {
    email,
    password,
  });
  const user = authUserFromBackend(response.user);
  if (!user) throw new ApiError("The account could not be signed in.");
  return user;
}

/** Revoke the current server-side session. */
export async function logoutAccount(): Promise<void> {
  if (AUTH_MODE === "stub") return;
  await requestWithoutBody("/api/auth/logout", "POST", undefined, false);
}

type BackendVideoJob = {
  job_id: string;
  label: string;
  profile: VideoPrivacyProfile;
  profile_label: string;
  profile_description: string;
  status: VideoPrivacyJob["status"];
  current_stage: string | null;
  stages: VideoPrivacyStage[];
  quality_flags: string[];
  output_usable: boolean;
  requires_acknowledgement: boolean;
  acknowledged: boolean;
  preview_available: boolean;
  preview_url: string | null;
  download_available: boolean;
  download_url: string | null;
  retention_expires_at: string | null;
  duration_seconds: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  research_only: boolean;
  anonymity_not_guaranteed: boolean;
};

function readStubVideoJobs(): StubVideoJob[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(VIDEO_JOBS_KEY);
    return raw ? (JSON.parse(raw) as StubVideoJob[]) : [];
  } catch {
    return [];
  }
}

function writeStubVideoJobs(jobs: StubVideoJob[]): void {
  window.localStorage.setItem(VIDEO_JOBS_KEY, JSON.stringify(jobs));
}

function videoJobFromBackend(job: BackendVideoJob): VideoPrivacyJob {
  return {
    jobId: job.job_id,
    label: job.label,
    profile: job.profile,
    profileLabel: job.profile_label,
    profileDescription: job.profile_description,
    status: job.status,
    currentStage: job.current_stage,
    stages: job.stages,
    qualityFlags: job.quality_flags,
    outputUsable: job.output_usable,
    requiresAcknowledgement: job.requires_acknowledgement,
    acknowledged: job.acknowledged,
    previewAvailable: job.preview_available,
    previewUrl: job.preview_url ? `${API_BASE_URL}${job.preview_url}` : null,
    downloadAvailable: job.download_available,
    downloadUrl: job.download_url ? `${API_BASE_URL}${job.download_url}` : null,
    retentionExpiresAt: job.retention_expires_at,
    durationSeconds: job.duration_seconds,
    fps: job.fps,
    width: job.width,
    height: job.height,
    createdAt: job.created_at,
    completedAt: job.completed_at,
    error: job.error,
    researchOnly: job.research_only,
    anonymityNotGuaranteed: job.anonymity_not_guaranteed,
  };
}

function advanceStubVideoJob(stored: StubVideoJob): StubVideoJob {
  const elapsed = Date.now() - new Date(stored.submittedAt).getTime();
  const job = stored.job;
  if (job.status === "failed" || job.status === "expired") return stored;
  if (elapsed >= 2600) {
    const ready = {
      ...job,
      status: "ready" as const,
      currentStage: "cleanup",
      stages: job.stages.map((stage) => ({
        ...stage,
        status: "complete" as const,
      })),
      previewAvailable: true,
      downloadAvailable: true,
      downloadUrl: "data:video/mp4;base64,c3R1Yg==",
      completedAt: job.completedAt ?? new Date().toISOString(),
    };
    return { ...stored, job: ready };
  }
  if (elapsed >= 900) {
    const processing = {
      ...job,
      status: "processing" as const,
      currentStage: "privacy-transform",
      stages: job.stages.map((stage, index) => ({
        ...stage,
        status:
          index === 0
            ? ("complete" as const)
            : index === 1
              ? ("active" as const)
              : ("pending" as const),
      })),
    };
    return { ...stored, job: processing };
  }
  return stored;
}

function stubVideoJob(profile: VideoPrivacyProfile): VideoPrivacyJob {
  const now = new Date().toISOString();
  return {
    jobId: `VID-${Date.now().toString(36).toUpperCase()}`,
    label: "Video upload 01",
    profile,
    profileLabel: profile === "face-redacted" ? "Face redaction" : "Pose-only",
    profileDescription:
      profile === "face-redacted"
        ? "Blur detected faces while keeping the surrounding scene visible."
        : "Replace the scene with pose landmarks on a non-identifying background.",
    status: "queued",
    currentStage: "preflight",
    stages: [
      "preflight",
      "privacy-transform",
      "output-validation",
      "cleanup",
    ].map((id) => ({
      id: id as VideoPrivacyStage["id"],
      status: "pending" as const,
    })),
    qualityFlags: [],
    outputUsable: true,
    requiresAcknowledgement: false,
    acknowledged: false,
    previewAvailable: false,
    previewUrl: null,
    downloadAvailable: false,
    downloadUrl: null,
    retentionExpiresAt: new Date(
      Date.now() + 24 * 60 * 60 * 1000,
    ).toISOString(),
    durationSeconds: 42,
    fps: 30,
    width: 1280,
    height: 720,
    createdAt: now,
    completedAt: null,
    error: null,
    researchOnly: true,
    anonymityNotGuaranteed: true,
  };
}

function readStubJobs(): StubJob[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(JOBS_KEY);
    return raw ? (JSON.parse(raw) as StubJob[]) : [];
  } catch {
    return [];
  }
}

function writeStubJobs(jobs: StubJob[]): void {
  window.localStorage.setItem(JOBS_KEY, JSON.stringify(jobs));
}

function readStubDrafts(): StubDraft[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(DRAFTS_KEY);
    return raw ? (JSON.parse(raw) as StubDraft[]) : [];
  } catch {
    return [];
  }
}

function writeStubDrafts(drafts: StubDraft[]): void {
  window.localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

function methodForId(methodId: string | undefined): PrivacyMethod {
  if (methodId?.includes("signal-obfuscation"))
    return privacyProfileForSelection(["signal-obfuscation"]);
  return (
    PRIVACY_METHODS.find((item) => item.id === methodId) ?? PRIVACY_METHODS[0]
  );
}

function methodsForProfile(
  profile: string | undefined,
  methods?: string[],
): PrivacyMethod[] {
  return normalizePrivacySelection(methods ?? profile ?? "metadata-scrub").map(
    (id) =>
      PRIVACY_METHODS.find((item) => item.id === id) ?? PRIVACY_METHODS[0],
  );
}

type BackendSession = {
  session_id: string;
  case_id?: string | null;
  privacy_method: string;
  privacy_methods?: string[];
  status: string;
  current_stage: string | null;
  created_at: string;
  completed_at: string | null;
  error_message?: string | null;
  progress: {
    total_recordings: number;
    finished_recordings: number;
    completed_recordings: number;
    failed_recordings: number;
    percent: number;
  };
  summary: { model_alert_recordings: number };
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
  error_message?: string | null;
  model_alert_window_count?: number;
  model_alert?: boolean;
  alert_intervals?: Array<{ start_seconds: number; end_seconds: number }>;
  model_name?: string | null;
  model_version?: string | null;
  score_type?: string | null;
  session_id?: string;
  session_created_at?: string;
  privacy_method?: string;
  privacy_methods?: string[];
};

type BackendPredictionResponse = {
  model: {
    name: string;
    version: string;
    threshold: number;
    score_type: string;
    calibrated: boolean;
    calibration_method: string | null;
    calibration_version?: string | null;
    calibration_dataset?: string | null;
    privacy_method?: string | null;
  } | null;
  summary?: {
    window_count: number;
    flagged_window_count: number;
    flagged_window_fraction: number;
    peak_window_score: number;
    highest_window?: {
      start_seconds: number;
      end_seconds: number;
      score: number;
    } | null;
    alert_intervals?: Array<{ start_seconds: number; end_seconds: number }>;
    aggregation_unit: string;
    recording_probability_available: boolean;
  };
  predictions: Array<{
    start_seconds: number;
    end_seconds: number;
    score?: number;
    probability: number;
    raw_score?: number | null;
    calibrated_probability?: number | null;
    score_type?: string;
    calibration_method?: string | null;
    calibration_version?: string | null;
    calibration_dataset?: string | null;
    seizure_detected: boolean;
  }>;
};

type BackendExplanationResponse = {
  explanations: Array<{ is_clinical: boolean; data: unknown }>;
};

function parseResearchAttribution(data: unknown): ResearchAttribution | null {
  if (!data || typeof data !== "object") return null;
  const value = data as Record<string, unknown>;
  if (
    value.method !== "shap-gradient" ||
    typeof value.window_index !== "number" ||
    typeof value.score !== "number" ||
    typeof value.threshold !== "number"
  )
    return null;
  if (
    !Array.isArray(value.top_channels) ||
    !value.top_channels.every((item) => typeof item === "string")
  )
    return null;
  if (!Array.isArray(value.channel_scores) || !Array.isArray(value.time_bins))
    return null;
  const channelScores = value.channel_scores.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const channel = item as Record<string, unknown>;
    return typeof channel.label === "string" &&
      typeof channel.mean_absolute_attribution === "number"
      ? [
          {
            label: channel.label,
            meanAbsoluteAttribution: channel.mean_absolute_attribution,
          },
        ]
      : [];
  });
  const timeBins = value.time_bins.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const bin = item as Record<string, unknown>;
    return typeof bin.start_seconds === "number" &&
      typeof bin.end_seconds === "number" &&
      Array.isArray(bin.channel_scores) &&
      bin.channel_scores.every((score) => typeof score === "number")
      ? [
          {
            startSeconds: bin.start_seconds,
            endSeconds: bin.end_seconds,
            channelScores: bin.channel_scores as number[],
          },
        ]
      : [];
  });
  if (channelScores.length !== 18 || !timeBins.length) return null;
  return {
    method: "shap-gradient",
    windowIndex: value.window_index,
    windowStartSeconds:
      typeof value.window_start_seconds === "number"
        ? value.window_start_seconds
        : 0,
    windowEndSeconds:
      typeof value.window_end_seconds === "number"
        ? value.window_end_seconds
        : 0,
    score: value.score,
    threshold: value.threshold,
    topChannels: value.top_channels,
    channelScores,
    timeBins,
    note:
      typeof value.note === "string"
        ? value.note
        : "Research attribution is not a clinical explanation.",
  };
}

function publicSessionStatus(status: string): SessionStatus {
  if (status === "completed" || status === "completed_with_errors")
    return status;
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

function recordingFromBackend(
  recording: BackendRecording,
  session?: BackendSession,
): Recording {
  return {
    recordId: recording.record_id,
    sequenceIndex: recording.sequence_index,
    displayName: recording.source_filename,
    status: recording.status,
    durationSeconds: recording.duration_seconds,
    samplingRate: recording.sampling_rate,
    channelCount: recording.channel_count,
    modelAlertWindowCount: recording.model_alert_window_count ?? 0,
    modelAlert:
      recording.model_alert ?? (recording.model_alert_window_count ?? 0) > 0,
    alertIntervals: (recording.alert_intervals ?? []).map((interval) => ({
      startSeconds: interval.start_seconds,
      endSeconds: interval.end_seconds,
    })),
    modelName: recording.model_name ?? undefined,
    modelVersion: recording.model_version ?? undefined,
    scoreType: recording.score_type ?? undefined,
    errorMessage: recording.error_message ?? undefined,
    sessionId: recording.session_id ?? session?.session_id,
    sessionCreatedAt: recording.session_created_at ?? session?.created_at,
    privacyMethod: recording.privacy_method
      ? methodForId(recording.privacy_method)
      : session
        ? methodForId(session.privacy_method)
        : undefined,
    privacyMethods: methodsForProfile(
      recording.privacy_method ?? session?.privacy_method,
      recording.privacy_methods ?? session?.privacy_methods,
    ),
  };
}

function sessionFromBackend(session: BackendSession): Session {
  return {
    sessionId: session.session_id,
    caseId: session.case_id ?? null,
    privacyMethod: methodForId(session.privacy_method),
    privacyMethods: methodsForProfile(
      session.privacy_method,
      session.privacy_methods,
    ),
    status: publicSessionStatus(session.status),
    currentStage: session.current_stage,
    createdAt: session.created_at,
    completedAt: session.completed_at,
    errorMessage: session.error_message ?? undefined,
    recordings: session.recordings.map((recording) =>
      recordingFromBackend(recording, session),
    ),
    progress: progressFromBackend(session.progress),
    summary: summaryFromBackend(session.summary),
  };
}

function progressFromBackend(
  progress: BackendSession["progress"],
): SessionProgress {
  return {
    totalRecordings: progress.total_recordings,
    finishedRecordings: progress.finished_recordings,
    completedRecordings: progress.completed_recordings,
    failedRecordings: progress.failed_recordings,
    percent: progress.percent,
  };
}

function summaryFromBackend(
  summary: BackendSession["summary"],
): SessionSummary {
  return {
    modelAlertRecordings: summary.model_alert_recordings,
  };
}

function stubSessionFromJob(job: StubJob): Session {
  const status: SessionStatus =
    job.status === "complete"
      ? "completed"
      : job.status === "failed"
        ? "failed"
        : job.status === "processing"
          ? "preprocessing"
          : "queued";
  const modelAlertWindowCount =
    status === "completed" ? createStubResult(job).flaggedWindowCount : 0;
  return {
    sessionId: job.jobId,
    caseId: `CASE-${job.jobId.slice(-8)}`,
    privacyMethod: job.privacyMethod,
    privacyMethods: methodsForProfile(job.privacyMethod.id),
    status,
    currentStage:
      status === "queued" || status === "completed" || status === "failed"
        ? null
        : "processing",
    createdAt: job.submittedAt,
    completedAt: status === "completed" ? job.submittedAt : null,
    errorMessage: job.errorMessage,
    recordings: [
      {
        recordId: job.jobId,
        sequenceIndex: 1,
        displayName: job.recordingLabel,
        status:
          status === "completed"
            ? "inferred"
            : status === "failed"
              ? "failed"
              : "uploaded",
        durationSeconds: null,
        samplingRate: null,
        channelCount: null,
        modelAlertWindowCount,
        modelAlert: modelAlertWindowCount > 0,
        alertIntervals:
          status === "completed" ? createStubResult(job).alertIntervals : [],
        scoreType: "development_score",
        errorMessage: job.errorMessage,
        sessionId: job.jobId,
        sessionCreatedAt: job.submittedAt,
        privacyMethod: job.privacyMethod,
      },
    ],
    progress: {
      totalRecordings: 1,
      finishedRecordings: status === "completed" || status === "failed" ? 1 : 0,
      completedRecordings: status === "completed" ? 1 : 0,
      failedRecordings: status === "failed" ? 1 : 0,
      percent: status === "completed" || status === "failed" ? 100 : 0,
    },
    summary: { modelAlertRecordings: 0 },
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
  for (let index = 0; index < seed.length; index += 1)
    value = (value * 31 + seed.charCodeAt(index)) % 997;
  return ((value + offset * 37) % 100) / 100;
}

function mergeAlertIntervals(
  predictions: Array<{
    start_seconds?: number;
    end_seconds?: number;
    startSeconds?: number;
    endSeconds?: number;
    seizure_detected?: boolean;
    seizureDetected?: boolean;
  }>,
): Array<{ start_seconds: number; end_seconds: number }> {
  const ranges = predictions
    .filter(
      (prediction) => prediction.seizure_detected ?? prediction.seizureDetected,
    )
    .map((prediction) => ({
      start_seconds: prediction.start_seconds ?? prediction.startSeconds ?? 0,
      end_seconds: prediction.end_seconds ?? prediction.endSeconds ?? 0,
    }))
    .sort((left, right) => left.start_seconds - right.start_seconds);
  const merged: Array<{ start_seconds: number; end_seconds: number }> = [];
  for (const range of ranges) {
    if (range.end_seconds <= range.start_seconds) continue;
    const previous = merged.at(-1);
    if (previous && range.start_seconds <= previous.end_seconds)
      previous.end_seconds = Math.max(previous.end_seconds, range.end_seconds);
    else merged.push({ ...range });
  }
  return merged;
}

function predictionScore(
  prediction: BackendPredictionResponse["predictions"][number],
): number {
  return prediction.score ?? prediction.probability;
}

function findHighestWindow(
  predictions: BackendPredictionResponse["predictions"],
): { startSeconds: number; endSeconds: number; score: number } | null {
  const highest = predictions.reduce<(typeof predictions)[number] | null>(
    (current, item) =>
      !current || predictionScore(item) > predictionScore(current)
        ? item
        : current,
    null,
  );
  return highest
    ? {
        startSeconds: highest.start_seconds,
        endSeconds: highest.end_seconds,
        score: predictionScore(highest),
      }
    : null;
}

function createStubResult(job: StubJob): AnalysisResult {
  const predictionWindows = Array.from({ length: 29 }, (_, index) => {
    const score = seededNumber(job.jobId, index + 80);
    return {
      startSeconds: index * 2,
      endSeconds: index * 2 + 4,
      score,
      rawScore: null,
      calibratedProbability: null,
      threshold: 0.5,
      seizureDetected: score >= 0.5,
    };
  });
  const strongest = predictionWindows.reduce((current, item) =>
    item.score > current.score ? item : current,
  );
  const alertIntervals = mergeAlertIntervals(predictionWindows);
  return {
    recordId: job.jobId,
    sessionId: job.jobId,
    recordingLabel: job.recordingLabel,
    submittedAt: job.submittedAt,
    prediction: strongest.seizureDetected ? "seizure" : "no-seizure",
    peakWindowScore: strongest.score,
    threshold: 0.5,
    windowCount: predictionWindows.length,
    flaggedWindowCount: predictionWindows.filter((item) => item.seizureDetected)
      .length,
    flaggedWindowFraction:
      predictionWindows.filter((item) => item.seizureDetected).length /
      predictionWindows.length,
    privacyMethod: job.privacyMethod,
    privacyMethods: methodsForProfile(job.privacyMethod.id),
    recordingDurationSeconds: 60,
    alertIntervals: alertIntervals.map((interval) => ({
      startSeconds: interval.start_seconds,
      endSeconds: interval.end_seconds,
    })),
    highestWindow: {
      startSeconds: strongest.startSeconds,
      endSeconds: strongest.endSeconds,
      score: strongest.score,
    },
    predictionWindows,
    scoreType: "development_score",
    calibrationMethod: null,
    calibrationVersion: null,
    calibrationDataset: null,
    recordingProbabilityAvailable: false,
    explanationSummary:
      "Each point is the score for one four-second window. Amber windows crossed the displayed threshold; the timeline does not explain why the model produced a score.",
    researchAttributions: [],
    modelName: "development-stub",
    modelVersion: "stub-0.1.0",
    nonClinical: true,
  };
}

export async function getSessions(signal?: AbortSignal): Promise<Session[]> {
  if (USE_STUB) {
    await wait(180);
    if (signal?.aborted)
      throw new DOMException("Request aborted.", "AbortError");
    const jobs = readStubJobs().map(advanceStubStatus);
    writeStubJobs(jobs);
    return jobs
      .sort((left, right) => right.submittedAt.localeCompare(left.submittedAt))
      .map(stubSessionFromJob);
  }
  const sessions = await getJson<BackendSession[]>("/api/sessions", signal);
  return sessions.map(sessionFromBackend);
}

type BackendCaseSummary = {
  case_id: string;
  modalities: Array<"eeg" | "video">;
  analysis_count: number;
  latest_created_at: string;
  status: CaseSummary["status"];
  flagged_interval_count: number;
  explanation_ready: boolean;
};

export async function getCases(signal?: AbortSignal): Promise<CaseSummary[]> {
  if (USE_STUB) {
    const sessions = await getSessions(signal);
    return sessions.map((session) => ({
      caseId: session.caseId ?? `CASE-${session.sessionId.slice(-8)}`,
      modalities: ["eeg"],
      analysisCount: 1,
      latestCreatedAt: session.createdAt,
      status:
        toDisplayStatus(session.status) === "failed" ||
        toDisplayStatus(session.status) === "partial"
          ? "needs_review"
          : toDisplayStatus(session.status) === "complete"
            ? "complete"
            : "processing",
      flaggedIntervalCount: session.summary.modelAlertRecordings,
      explanationReady: toDisplayStatus(session.status) === "complete",
    }));
  }
  const cases = await getJson<BackendCaseSummary[]>("/api/cases", signal);
  return cases.map((item) => ({
    caseId: item.case_id,
    modalities: item.modalities,
    analysisCount: item.analysis_count,
    latestCreatedAt: item.latest_created_at,
    status: item.status,
    flaggedIntervalCount: item.flagged_interval_count,
    explanationReady: item.explanation_ready,
  }));
}

export async function getCase(
  caseId: string,
  signal?: AbortSignal,
): Promise<CaseDetail> {
  const response = await getJson<{
    case_id: string;
    analyses: Array<{
      id: string;
      modality: "eeg" | "video";
      status: CaseAnalysis["status"];
      created_at: string;
      review_ready: boolean;
    }>;
  }>(`/api/cases/${encodeURIComponent(caseId)}`, signal);
  return {
    caseId: response.case_id,
    analyses: response.analyses.map((analysis) => ({
      id: analysis.id,
      modality: analysis.modality,
      status: analysis.status,
      createdAt: analysis.created_at,
      reviewReady: analysis.review_ready,
    })),
  };
}

/** Return the backend asset URL for a protected video response. */
export function videoPrivacyAssetUrl(path: string | null): string | null {
  return path
    ? path.startsWith("http")
      ? path
      : `${API_BASE_URL}${path}`
    : null;
}

/** Create one standalone video privacy job. */
export async function submitVideoPrivacy(
  file: File,
  onProgress: (progress: number) => void,
  signal?: AbortSignal,
): Promise<VideoPrivacyJob> {
  if (USE_STUB) {
    for (const progress of [22, 56, 100]) {
      await wait(120);
      if (signal?.aborted)
        throw new DOMException("Upload aborted.", "AbortError");
      onProgress(progress);
    }
    const job = stubVideoJob("face-redacted");
    writeStubVideoJobs([
      { job, submittedAt: job.createdAt },
      ...readStubVideoJobs(),
    ]);
    return job;
  }
  const formData = new FormData();
  formData.append("video", file);
  formData.append("profile", "face-redacted");
  const response = await uploadJson<{ job: BackendVideoJob }>(
    "/api/video-privacy/jobs",
    formData,
    onProgress,
    signal,
  );
  return videoJobFromBackend(response.job);
}

/** Read one video privacy job and advance the local stub when enabled. */
export async function getVideoPrivacyJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<VideoPrivacyJob> {
  if (USE_STUB) {
    await wait(120);
    if (signal?.aborted)
      throw new DOMException("Request aborted.", "AbortError");
    const jobs = readStubVideoJobs().map(advanceStubVideoJob);
    writeStubVideoJobs(jobs);
    const match = jobs.find((item) => item.job.jobId === jobId)?.job;
    if (!match)
      throw new ApiError("This video privacy job could not be found.", 404);
    return match;
  }
  const response = await getJson<{ job: BackendVideoJob }>(
    `/api/video-privacy/jobs/${encodeURIComponent(jobId)}`,
    signal,
  );
  return videoJobFromBackend(response.job);
}

/** Acknowledge a usable quality caveat before downloading the output. */
export async function acknowledgeVideoPrivacyJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<VideoPrivacyJob> {
  if (USE_STUB) {
    const jobs = readStubVideoJobs();
    const match = jobs.find((item) => item.job.jobId === jobId);
    if (!match)
      throw new ApiError("This video privacy job could not be found.", 404);
    if (match.job.status !== "needs_review" || !match.job.outputUsable)
      throw new ApiError("This output does not require acknowledgement.", 409);
    const job = {
      ...match.job,
      acknowledged: true,
      requiresAcknowledgement: false,
      downloadAvailable: true,
    };
    writeStubVideoJobs(
      jobs.map((item) => (item.job.jobId === jobId ? { ...item, job } : item)),
    );
    return job;
  }
  const response = await postFormJson<{ job: BackendVideoJob }>(
    `/api/video-privacy/jobs/${encodeURIComponent(jobId)}/acknowledge`,
    new FormData(),
    signal,
  );
  return videoJobFromBackend(response.job);
}

export async function getSession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<Session> {
  if (USE_STUB) {
    const session = (await getSessions(signal)).find(
      (item) => item.sessionId === sessionId,
    );
    if (!session) throw new ApiError("This session could not be found.", 404);
    return session;
  }
  return sessionFromBackend(
    await getJson<BackendSession>(
      `/api/sessions/${encodeURIComponent(sessionId)}`,
      signal,
    ),
  );
}

export async function deleteSession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<void> {
  if (USE_STUB) {
    await wait(80);
    if (signal?.aborted)
      throw new DOMException("Delete aborted.", "AbortError");
    writeStubJobs(readStubJobs().filter((job) => job.jobId !== sessionId));
    return;
  }
  await requestWithoutBody(
    `/api/sessions/${encodeURIComponent(sessionId)}`,
    "DELETE",
    signal,
  );
}

export async function getRecording(
  recordId: string,
  signal?: AbortSignal,
): Promise<Recording> {
  if (USE_STUB) {
    const session = (await getSessions(signal)).find((item) =>
      item.recordings.some((recording) => recording.recordId === recordId),
    );
    const recording = session?.recordings.find(
      (item) => item.recordId === recordId,
    );
    if (!recording)
      throw new ApiError("This recording could not be found.", 404);
    return recording;
  }
  return recordingFromBackend(
    await getJson<BackendRecording>(
      `/api/recordings/${encodeURIComponent(recordId)}`,
      signal,
    ),
  );
}

export async function stageUpload(
  file: File,
  onProgress: (progress: number) => void,
  signal?: AbortSignal,
): Promise<UploadDraft> {
  if (USE_STUB) {
    for (const progress of [18, 42, 68, 100]) {
      await wait(160);
      if (signal?.aborted)
        throw new DOMException("Upload aborted.", "AbortError");
      onProgress(progress);
    }
    const now = new Date();
    const draft: StubDraft = {
      draftId: `UPL-${Date.now().toString(36).toUpperCase()}`,
      status: "staged",
      createdAt: now.toISOString(),
      expiresAt: new Date(now.getTime() + 30 * 60 * 1000).toISOString(),
      fileSize: file.size,
    };
    writeStubDrafts([draft, ...readStubDrafts()]);
    return draft;
  }
  const formData = new FormData();
  formData.append("archive", file);
  const response = await uploadJson<{
    draft_id: string;
    status: "staged";
    created_at: string;
    expires_at: string;
  }>("/api/uploads/drafts", formData, onProgress, signal);
  return {
    draftId: response.draft_id,
    status: response.status,
    createdAt: response.created_at,
    expiresAt: response.expires_at,
  };
}

export async function getUploadDraft(
  draftId: string,
  signal?: AbortSignal,
): Promise<UploadDraft> {
  if (USE_STUB) {
    await wait(100);
    const draft = readStubDrafts().find((item) => item.draftId === draftId);
    if (!draft || new Date(draft.expiresAt).getTime() <= Date.now())
      throw new ApiError("This upload draft has expired.", 404);
    return draft;
  }
  const response = await getJson<{
    draft_id: string;
    status: "staged";
    created_at: string;
    expires_at: string;
  }>(`/api/uploads/drafts/${encodeURIComponent(draftId)}`, signal);
  return {
    draftId: response.draft_id,
    status: response.status,
    createdAt: response.created_at,
    expiresAt: response.expires_at,
  };
}

export async function finalizeUploadDraft(
  draftId: string,
  privacySelection: string | string[],
  caseId?: string,
  signal?: AbortSignal,
): Promise<{ sessionId: string; caseId: string | null }> {
  const methodIds = normalizePrivacySelection(privacySelection);
  if (USE_STUB) {
    await wait(160);
    if (signal?.aborted)
      throw new DOMException("Request aborted.", "AbortError");
    const draft = readStubDrafts().find((item) => item.draftId === draftId);
    if (!draft)
      throw new ApiError("This upload draft could not be found.", 404);
    const method = privacyProfileForSelection(methodIds);
    const jobNumber = readStubJobs().length + 1;
    const job: StubJob = {
      jobId: `MDS-${Date.now().toString(36).toUpperCase()}`,
      recordingLabel: `Recording ${String(jobNumber).padStart(2, "0")}`,
      submittedAt: new Date().toISOString(),
      status: "queued",
      privacyMethod: method,
    };
    writeStubDrafts(
      readStubDrafts().filter((item) => item.draftId !== draftId),
    );
    writeStubJobs([job, ...readStubJobs()]);
    return {
      sessionId: job.jobId,
      caseId: caseId ?? `CASE-${job.jobId.slice(-8)}`,
    };
  }
  const formData = new FormData();
  formData.append("privacy_methods", JSON.stringify(methodIds));
  if (caseId) formData.append("case_id", caseId);
  const response = await postFormJson<{
    session_id: string;
    case_id?: string | null;
    status: string;
  }>(
    `/api/uploads/drafts/${encodeURIComponent(draftId)}/finalize`,
    formData,
    signal,
  );
  return { sessionId: response.session_id, caseId: response.case_id ?? null };
}

export async function deleteUploadDraft(
  draftId: string,
  signal?: AbortSignal,
): Promise<void> {
  if (USE_STUB) {
    writeStubDrafts(
      readStubDrafts().filter((item) => item.draftId !== draftId),
    );
    return;
  }
  await requestWithoutBody(
    `/api/uploads/drafts/${encodeURIComponent(draftId)}`,
    "DELETE",
    signal,
  );
}

/** Backwards-compatible one-call upload for existing callers. */
export async function submitAnalysis(
  file: File,
  privacyMethodId: string | string[],
  onProgress: (progress: number) => void,
  signal?: AbortSignal,
): Promise<{ sessionId: string }> {
  const draft = await stageUpload(file, onProgress, signal);
  return finalizeUploadDraft(draft.draftId, privacyMethodId, undefined, signal);
}

export async function getResult(
  recordId: string,
  signal?: AbortSignal,
): Promise<AnalysisResult> {
  if (USE_STUB) {
    await wait(220);
    if (signal?.aborted)
      throw new DOMException("Request aborted.", "AbortError");
    const job = readStubJobs()
      .map(advanceStubStatus)
      .find((item) => item.jobId === recordId);
    if (!job) throw new ApiError("This analysis could not be found.", 404);
    if (job.status === "failed")
      throw new ApiError(
        job.errorMessage ?? "This recording failed during processing.",
        422,
      );
    return createStubResult(job);
  }
  const record = await getRecording(recordId, signal);
  if (record.status === "failed")
    throw new ApiError(
      record.errorMessage ?? "This recording failed during processing.",
      422,
    );
  const [predictionPayload, explanationPayload] = await Promise.all([
    getJson<BackendPredictionResponse>(
      `/api/recordings/${encodeURIComponent(record.recordId)}/prediction`,
      signal,
    ),
    getJson<BackendExplanationResponse>(
      `/api/recordings/${encodeURIComponent(record.recordId)}/explanation`,
      signal,
    ),
  ]);
  const predictions = predictionPayload.predictions;
  const predictionSummary = predictionPayload.summary ?? {
    window_count: predictions.length,
    flagged_window_count: predictions.filter((item) => item.seizure_detected)
      .length,
    flagged_window_fraction: predictions.length
      ? predictions.filter((item) => item.seizure_detected).length /
        predictions.length
      : 0,
    peak_window_score: Math.max(...predictions.map(predictionScore), 0),
    highest_window: findHighestWindow(predictions),
    alert_intervals: mergeAlertIntervals(predictions),
    aggregation_unit: "window",
    recording_probability_available: false,
  };
  const researchAttributions = explanationPayload.explanations
    .filter((item) => !item.is_clinical)
    .map((item) => parseResearchAttribution(item.data))
    .filter((item): item is ResearchAttribution => item !== null);
  const highestWindow = predictionSummary.highest_window;
  return {
    recordId,
    sessionId: record.sessionId ?? "unknown-session",
    recordingLabel: record.displayName,
    submittedAt: record.sessionCreatedAt ?? new Date().toISOString(),
    prediction:
      predictionSummary.flagged_window_count > 0 ? "seizure" : "no-seizure",
    peakWindowScore: predictionSummary.peak_window_score,
    threshold: predictionPayload.model?.threshold ?? 0.5,
    windowCount: predictionSummary.window_count,
    flaggedWindowCount: predictionSummary.flagged_window_count,
    flaggedWindowFraction: predictionSummary.flagged_window_fraction,
    scoreType:
      predictionPayload.model?.score_type ??
      predictions[0]?.score_type ??
      "development_score",
    calibrationMethod: predictionPayload.model?.calibration_method ?? null,
    calibrationVersion: predictionPayload.model?.calibration_version ?? null,
    calibrationDataset: predictionPayload.model?.calibration_dataset ?? null,
    recordingProbabilityAvailable:
      predictionSummary.recording_probability_available,
    privacyMethod: record.privacyMethod ?? methodForId(undefined),
    privacyMethods: record.privacyMethods ?? [
      record.privacyMethod ?? methodForId(undefined),
    ],
    recordingDurationSeconds:
      record.durationSeconds ?? predictions.at(-1)?.end_seconds ?? 0,
    alertIntervals: (
      predictionSummary.alert_intervals ?? mergeAlertIntervals(predictions)
    ).map((interval) => ({
      startSeconds: interval.start_seconds,
      endSeconds: interval.end_seconds,
    })),
    highestWindow: highestWindow
      ? {
          startSeconds:
            "start_seconds" in highestWindow
              ? highestWindow.start_seconds
              : highestWindow.startSeconds,
          endSeconds:
            "end_seconds" in highestWindow
              ? highestWindow.end_seconds
              : highestWindow.endSeconds,
          score: highestWindow.score,
        }
      : findHighestWindow(predictions),
    predictionWindows: predictions.map((prediction) => ({
      startSeconds: prediction.start_seconds,
      endSeconds: prediction.end_seconds,
      score: predictionScore(prediction),
      rawScore: prediction.raw_score ?? null,
      calibratedProbability: prediction.calibrated_probability ?? null,
      threshold: predictionPayload.model?.threshold ?? 0.5,
      scoreType: prediction.score_type ?? predictionPayload.model?.score_type,
      calibrationMethod:
        prediction.calibration_method ??
        predictionPayload.model?.calibration_method ??
        null,
      calibrationVersion:
        prediction.calibration_version ??
        predictionPayload.model?.calibration_version ??
        null,
      calibrationDataset:
        prediction.calibration_dataset ??
        predictionPayload.model?.calibration_dataset ??
        null,
      seizureDetected: prediction.seizure_detected,
    })),
    explanationSummary:
      explanationPayload.explanations.length > 0
        ? predictionPayload.model?.score_type === "calibrated_probability"
          ? "Each point is the estimated probability that one four-second window meets the research seizure-label definition. Highlighted windows crossed the displayed threshold; this is not a recording-level probability or diagnosis."
          : "Each point is the score for one four-second window. Highlighted windows crossed the displayed threshold; the timeline does not explain why the model produced a score."
        : "No explanation artifact was returned for this recording.",
    researchAttributions,
    modelName: predictionPayload.model?.name ?? "backend-model",
    modelVersion: predictionPayload.model?.version ?? "unknown",
    nonClinical: explanationPayload.explanations.every(
      (item) => !item.is_clinical,
    ),
  };
}

export async function getSignalPreview(
  recordId: string,
  startSeconds: number,
  durationSeconds: number,
  maxPoints: number,
  signal?: AbortSignal,
): Promise<SignalPreview> {
  if (USE_STUB) {
    await wait(120);
    if (signal?.aborted)
      throw new DOMException("Request aborted.", "AbortError");
    const result = await getResult(recordId, signal);
    if (result.flaggedWindowCount === 0)
      throw new ApiError(
        "No model-positive signal is available for this recording.",
        404,
      );
    const points = Math.min(maxPoints, 480);
    const timeSeconds = Array.from(
      { length: points },
      (_, index) =>
        startSeconds + (durationSeconds * index) / Math.max(1, points - 1),
    );
    const channels = PRIVACY_SIGNAL_CHANNELS.map((label, channelIndex) => ({
      label,
      samples: timeSeconds.map((time, index) => {
        const relativeTime = time - startSeconds;
        const phase = channelIndex * 0.37;
        const baseline =
          Math.sin(
            relativeTime * Math.PI * 2 * (7.2 + channelIndex * 0.04) + phase,
          ) *
            0.17 +
          Math.sin(relativeTime * Math.PI * 2 * 13.4 + phase * 0.7) * 0.07 +
          Math.sin(relativeTime * Math.PI * 2 * 31 + channelIndex) * 0.025 +
          Math.sin((index + 1) * (channelIndex + 3) * 1.618) * 0.035;
        const flagged = result.alertIntervals.some(
          (interval) =>
            time >= interval.startSeconds && time <= interval.endSeconds,
        );
        const pulsePosition = (relativeTime * 4.5 + channelIndex * 0.11) % 1;
        const transient = flagged
          ? Math.exp(-(((pulsePosition - 0.18) / 0.055) ** 2)) * 0.2 -
            Math.exp(-(((pulsePosition - 0.28) / 0.08) ** 2)) * 0.11
          : 0;
        return baseline + transient;
      }),
    }));
    return {
      recordId,
      representation: result.privacyMethods.some(
        (method) => method.id === "signal-obfuscation",
      )
        ? "signal-obfuscated"
        : "metadata-scrubbed",
      samplingRate: 256,
      channels,
      timeSeconds,
      segments: [
        {
          sourceStartSeconds: startSeconds,
          sourceEndSeconds: startSeconds + durationSeconds,
        },
      ],
      flaggedIntervals: result.alertIntervals
        .filter(
          (window) =>
            window.endSeconds > startSeconds &&
            window.startSeconds < startSeconds + durationSeconds,
        )
        .map((window) => ({
          startSeconds: Math.max(startSeconds, window.startSeconds),
          endSeconds: Math.min(
            startSeconds + durationSeconds,
            window.endSeconds,
          ),
        })),
    };
  }
  const query = new URLSearchParams({
    start_seconds: String(startSeconds),
    duration_seconds: String(durationSeconds),
    max_points: String(maxPoints),
  });
  const response = await getJson<{
    record_id: string;
    representation: "metadata-scrubbed" | "signal-obfuscated";
    sampling_rate: number;
    channels: Array<{ label: string; samples: number[] }>;
    time_seconds: number[];
    segments: Array<{
      source_start_seconds: number;
      source_end_seconds: number;
    }>;
    flagged_intervals: Array<{ start_seconds: number; end_seconds: number }>;
  }>(
    `/api/recordings/${encodeURIComponent(recordId)}/signal?${query.toString()}`,
    signal,
  );
  return {
    recordId: response.record_id,
    representation: response.representation,
    samplingRate: response.sampling_rate,
    channels: response.channels,
    timeSeconds: response.time_seconds,
    segments: response.segments.map((segment) => ({
      sourceStartSeconds: segment.source_start_seconds,
      sourceEndSeconds: segment.source_end_seconds,
    })),
    flaggedIntervals: response.flagged_intervals.map((interval) => ({
      startSeconds: interval.start_seconds,
      endSeconds: interval.end_seconds,
    })),
  };
}

export async function getJson<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    signal,
    headers: { Accept: "application/json" },
    credentials: REQUEST_CREDENTIALS,
    cache: "no-store",
  });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

async function requestWithoutBody(
  path: string,
  method: string,
  signal?: AbortSignal,
  notifyExpiry = true,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    signal,
    headers: { Accept: "application/json" },
    credentials: REQUEST_CREDENTIALS,
  });
  if (!response.ok) throw await readError(response, notifyExpiry);
}

async function postFormJson<T>(
  path: string,
  body: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body,
    signal,
    headers: { Accept: "application/json" },
    credentials: REQUEST_CREDENTIALS,
  });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: JSON.stringify(body),
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    credentials: REQUEST_CREDENTIALS,
  });
  if (!response.ok) throw await readError(response, false);
  return (await response.json()) as T;
}

async function readError(
  response: Response,
  notifyExpiry = true,
): Promise<ApiError> {
  if (
    notifyExpiry &&
    response.status === 401 &&
    typeof window !== "undefined"
  ) {
    window.dispatchEvent(new Event("mds01:auth-expired"));
  }
  let message = `Request failed with status ${response.status}.`;
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload.detail) message = payload.detail;
  } catch {
    /* Keep the status message. */
  }
  return new ApiError(message, response.status);
}

export function uploadJson<T>(
  path: string,
  body: FormData,
  onProgress: (progress: number) => void,
  signal?: AbortSignal,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}${path}`);
    request.withCredentials = true;
    request.responseType = "json";
    request.setRequestHeader("Accept", "application/json");
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable)
        onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300)
        return resolve(request.response as T);
      const detail = (request.response as ApiErrorPayload | null)?.detail;
      reject(
        new ApiError(
          detail ?? `Upload failed with status ${request.status}.`,
          request.status,
        ),
      );
    });
    request.addEventListener("error", () =>
      reject(new ApiError("The analysis service could not be reached.")),
    );
    request.addEventListener("abort", () =>
      reject(new DOMException("Upload aborted.", "AbortError")),
    );
    if (signal) {
      if (signal.aborted) request.abort();
      signal.addEventListener("abort", () => request.abort(), { once: true });
    }
    request.send(body);
  });
}
