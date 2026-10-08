export type DisplayStatus =
  | "queued"
  | "processing"
  | "complete"
  | "partial"
  | "failed";

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
  timeSeconds?: number[];
}

export interface SignalPreview {
  recordId: string;
  representation: "metadata-scrubbed" | "signal-obfuscated" | "original-source";
  displayFilter?: string | null;
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

export type RecordingStatus =
  | "uploaded"
  | "validating"
  | "deidentified"
  | "processing"
  | "processed"
  | "inferred"
  | "failed";

export interface Recording {
  sourceAvailable?: boolean;
  retentionPolicy?: string;
  recordId: string;
  sequenceIndex: number;
  displayName: string;
  sourceFormat?: "edf" | "nicolet" | "nicolet-e";
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

export type PatientNameVerificationStatus = "reviewed" | "auto_extracted";

export interface CaseSummary {
  caseId: string;
  patientName?: string | null;
  patientNameVerificationStatus?: PatientNameVerificationStatus | null;
  reportSummary?: string | null;
  modalities: Array<"eeg" | "video">;
  analysisCount: number;
  eegRecordingCount?: number;
  videoClipCount?: number;
  privacyPreviewCount: number;
  latestCreatedAt: string;
  status: "processing" | "complete" | "needs_review";
  flaggedIntervalCount: number;
  explanationReady: boolean;
}

export interface CaseAnalysis {
  id: string;
  modality: "eeg" | "video";
  status: "processing" | "complete" | "needs_review";
  createdAt: string;
  reviewReady: boolean;
}

export interface CaseDetail {
  caseId: string;
  patientName?: string | null;
  patientNameVerificationStatus?: PatientNameVerificationStatus | null;
  analyses: CaseAnalysis[];
}

export interface PatientProfileDetail {
  label: string;
  value: string;
}

export interface PatientProfile {
  name: string;
  hospitalId: string;
  age: string;
  findings: string;
  details?: PatientProfileDetail[];
  reviewed: boolean;
  verificationStatus: "reviewed" | "auto_extracted";
  reviewedAt: string | null;
}

export type SessionStatus =
  | "queued"
  | "validating"
  | "deidentifying"
  | "preprocessing"
  | "inference"
  | "explaining"
  | "completed"
  | "completed_with_errors"
  | "failed";

export interface Session {
  sourceAvailable?: boolean;
  retentionPolicy?: string;
  sessionId: string;
  caseId: string | null;
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
  processingAttempts: ProcessingAttempt[];
}

export interface ProcessingAttempt {
  recordingSequenceIndex: number | null;
  stage: string;
  status: "pending" | "running" | "succeeded" | "failed";
  startedAt: string | null;
  finishedAt: string | null;
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
  timeBins: Array<{
    startSeconds: number;
    endSeconds: number;
    channelScores: number[];
  }>;
  note: string;
}

export type EegAnnotationKind = "seizure_event" | "manual_annotation" | "other";

export type EegAnnotationSource =
  | "embedded-nicolet"
  | "reference"
  | "demo-fixture"
  | "unavailable";

export interface EegAnnotationEvent {
  onsetSeconds: number;
  durationSeconds: number;
  kind: EegAnnotationKind;
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
  highestWindow: (TimeInterval & { score: number }) | null;
  predictionWindows: PredictionWindow[];
  explanationSummary: string;
  researchAttributions: ResearchAttribution[];
  annotationEvents: EegAnnotationEvent[];
  annotationSource: EegAnnotationSource;
  annotationReviewRequired: boolean;
  modelName: string;
  modelVersion: string;
  nonClinical: boolean;
}

export interface ApiErrorPayload {
  detail?: unknown;
}

export type VideoPrivacyProfile =
  | "face-redacted"
  | "face-redacted-pose-preview"
  | "pose-only";
export type VideoPrivacyStatus =
  | "queued"
  | "preflight"
  | "processing"
  | "validating"
  | "ready"
  | "needs_review"
  | "failed"
  | "expired";

export interface VideoPrivacyStage {
  id:
    | "preflight"
    | "privacy-transform"
    | "keypoint-preview"
    | "output-validation"
    | "cleanup";
  status: "pending" | "active" | "complete";
}

export interface VideoPrivacyPoseEvidence {
  model: "Lightweight OpenPose";
  detectedFrames: number;
  sampledFrames: number;
  trackingStopped: boolean;
  status: "not-detected" | "partial" | "complete";
  actionUnits: "not-configured";
}

export interface VideoPrivacyJob {
  jobId: string;
  caseId: string | null;
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
  poseEvidence: VideoPrivacyPoseEvidence | null;
  createdAt: string;
  completedAt: string | null;
  error: string | null;
  researchOnly: boolean;
  anonymityNotGuaranteed: boolean;
}
