---
title: 'technical research: Privacy-preserving patient video de-identification for MDS01'
type: 'technical'
topic: 'Privacy-preserving patient video de-identification for MDS01'
decision: 'Choose an initial patient-video representation and integration approach that preserves required action-analysis utility while minimizing identity leakage.'
source: 'native web run'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-08-26'
updated: '2026-08-26'
---

# Technical research: Privacy-preserving patient video de-identification for MDS01

## Executive summary

Adopt a **pose-only research pipeline first**, behind an inference adapter, and
retain normalized keypoints plus action intervals rather than patient video.
Use MediaPipe Pose Landmarker for the first bounded prototype because its
official video-mode API is small and directly compatible with Python frame
decoding [7]. Keep MMPose as the alternative when the project needs a larger
model zoo, explicit 2D/3D selection, or custom checkpoints [9].

Treat face-blurred video as an optional **review derivative**, not the default
de-identified artifact. Blurring addresses visible faces, but video
identifiability is contextual and includes linkability and other direct or
indirect cues [1]. Face obfuscation can also affect action-recognition utility,
so the transformed representation needs its own utility evaluation [2].

Pose data reduces raw-pixel exposure but is not automatically anonymous:
published work demonstrates re-identification and sensitive-attribute leakage
from skeleton trajectories, including body and motion cues [3][4]. The
retained pose output must therefore be treated as research data and tested
against identity, attribute, and linkage attacks before any stronger privacy
claim.

Defer a learned spatio-temporal anonymizer. SPAct and STPrivacy show that
learned transforms can optimize the action/privacy trade-off and that complete
video-level attacks matter, but using that path in MDS01 requires local action
labels, privacy/identity attack data, retraining, and a reviewed model
contract [5][6]. A first release should establish the data contract and
evaluation harness before taking on that model risk.

## 1. Landscape and maturity

The relevant approaches fall into three practical tiers:

1. **Pixel redaction:** face detection followed by blur, masking, or another
   visual replacement. It is easy to explain and supports human review, but
   the privacy boundary must also cover audio, subtitles, metadata, background
   text, clothing, and other linkable cues. The ICO explicitly treats video as
   qualitative/unstructured data requiring context-specific assessment and
   recommends considering blurring/masking and audio treatment as possible
   measures, not universal guarantees [1].
2. **Derived motion representation:** extract body landmarks or skeleton
   trajectories and delete the RGB frames. This is the strongest practical
   minimization option when the product only needs movement/action analysis,
   but skeleton data can retain identity and sensitive attributes [3][4].
3. **Learned privacy-preserving video models:** train an anonymizer jointly or
   adversarially with action and privacy tasks. SPAct and STPrivacy demonstrate
   the research direction; STPrivacy specifically addresses temporal/video-level
   privacy rather than only frame-level obfuscation [5][6]. This is a later
   research track for MDS01, not a safe off-the-shelf privacy switch.

The evidence does not support calling any candidate “anonymous” by default.
The right claim is a documented risk-reduction profile whose residual
identifiability is tested in the intended release context [1].

## 2. Integration and architecture

The official tooling supports the shape MDS01 needs:

- MediaPipe Pose Landmarker accepts decoded video frames with monotonically
  increasing timestamps and returns pose landmarks in video mode [7].
- MediaPipe Face Detector has the same frame/timestamp pattern, making it
  suitable for a redacted-preview branch [8].
- MMPose provides configurable video inference through a unified Python
  inferencer and supports model aliases, configuration files, and checkpoints
  [9].
- FFmpeg supports explicit stream mapping, disabling audio/subtitle/data
  streams, and controlling metadata copying [10].

Integrate video as a separate asset linked to the existing session, not as
fields added to the EEG recording contract:

    Session
    ├── EEG recordings → existing EEG pipeline
    └── Video assets
        → encrypted draft upload
        → container/stream validation
        → remove audio, subtitles, and metadata
        → pose extraction and/or face redaction
        → action analysis
        → safe result JSON
        → retain only policy-approved derivative

The new video path should reuse the existing encrypted upload-draft boundary,
session-scoped private storage, BackgroundTasks scheduling, safe public
serialization, and cleanup policy. The new code should add a video processing
service and adapter boundary without coupling the EEG H5 runtime to computer
vision dependencies.

## 3. Implementation reality

MediaPipe plus OpenCV is the smallest credible first prototype: Google
documents OpenCV frame decoding and video-mode pose/face inference [7][8].
MMPose is the stronger configurable alternative, but its broader model and
PyTorch surface should be isolated behind the same adapter interface [9].
FFmpeg should own stream selection and metadata handling, followed by output
inspection tests rather than trusting command flags [10].

A learned anonymizer should wait until MDS01 has a consented or synthetic
fixture set, an action taxonomy, and explicit attack tasks. The research
literature evaluates utility and privacy together; it does not turn a generic
face-blur or pose extractor into a validated anonymizer [5][6][11].

Minimum evaluation before retaining a derivative:

- action classification or event-detection utility on transformed data;
- face/person re-identification;
- sensitive-attribute inference;
- cross-clip linkage of the same subject;
- temporal consistency and missed-detection rate;
- audio, subtitle, metadata, background-text, and multi-person coverage;
- human review of representative failures.

## Cross-dimension insights

- The product decision is really **human visual review versus machine motion
  analysis**. Pose-only is the better first retained artifact when machine
  analysis is sufficient; redacted video is justified only when reviewers need
  visual context.
- Privacy processing must be treated as a sequence, not a single blur step:
  remove non-video streams and metadata, derive the minimum representation,
  run attack/utility checks, then delete the original and transient frames.
- Temporal identity leakage is a first-class risk. A method that looks private
  frame by frame can still expose a subject through a whole clip [6].
- The architecture should make privacy profiles explicit so the project can
  compare pose-only and redacted-video without changing session ownership,
  storage boundaries, or public ID rules.

## Recommendations

1. **Choose pose-only as the first implementation target** and retain only
   normalized keypoints, confidence values, timestamps, and action intervals.
   Bind this to the future video specification and architecture spine.
2. **Add redacted-video as a second, opt-in profile** only if human review
   requires it. Remove audio/subtitles and scrub metadata; use face detection
   with temporal coverage checks; label the result as research-only.
3. **Create a VideoAsset/VideoRecording child of a session** with its own
   status, privacy profile, derived artifact reference, action results, and
   bounded preview policy. Keep raw paths and original names private.
4. **Introduce a VideoInferenceAdapter** so MediaPipe can serve the first
   prototype and MMPose or a learned model can be evaluated later without
   changing storage, API, or retention code.
5. **Make privacy evaluation part of the acceptance contract**, not a later
   research note. No derivative should be described as anonymous until the
   documented attack suite and human failure review support that claim.

## Open questions

- What actions or clinical events must the system recognize?
- Is human review of a video required, or are action intervals/keypoints enough?
- Is audio ever needed for the intended task? If not, remove it unconditionally.
- Will one video contain multiple patients or staff, and must all people be
  redacted/tracked?
- What resolution, duration, frame rate, and upload limits are acceptable?
- What consented or synthetic data can be used for action and privacy tests?
- Which privacy attackers and release audiences define the threat model?
- Should video and EEG be time-synchronized, and if so, what safe public
  representation exposes alignment?

## Source appendix

| Ref | Claim/finding supported | Publisher | Publication date | Accessed | Confidence |
| --- | --- | --- | --- | --- | --- |
| [1] | Contextual identifiability, linkability, and video-specific anonymisation measures | [UK Information Commissioner’s Office](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/how-do-we-ensure-anonymisation-is-effective/) | Undated current guidance | 2026-08-26 | High |
| [2] | Face obfuscation can affect video action-recognition utility | [Computer Vision Foundation](https://openaccess.thecvf.com/content/CVPR2021W/TCV/html/Tomei_Estimating_and_Fixing_the_Effect_of_Face_Obfuscation_in_Video_CVPRW_2021_paper.html) | 2021-06 | 2026-08-26 | Medium |
| [3] | Skeleton trajectories can leak identity and sensitive attributes | [arXiv](https://arxiv.org/abs/2111.15129) | 2021-11 | 2026-08-26 | Medium |
| [4] | Body proportions and motion style are privacy-relevant skeleton cues | [Computer Vision Foundation](https://openaccess.thecvf.com/content/ICCV2025/papers/Carr_Privacy-centric_Deep_Motion_Retargeting_for_Anonymization_of_Skeleton-Based_Motion_Visualization_ICCV2025_paper.pdf) | 2025-10 | 2026-08-26 | Medium |
| [5] | Learned anonymization can optimize action utility against privacy tasks | [Computer Vision Foundation](https://openaccess.thecvf.com/content/CVPR2022/html/Dave_SPAct_Self-Supervised_Privacy_Preservation_for_Action_Recognition_CVPR2022_paper.html) | 2022-06 | 2026-08-26 | High |
| [6] | Temporal/video-level privacy attacks matter beyond frame-level handling | [Computer Vision Foundation](https://openaccess.thecvf.com/content/ICCV2023/html/Li_STPrivacy_Spatio-Temporal_Privacy-Preserving_Action_Recognition_ICCV2023_paper.html) | 2023-10 | 2026-08-26 | High |
| [7] | MediaPipe Pose Landmarker video-mode frame inference | [Google AI Edge](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python) | Current documentation | 2026-08-26 | High |
| [8] | MediaPipe Face Detector video-mode frame inference | [Google AI Edge](https://developers.google.com/edge/mediapipe/solutions/vision/face_detector/python) | Current documentation | 2026-08-26 | High |
| [9] | MMPose configurable image/video inference | [OpenMMLab](https://github.com/open-mmlab/mmpose/blob/main/docs/en/user_guides/inference.md) | Current documentation | 2026-08-26 | High |
| [10] | FFmpeg stream and metadata controls | [FFmpeg project](https://www.ffmpeg.org/ffmpeg.html) | Current documentation | 2026-08-26 | High |
| [11] | Learned face anonymization is task-specific and requires evaluation | [Computer Vision Foundation](https://openaccess.thecvf.com/content_ECCV_2018/html/Zhongzheng_Ren_Learning_to_Anonymize_ECCV_2018_paper.html) | 2018-09 | 2026-08-26 | Medium |

## Staleness map

Generated from the claims ledger with the technical-pack freshness windows:
version/compatibility claims re-check monthly, ecosystem claims every six
months, landscape claims yearly, and pattern claims every two years. Current
tool compatibility should be re-checked first. The mechanical map reports 7 of
11 claims outside their freshness window; that flags refresh priority rather
than invalidating the historical evidence. Re-check dates from this run are:

- privacy guidance: 2027-08-01;
- patterns: 2023-06-01, 2025-10-01;
- privacy attack evidence: 2023-11-01, 2027-10-01;
- landscape: 2023-06-01;
- version compatibility: 2026-08-01, 2026-09-01, 2026-09-01, 2026-08-01;
- implementation risk: 2020-09-01.

The earliest scheduled re-check is 2020-09-01 for the historical learned-face
anonymization evidence; refresh this research before making a production
privacy claim.
