# Implementation reality digest — round 1

## Findings

- **A lightweight first prototype is feasible with MediaPipe plus OpenCV.**
  Google documents decoding video frames through OpenCV and running Pose
  Landmarker or Face Detector in video mode. This supplies a small Python
  integration surface for a proof of concept; it does not supply the
  de-identification policy, threat model, or action classifier. (Publisher:
  Google AI Edge; documentation accessed 2026-08-26; confidence: high; class:
  implementation reality.)
  Sources:
  - https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python
  - https://developers.google.com/edge/mediapipe/solutions/vision/face_detector/python

- **MMPose is appropriate when model choice and extensibility matter more than
  dependency weight.** The official API supports video input and configurable
  2D/3D models. It should be isolated behind an inference adapter so the
  privacy/storage pipeline does not depend on one pose library. (Publisher:
  OpenMMLab; documentation accessed 2026-08-26; confidence: high; class:
  implementation reality.)
  Source: https://github.com/open-mmlab/mmpose/blob/main/docs/en/user_guides/inference.md

- **A learned anonymizer should be deferred until a dataset and attacks are
  available.** The research methods cited in the landscape digest train and
  evaluate against utility and privacy tasks. Without patient-video action
  labels and identity/attribute attack data, MDS01 could not credibly tune or
  validate such a transform; it would be an unreviewed model contract.
  (Publishers: Computer Vision Foundation; 2018–2023; accessed 2026-08-26;
  confidence: medium; class: implementation risk.)
  Sources:
  - https://openaccess.thecvf.com/content_ECCV_2018/html/Zhongzheng_Ren_Learning_to_Anonymize_ECCV_2018_paper.html
  - https://openaccess.thecvf.com/content/CVPR2022/html/Dave_SPAct_Self-Supervised_Privacy_Preservation_for_Action_Recognition_CVPR_2022_paper.html

- **Tooling does not remove the need for output inspection.** FFmpeg can
  select streams and disable metadata copying, while MediaPipe/OpenCV or
  MMPose can produce derived frames or landmarks. The pipeline still needs
  tests that inspect output streams, metadata, face coverage, missing-frame
  behavior, and whether retained pose data can support simple re-identification
  attacks. (Publishers: FFmpeg project, Google AI Edge, OpenMMLab; accessed
  2026-08-26; confidence: high; class: implementation reality.)
  Sources:
  - https://www.ffmpeg.org/ffmpeg.html
  - https://developers.google.com/edge/mediapipe/solutions/vision/face_detector/python
  - https://github.com/open-mmlab/mmpose/blob/main/docs/en/user_guides/inference.md

## Recommendation

Start with a **pose-only research pipeline** behind an adapter, using MediaPipe
for the first bounded prototype unless the project already needs MMPose’s model
zoo or 3D/custom configuration. Store normalized keypoints and action
intervals, not patient video, as the initial retained artifact. Add a separate
redacted-video mode only if reviewers need visual evidence; make it
audio-free, metadata-scrubbed, and subject to full-frame/multi-person coverage
tests.

Treat both outputs as research data, not anonymous data, until a documented
attack evaluation supports a stronger claim.

## Leads and gaps

- Need a small consented/synthetic video fixture set with controlled identity,
  background, occlusion, camera, and action variation.
- Need an action taxonomy and target output contract before choosing a model.
- Need an evaluation harness for action utility, face/person re-identification,
  attribute inference, linkage across clips, and temporal consistency.
- Need a decision on whether audio is always removed or separately analyzed.
