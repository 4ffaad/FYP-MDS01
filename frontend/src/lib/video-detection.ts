import { getJson, uploadBinary } from "./api";
import { prepareVideoUploadFile } from "./safe-upload";

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
  duration_seconds?: number;
  fps?: number;
  frame_count?: number;
  model: {
    model_name: string;
    model_version: string;
    weights_hash: string;
    preprocessing_version: string;
    contract_version?: string;
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
    pose_model_input?: string;
    model_input_adaptation?: "none" | "letterbox";
    adaptation_experimental?: boolean;
    source_resolution?: [number, number];
    model_resolution?: [number, number];
    model_input_padding_ltrb?: [number, number, number, number];
    face_detection_coverage: number;
    quality_flags: string[];
    review_required: boolean;
    audio_policy?: string;
  };
}

export interface VideoPreflightResult {
  accepted: boolean;
  width: number | null;
  height: number | null;
  required_width: 1920;
  required_height: 1080;
  adaptation?: "none" | "letterbox";
  experimental?: boolean;
  fps?: number;
  duration_seconds?: number;
  message: string;
}

export function preflightDetection(
  file: File,
  progress: (value: number) => void,
  signal?: AbortSignal,
) {
  const safeName = prepareVideoUploadFile(file);
  const extension = safeName.name.split(".").pop() ?? "";
  return uploadBinary<VideoPreflightResult>(
    "/api/video-detection/preflight",
    safeName,
    progress,
    signal,
    { "X-Video-Format": extension },
  );
}

export async function uploadDetection(
  file: File,
  progress: (value: number) => void,
  caseId?: string,
  signal?: AbortSignal,
) {
  const safeName = prepareVideoUploadFile(file);
  const extension = safeName.name.split(".").pop() ?? "";
  return uploadBinary<{ job: DetectionJob }>(
    "/api/video-detection/jobs",
    safeName,
    progress,
    signal,
    {
      "X-Video-Format": extension,
      ...(caseId ? { "X-Case-ID": caseId } : {}),
    },
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
