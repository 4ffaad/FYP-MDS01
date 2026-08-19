export type DisplayStatus = "queued" | "processing" | "complete" | "partial" | "failed";

export interface PrivacyMethod {
  id: string;
  label: string;
  description: string;
}

export interface TimeInterval {
  startSeconds: number;
  endSeconds: number;
}

export interface ReferenceAnnotation {
  source: string;
  intervals: TimeInterval[];
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
  referenceAnnotation: ReferenceAnnotation | null;
  modelAlertWindowCount: number;
  sessionId?: string;
  sessionCreatedAt?: string;
  privacyMethod?: PrivacyMethod;
}

export type SessionStatus = "queued" | "validating" | "deidentifying" | "preprocessing" | "inference" | "explaining" | "completed" | "completed_with_errors" | "failed";

export interface Session {
  sessionId: string;
  privacyMethod: PrivacyMethod;
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
  datasetSeizureRecordings: number | null;
  modelAlertRecordings: number;
}

export type PredictionLabel = "seizure" | "no-seizure" | "review";

export interface PredictionWindow extends TimeInterval {
  probability: number;
  seizureDetected: boolean;
}

export interface SignalPreview {
  channelLabels: string[];
  samples: number[][];
  samplingRate: number;
  startSeconds: number;
  durationSeconds: number;
}

export interface AnalysisResult {
  recordId: string;
  sessionId: string;
  recordingLabel: string;
  submittedAt: string;
  prediction: PredictionLabel;
  peakWindowScore: number;
  windowCount: number;
  flaggedWindowCount: number;
  flaggedWindowFraction: number;
  privacyMethod: PrivacyMethod;
  recordingDurationSeconds: number;
  predictionWindows: PredictionWindow[];
  referenceAnnotation: ReferenceAnnotation | null;
  signalPreview: SignalPreview | null;
  signalPreviewAvailable: boolean;
  explanationSummary: string;
  modelName: string;
  modelVersion: string;
  nonClinical: boolean;
}

export interface ApiErrorPayload { detail?: string; }
