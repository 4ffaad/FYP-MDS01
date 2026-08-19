export type JobStatus = "queued" | "processing" | "complete" | "failed";

export interface PrivacyMethod {
  id: string;
  label: string;
  description: string;
}

export interface Job {
  jobId: string;
  recordingLabel: string;
  submittedAt: string;
  status: JobStatus;
  privacyMethod: PrivacyMethod;
  errorMessage?: string;
}

export type PredictionLabel = "seizure" | "no-seizure" | "review";

export interface AnalysisResult {
  jobId: string;
  recordingLabel: string;
  submittedAt: string;
  prediction: PredictionLabel;
  confidence: number;
  privacyMethod: PrivacyMethod;
  timeSeries: number[];
  attentionWeights: number[];
  explanationSummary: string;
  modelName: string;
  modelVersion: string;
  nonClinical: boolean;
}

export interface ApiErrorPayload { detail?: string; }
