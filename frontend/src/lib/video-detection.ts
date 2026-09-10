import { getJson, uploadJson, videoPrivacyAssetUrl } from "./api";

export interface DetectionJob {
  job_id: string;
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
  predictions: { start_time: number; end_time: number; raw_score: number; score: number; score_type: string; seizure_detected: boolean }[];
  intervals: { start_time: number; end_time: number }[];
  recording_probability_available: false;
}

export async function uploadDetection(file: File, progress: (value: number) => void) {
  const data = new FormData();
  data.append("video", file);
  try {
    return await uploadJson<{ job: DetectionJob }>("/api/video-detection/jobs", data, progress);
  } catch (error) {
    if (error && typeof error === "object" && "status" in error && error.status === 401) window.dispatchEvent(new Event("mds01:auth-expired"));
    throw error;
  }
}

export const listDetections = (signal?: AbortSignal) => getJson<{ jobs: DetectionJob[] }>("/api/video-detection/jobs", signal);
export const getDetection = (id: string, signal?: AbortSignal) => getJson<{ job: DetectionJob }>(`/api/video-detection/jobs/${encodeURIComponent(id)}`, signal);
export const getDetectionResults = (id: string, signal?: AbortSignal) => getJson<DetectionResult>(`/api/video-detection/jobs/${encodeURIComponent(id)}/predictions`, signal);
export const detectionVideoUrl = (id: string) => videoPrivacyAssetUrl(`/api/video-detection/jobs/${encodeURIComponent(id)}/video`);
