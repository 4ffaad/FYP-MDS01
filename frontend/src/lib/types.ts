export type DisplayStatus = "queued" | "processing" | "complete" | "partial" | "failed";

export interface PrivacyMethod {
  id: string;
  label: string;
  description: string;
  previewTitle?: string;
  previewDescription?: string;
  required?: boolean;
}

export interface UploadDraft {
  draftId: string;
  status: "staged";
  createdAt: string;
  expiresAt: string;
}

export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
}

export interface SignalPreviewChannel {
  label: string;
  samples: number[];
}

export interface SignalPreview {
  recordId: string;
  representation: "metadata-scrubbed" | "signal-obfuscated";
  samplingRate: number;
  channels: SignalPreviewChannel[];
  timeSeconds: number[];
  segments: Array<{ sourceStartSeconds: number; sourceEndSeconds: number }>;
  flaggedIntervals: TimeInterval[];
}

export interface TimeInterval {
  startSeconds: number;
  endSeconds: number;
}

export type RecordingStatus = "uploaded" | "validating" | "deidentified" | "processing" | "processed" | "inferred" | "failed";

export interface Recording {
  recordId: string;
  sequenceIndex: number;
  displayName: string;
  status: RecordingStatus;
  durationSeconds: number | null;
  samplingRate: number | null;
  channelCount: number | null;
  errorMessage?: string;
  modelAlertWindowCount: number;
  modelAlert: boolean;
  alertIntervals: TimeInterval[];
  modelName?: string;
  modelVersion?: string;
  scoreType?: string;
  sessionId?: string;
  sessionCreatedAt?: string;
  privacyMethod?: PrivacyMethod;
  privacyMethods?: PrivacyMethod[];
}

export type SessionStatus = "queued" | "validating" | "deidentifying" | "preprocessing" | "inference" | "explaining" | "completed" | "completed_with_errors" | "failed";

export interface Session {
  sessionId: string;
  privacyMethod: PrivacyMethod;
  privacyMethods: PrivacyMethod[];
  status: SessionStatus;
  currentStage: string | null;
  createdAt: string;
  completedAt: string | null;
  errorMessage?: string;
  recordings: Recording[];
  progress: SessionProgress;
  summary: SessionSummary;
}

export interface SessionProgress {
  totalRecordings: number;
  finishedRecordings: number;
  completedRecordings: number;
  failedRecordings: number;
  percent: number;
}

export interface SessionSummary {
  modelAlertRecordings: number;
}

export type PredictionLabel = "seizure" | "no-seizure" | "review";

export interface PredictionWindow extends TimeInterval {
  /** The exact score used for thresholding and display. */
  score: number;
  /** Raw model output, shown only in technical details when available. */
  rawScore: number | null;
  /** Calibrated probability, present only for a reviewed calibrated model. */
  calibratedProbability: number | null;
  seizureDetected: boolean;
  threshold: number;
  scoreType?: string;
  calibrationMethod?: string | null;
  calibrationVersion?: string | null;
  calibrationDataset?: string | null;
}

export interface ResearchAttribution {
  method: "shap-gradient";
  windowIndex: number;
  windowStartSeconds: number;
  windowEndSeconds: number;
  score: number;
  threshold: number;
  topChannels: string[];
  channelScores: Array<{ label: string; meanAbsoluteAttribution: number }>;
  timeBins: Array<{ startSeconds: number; endSeconds: number; channelScores: number[] }>;
  note: string;
}

export interface AnalysisResult {
  recordId: string;
  sessionId: string;
  recordingLabel: string;
  submittedAt: string;
  prediction: PredictionLabel;
  peakWindowScore: number;
  threshold: number;
  scoreType: string;
  calibrationMethod: string | null;
  calibrationVersion: string | null;
  calibrationDataset: string | null;
  recordingProbabilityAvailable: boolean;
  windowCount: number;
  flaggedWindowCount: number;
  flaggedWindowFraction: number;
  privacyMethod: PrivacyMethod;
  privacyMethods: PrivacyMethod[];
  recordingDurationSeconds: number;
  alertIntervals: TimeInterval[];
  highestWindow: TimeInterval & { score: number } | null;
  predictionWindows: PredictionWindow[];
  explanationSummary: string;
  researchAttributions: ResearchAttribution[];
  modelName: string;
  modelVersion: string;
  nonClinical: boolean;
}

export interface ApiErrorPayload { detail?: string; }

export type VideoPrivacyProfile = "face-redacted" | "pose-only";
export type VideoPrivacyStatus = "queued" | "preflight" | "processing" | "validating" | "ready" | "needs_review" | "failed" | "expired";

export interface VideoPrivacyStage {
  id: "preflight" | "privacy-transform" | "output-validation" | "cleanup";
  status: "pending" | "active" | "complete";
}

export interface VideoPrivacyJob {
  jobId: string;
  label: string;
  profile: VideoPrivacyProfile;
  profileLabel: string;
  profileDescription: string;
  status: VideoPrivacyStatus;
  currentStage: string | null;
  stages: VideoPrivacyStage[];
  qualityFlags: string[];
  outputUsable: boolean;
  requiresAcknowledgement: boolean;
  acknowledged: boolean;
  previewAvailable: boolean;
  previewUrl: string | null;
  downloadAvailable: boolean;
  downloadUrl: string | null;
  retentionExpiresAt: string | null;
  durationSeconds: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  createdAt: string;
  completedAt: string | null;
  error: string | null;
  researchOnly: boolean;
  anonymityNotGuaranteed: boolean;
}
