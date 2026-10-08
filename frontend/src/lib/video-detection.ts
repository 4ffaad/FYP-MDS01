import { apiMediaUrl, getJson, postJson, uploadBinary } from "./api";
import { prepareVideoUploadFile } from "./safe-upload";

export interface VideoEegSync {
  status: "pending" | "linked" | "unavailable" | "unmatched" | "ambiguous";
  record_id: string | null;
  session_id: string | null;
  eeg_source_start_seconds: number | null;
  video_duration_seconds: number | null;
  eeg_coverage_seconds: number | null;
  mapped_segments: Array<{
    video_start_seconds: number;
    video_end_seconds: number;
    eeg_source_start_seconds: number;
  }>;
}

/** Convert an EEG source-clock time through the validated clip/segment map. */
export function videoTimeForEegTime(
  segments: VideoEegSync["mapped_segments"] | undefined,
  eegSeconds: number,
): number | null {
  if (!segments || !Number.isFinite(eegSeconds)) return null;
  for (const segment of segments) {
    const segmentDuration =
      segment.video_end_seconds - segment.video_start_seconds;
    const eegEnd = segment.eeg_source_start_seconds + segmentDuration;
    if (
      Number.isFinite(segmentDuration) &&
      segmentDuration > 0 &&
      eegSeconds >= segment.eeg_source_start_seconds &&
      eegSeconds <= eegEnd
    ) {
      return (
        segment.video_start_seconds +
        eegSeconds -
        segment.eeg_source_start_seconds
      );
    }
  }
  return null;
}

/** Convert a protected clip time back to EEG source-clock time. */
export function eegTimeForVideoTime(
  segments: VideoEegSync["mapped_segments"] | undefined,
  videoSeconds: number,
): number | null {
  if (!segments || !Number.isFinite(videoSeconds)) return null;
  for (const segment of segments) {
    if (
      videoSeconds >= segment.video_start_seconds &&
      videoSeconds <= segment.video_end_seconds
    ) {
      return (
        segment.eeg_source_start_seconds +
        videoSeconds -
        segment.video_start_seconds
      );
    }
  }
  return null;
}

export interface DetectionJob {
  job_id: string;
  case_id: string | null;
  label: string;
  status: "queued" | "processing" | "ready" | "failed" | "expired";
  current_stage: string;
  duration_seconds: number;
  fps: number;
  blur_strength_percent: number;
  review_privacy_method?:
    | "unblurred-owner-source"
    | "legacy-face-blur"
    | "pose-region-patient-blur-with-full-frame-fallback"
    | "tracked-face-blur-with-full-frame-fallback";
  created_at: string;
  retention_expires_at: string | null;
  reference_only?: boolean;
  source_available?: boolean;
  retention_policy?: "until-deletion" | "legacy-expiry";
  video_available: boolean;
  error: string | null;
  sync?: VideoEegSync;
}

export function videoJobFailureMessage(
  status: "failed" | "expired",
  message: string | null,
): string {
  if (status === "expired") return "Video job expired. No result is available.";
  const unavailableMessage =
    "Video processing failed; no result was produced. The reason is not available here.";
  if (!message) return unavailableMessage;
  const normalized = message.toLocaleLowerCase("en-US");
  if (
    normalized.includes("face-redacted safely") ||
    normalized.includes("patient-blurred safely") ||
    normalized.includes("privacy")
  ) {
    return "The privacy transform could not be validated, so VSViG did not run and no video score was produced. Face redaction or the protected output did not pass its checks.";
  }
  if (
    normalized.includes("opening five-second pose check") &&
    normalized.includes("landmark")
  ) {
    return "No person track had all 15 VSViG-selected landmarks in every opening sample. Multiple people are supported; other OpenPose joints are not required.";
  }
  if (normalized.includes("landmark")) {
    return "Some sampled windows lacked one or more of the 15 VSViG-selected landmarks. Those windows remain unscored; other complete person tracks or windows may still have scores.";
  }
  if (normalized.includes("single patient") || normalized.includes("person")) {
    return "Pose extraction could not establish a stable person stream for a complete model window. Multiple people are supported and scored separately when their selected landmarks are visible.";
  }
  if (
    normalized.includes("readable avi") ||
    normalized.includes("five seconds")
  ) {
    return "The clip could not pass video input checks. Use a readable AVI, MP4, MOV, or WebM video that is at least five seconds long and has stable frame timing.";
  }
  if (normalized.includes("1920") && normalized.includes("1080")) {
    return "This clip does not meet the 1920×1080 input requirement. Use the matching original-resolution video; resizing cannot add detail.";
  }
  return unavailableMessage;
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
      method: "patch-occlusion" | "vsvig-graph-grad-cam";
      note: string;
      target_class?: "flagged" | "below_threshold";
      patches?: {
        patch_index: number;
        component?: string;
        score_change: number;
      }[];
      pose_samples?: {
        timestamp: number;
        points: {
          patch_index: number;
          x: number;
          y: number;
          confidence: number;
        }[];
      }[];
      gradcam_samples?: {
        timestamp: number;
        patches: { patch_index: number; relevance: number }[];
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
  subjects?: DetectionTrackResult[];
  recording_probability_available: false;
  privacy?: {
    method:
      | "unblurred-owner-source"
      | "pose-region-patient-blur-with-full-frame-fallback"
      | "tracked-face-blur-with-full-frame-fallback"
      | "face-detection-and-full-frame-blur";
    model_input:
      | "15 individually blurred RGB patches per sampled frame"
      | "15 unblurred RGB patches per sampled frame";
    blur_strength_percent?: number;
    pose_model_input?: string;
    model_input_adaptation?: "none" | "letterbox";
    adaptation_experimental?: boolean;
    source_resolution?: [number, number];
    model_resolution?: [number, number];
    model_input_padding_ltrb?: [number, number, number, number];
    face_detection_coverage?: number;
    face_blur_coverage?: number;
    patient_blur_coverage?: number;
    quality_flags: string[];
    overlay?: {
      skeleton: boolean;
      model_score: boolean;
      event_markers: boolean;
    };
    review_required: boolean;
    audio_policy?: string;
  };
  visualization?: {
    available: boolean;
    media_type: "video/mp4";
    audio_included: false;
    privacy_method:
      | "unblurred-owner-source-and-skeleton-overlay"
      | "pose-region-patient-blur-with-full-frame-fallback-and-skeleton-overlay"
      | "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay"
      | "face-blur-with-full-frame-fallback-and-skeleton-overlay";
    face_detection_coverage?: number;
    face_blur_coverage?: number;
    patient_blur_coverage?: number;
    full_frame_fallback_frames: number;
    quality_flags: string[];
  };
}

export interface DetectionTrackResult {
  subject_id: string;
  label: string;
  status: "scored" | "unscored";
  unavailable_reason:
    | "incomplete_pose"
    | "missing_pose"
    | "no_usable_windows"
    | null;
  unscored_windows: {
    start_time: number;
    end_time: number;
    reason: "incomplete_pose" | "missing_pose";
  }[];
  predictions: DetectionResult["predictions"];
  timeline?: DetectionResult["timeline"];
  intervals: DetectionResult["intervals"];
  events?: DetectionResult["events"];
  summary?: DetectionResult["summary"];
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
  pose_readiness?: {
    ready: boolean;
    checked_frames: number;
    required_frames: number;
    window_seconds: number;
    tracks_seen: number;
    usable_tracks: number;
    frames_without_person: number;
    frames_with_multiple_people: number;
    frames_with_tracking_break: number;
    frames_with_incomplete_pose: number;
    missing_landmarks: Record<string, number>;
  };
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
  blurStrengthPercent = 0,
  veegSync?: { sourceName: string; groupId: string },
  referenceOnly = false,
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
      ...(referenceOnly ? { "X-Video-Purpose": "reference" } : {}),
      "X-Model-Blur-Percent": String(blurStrengthPercent),
      ...(caseId ? { "X-Case-ID": caseId } : {}),
      ...(veegSync
        ? {
            "X-VEEG-Source-Name": encodeURIComponent(veegSync.sourceName),
            "X-VEEG-Source-Group": veegSync.groupId,
          }
        : {}),
    },
  );
}

export function finalizeVideoSyncGroup(
  caseId: string,
  groupId: string,
  expectedSourceNames: string[],
  signal?: AbortSignal,
) {
  return postJson<{
    group_id: string;
    status: VideoEegSync["status"];
    linked_jobs: number;
  }>(
    `/api/video-detection/cases/${encodeURIComponent(caseId)}/sync-groups/${encodeURIComponent(groupId)}/finalize`,
    { expected_source_names: expectedSourceNames },
    signal,
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
export const detectionVisualizationUrl = (id: string) =>
  apiMediaUrl(
    `/api/video-detection/jobs/${encodeURIComponent(id)}/visualization`,
  );
