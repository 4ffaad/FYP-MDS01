import { getBlob, getJson, uploadJson } from "./api";

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
  visualization_available: boolean;
  visualization_url: string | null;
  error: string | null;
}

export interface DetectionResult {
  duration_seconds?: number;
  fps?: number;
  frame_count?: number;
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
    pose_model?: string;
    pose_weights_hash?: string;
    partition_hash?: string;
    input_resolution?: { width: number; height: number };
    patch_labels?: string[];
    source_repository?: string;
    pose_repository?: string;
    privacy_input?: string;
    postprocessing?: string;
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
      patches: {
        patch_index: number;
        component?: string;
        score_change: number;
      }[];
    };
  }[];
  intervals: { start_time: number; end_time: number }[];
  timeline?: {
    timestamp: number;
    start_time: number;
    end_time: number;
    score: number;
    seizure_detected: boolean;
  }[];
  events?: {
    start_time: number;
    end_time: number;
    peak_score: number;
    peak_timestamp: number;
  }[];
  summary?: {
    peak_score: number;
    potential_event_detected: boolean;
    event_count: number;
    threshold: number;
  };
  recording_probability_available: false;
  privacy?: {
    method: "face-detection-and-full-frame-blur";
    model_input: "full-frame-blurred video";
    face_detection_coverage: number;
    quality_flags: string[];
    review_required: boolean;
    audio_policy?: string;
  };
  visualization?: {
    available: boolean;
    media_type: "video/mp4";
    audio_included: false;
    privacy_method: string;
    overlay: {
      skeleton: boolean;
      model_score: boolean;
      event_markers: boolean;
    };
    frontend_overlay?: {
      model_score: boolean;
      event_markers: boolean;
    };
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
  return uploadJson<{ job: DetectionJob }>(
    "/api/video-detection/jobs",
    data,
    progress,
  );
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

export const getDetectionVisualization = (id: string, signal?: AbortSignal) =>
  getBlob(
    `/api/video-detection/jobs/${encodeURIComponent(id)}/visualization`,
    signal,
  );
