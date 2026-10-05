# EEG and video inference, explained

This page explains what happens after an EEG or video is uploaded. The paths
use different models and do not combine their scores or automatically align
their timelines. All outputs are research-only.

## EEG: recording to window scores

1. The backend encrypts the upload and checks its contents.
2. It removes identifying file metadata, prepares the configured 18 EEG
   channels, and resamples to 256 samples per second.
3. It cuts the signal into four-second windows. A new window starts every two
   seconds, so adjacent windows overlap by two seconds. Each window has
   1,024 samples × 18 channels; the model input is float32 with shape
   (N, 1024, 18).
4. The selected runtime returns a score for each window. A configured threshold
   flags windows for review.
5. Scores and status are saved in the database. Temporary source and work files
   are cleaned up under the storage policy.

The progress panel records **Validate archive**, **Scrub EEG metadata**,
**Prepare model input**, **Run H5 model**, and **Generate explanation** by
recording. Each row shows its service state and elapsed time; archive validation
is session-wide. These labels are processing stages, not individual Python
function calls.

The **development stub** returns synthetic demo scores; it does not detect
seizures. The **H5 runtime** loads a local Keras model and checks its artifact
hash, reviewed contract, input shape, and output before inference. The current
candidate's scores are uncalibrated research scores, not probabilities.
When configured, SHAP shows relative input sensitivity by channel and time for
flagged windows. These values are not model weights or clinical causes.

## Video: pose plus blurred image patches

Video detection is independent of EEG:

1. The backend encrypts the uploaded clip and creates temporary normalized
   frames. Smaller clips can use experimental resizing in the local H5 profile;
   this does not add detail or make their scores equivalent to native
   1920×1080 video.
2. Lightweight OpenPose reads temporary source frames and looks for one
   complete body pose. If it cannot find all required keypoints, processing
   stops before VSViG.
3. OpenPose identifies the 15 patch locations from each transient source
   frame. The backend extracts the RGB patches, blurs each patch independently,
   and passes the patches with pose coordinates to VSViG. It does not pass the
   full source frame to VSViG.
4. The model samples 30 frames at 6 fps per window; the next window starts
   three sampled frames later. Its score is uncalibrated and thresholded for
   review.
5. The system retains encrypted predictions and an audio-free review video
   until the job expires. Face detections are checked against the tracked
   person's OpenPose head landmarks. A missing or mismatched face falls back
   to blurring the whole frame; the skeleton is drawn over that protected
   output. Source and temporary videos are removed after processing.

EEG upload creates the shared patient case first. Video submission starts as
soon as that case is accepted; EEG inference and video inference then run
independently. The video worker processes one clip at a time. If its queue is
full, the browser waits for an already accepted clip in the current intake and
retries only the clip the API explicitly rejected. If the queue is full because
of other work and no accepted clip can free capacity, that clip remains
unsubmitted and can be retried from the same intake.

An error such as incomplete_pose means no supported video result was produced.
It does not mean the video shows no seizure. Docker runs the backend and models;
see [local setup](setup.md), [architecture](architecture.md),
[backend details](backend.md), and the [video runbook](video-detection.md).

The video UI displays graph Grad-CAM for the strongest-scoring VSViG window.
The CAM is indexed by sampled time and the model's 15 keypoint patches, then
projected onto their 128×128 source regions. It is not pixel-level localization
or clinical causation. When EEG and video are displayed together, their
separate threshold intervals can be placed on one timeline using a manual
clock offset. That offset is unverified and the model scores are never added
together.
