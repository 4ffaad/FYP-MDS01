# Integration digest — round 1

## Findings

- **Video processing can be composed as a frame pipeline.** Google’s official
  MediaPipe Pose Landmarker supports image, video, and live-stream modes; for
  video it accepts decoded frames with monotonically increasing timestamps.
  MediaPipe’s Face Detector exposes the same video-mode pattern. This fits a
  server-side worker that decodes frames, runs a detector/landmarker, and
  writes a derived representation. (Publisher: Google AI Edge; documentation
  accessed 2026-08-26; confidence: high; class: integration/compatibility.)
  Sources:
  - https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python
  - https://developers.google.com/edge/mediapipe/solutions/vision/face_detector/python

- **MMPose is the more configurable pose-estimation option.** Its official
  inference guide supports images and videos through a unified Python
  inferencer and exposes model aliases, configuration paths, and checkpoint
  paths. This is useful if MDS01 needs explicit model selection, 2D/3D pose
  variants, or future custom training, but it introduces a larger PyTorch and
  model-management surface than a first MediaPipe prototype. (Publisher:
  OpenMMLab; documentation accessed 2026-08-26; confidence: high; class:
  integration/compatibility.)
  Source: https://github.com/open-mmlab/mmpose/blob/main/docs/en/user_guides/inference.md

- **FFmpeg should own stream selection and container metadata handling.** Its
  documentation supports explicit video-only mapping, disabling audio/subtitle
  streams, and disabling metadata copying. The processing contract should
  still inspect the output rather than trusting command flags, because the
  resulting file is the privacy boundary. (Publisher: FFmpeg project;
  documentation accessed 2026-08-26; confidence: high; class:
  integration/compatibility.)
  Source: https://www.ffmpeg.org/ffmpeg.html

## MDS01 integration implications

- Add a separate video asset/recording entity linked to the existing session;
  do not widen the EEG recording contract with video-specific fields.
- Reuse the existing encrypted upload-draft boundary, but validate video
  container, duration, frame rate, dimensions, stream count, and size before
  processing.
- Keep original video and decoded frames in private session-scoped storage,
  never PostgreSQL. Delete originals and transient frames after the derived
  artifact or aggregate result is committed.
- Add a video processing stage beside the EEG per-recording pipeline:
  validate → remove audio/metadata → derive redacted video or pose data →
  action analysis → write safe result JSON → retain only the policy-allowed
  artifact.
- Public endpoints should expose generated video-result IDs, status, action
  intervals, and privacy-profile metadata—not original filenames, paths, raw
  video, or unreviewed model scores.

## Leads and gaps

- Confirm whether Docker’s current research image can support the selected
  runtime without destabilizing the TensorFlow H5 path.
- Decide whether a future UI needs a redacted preview; if not, pose-only
  output can avoid retaining any viewable patient video.
- Define a bounded frame-sampling policy and failure behavior for missed
  detections before implementation.
