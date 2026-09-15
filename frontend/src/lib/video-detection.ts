import { getJson, uploadJson } from "./api";

export interface DetectionJob {
  job_id: string;
  case_id: string | null;
  label: string;
  status: "queued" | "processing" | "ready" | "failed" | "expired";
  current_stage: string;
  duration_seconds: number;
  fps: number;
  created_at: string;
  retention_expires_at: string;
  video_available: boolean;
  error: string | null;
}

export interface DetectionResult {
  model: {
    model_name: string;
    model_version: string;
    weights_hash: string;
    preprocessing_version: string;
    threshold: number;
    sample_fps: number;
    window_frames: number;
    stride_frames: number;
    calibrated: false;
  };
  predictions: {
    start_time: number;
    end_time: number;
    raw_score: number;
    score: number;
    score_type: string;
    seizure_detected: boolean;
    model_evidence?: {
      method: "patch-occlusion";
      note: string;
      patches: { patch_index: number; score_change: number }[];
    };
  }[];
  intervals: { start_time: number; end_time: number }[];
  recording_probability_available: false;
  privacy?: {
    method: "face-redaction";
    model_input: "face-redacted video";
    face_detection_coverage: number;
    quality_flags: string[];
    review_required: boolean;
  };
}

export async function uploadDetection(
  file: File,
  progress: (value: number) => void,
  caseId?: string,
) {
  const data = new FormData();
  data.append("video", file);
  if (caseId) data.append("case_id", caseId);
  try {
    return await uploadJson<{ job: DetectionJob }>(
      "/api/video-detection/jobs",
      data,
      progress,
    );
  } catch (error) {
    if (
      error &&
      typeof error === "object" &&
      "status" in error &&
      error.status === 401
    )
      window.dispatchEvent(new Event("mds01:auth-expired"));
    throw error;
  }
}

export const listDetections = (signal?: AbortSignal) =>
  getJson<{ jobs: DetectionJob[] }>("/api/video-detection/jobs", signal);
export const getDetection = (id: string, signal?: AbortSignal) =>
  getJson<{ job: DetectionJob }>(
    `/api/video-detection/jobs/${encodeURIComponent(id)}`,
    signal,
  );
export const getDetectionResults = (id: string, signal?: AbortSignal) =>
  getJson<DetectionResult>(
    `/api/video-detection/jobs/${encodeURIComponent(id)}/predictions`,
    signal,
  );
