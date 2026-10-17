# MDS01 Project Goal

**Last reviewed: 2026-10-17**

This document defines the project's intended outcome and scope. It is the
product goal, not a claim that every capability is complete. The implemented
system design is in [Project design](project-design.md). Verified behavior,
test evidence, and outstanding work are tracked in [`tasks/plan.md`](../tasks/plan.md)
and in the relevant technical guides linked from the [documentation index](README.md).

## Main goal

Develop a secure, privacy-preserving, and clinically useful EEG/VEEG
decision-support system that lets neurologists review EEG recordings alongside
synchronized patient videos, investigate potential seizure events, observe
patient movements, and review AI-generated findings through an interactive web
application.

The system should provide the essential review behavior of a clinical EEG
viewer while integrating seizure-detection models, synchronized video, event
annotations, and secure patient-data management. It supports neurologists; it
does not replace them or diagnose seizures autonomously.

## Core objectives

### 1. Clinical EEG visualization

Provide accurate EEG waveforms using established clinical viewing conventions:

- Open on a 12-second display window.
- Use the HUKM longitudinal bipolar montage, clinically appropriate channel
  ordering, and left/right/midline colors.
- Use the fixed HUKM reference profile for this prototype: 100 µV/cm, 30 mm/s,
  0.5–70 Hz, and 50 Hz notch where supported.
- Navigate the full recording with timestamps and event markers.
- Show model findings without modifying the original signal.

### 2. Synchronized EEG and video

Enable neurologists to review EEG and corresponding patient videos on a shared
timeline:

- Match HUKM EEG and video using verified timestamp metadata.
- Synchronize playback, pausing, seeking, and navigation.
- Display observed movements at the corresponding EEG time.
- Support observation of left-sided, right-sided, bilateral, and other
  seizure-related movements without inferring seizure origin from movement
  side alone.
- Let clinicians annotate and review events.
- Keep clinical video playback independent of AI video inference.

### 3. AI-assisted seizure detection

Use existing research models as supplementary evidence:

- Use the H5 EEG model to analyze recordings and flag potentially relevant
  windows.
- Show model scores, thresholds, and timestamps.
- Keep VSViG as a separate experimental video-inference workflow for compatible
  clips.
- Clearly distinguish research outputs from confirmed clinical findings or
  diagnoses.

Training a new seizure-detection model is outside this project's requirements.

### 4. Explainability and clinical interpretation

Make model findings traceable and useful to clinical review:

- Connect EEG flags to the corresponding waveform intervals.
- Link events to synchronized video when available.
- Present timestamps, annotations, scores, and processing limitations together.
- Allow clinicians to record movement observations.
- Distinguish clinician observations, imported clinical annotations, and
  AI-generated findings.

SHAP is not required for the current prototype. Explainability should prioritize
reviewable evidence over unsupported claims about why a model made a prediction.

### 5. Privacy and security

Protect sensitive recordings while allowing authorized clinical review:

- Encrypt retained recordings at rest and protect transfers in transit.
- Restrict patient-data access to authorized users.
- Provide secure authentication, authorization, and audit logging.
- Support controlled retention, download, and deletion.
- Preserve clinically necessary visual information when institutional
  authorization permits.
- Retain de-identification capabilities for research or data-sharing workflows
  that require them.

Privacy controls must protect confidentiality while preserving information
clinicians need to review an event.

### 6. Functional web prototype

Deliver an integrated web application using Next.js, FastAPI, and PostgreSQL.
Authorized users should be able to:

1. Upload and manage EEG/VEEG recordings.
2. View clinically readable EEG waveforms.
3. Navigate recordings and review event markers.
4. Watch synchronized patient video when available.
5. Examine AI-generated seizure flags.
6. Add and review clinical annotations.
7. Securely retain, retrieve, download, and delete recordings.
8. Run a separate experimental VSViG video demonstration.

## Expected outcome

The FYP prototype demonstrates three primary capabilities:

**A. EEG clinical review:** Accurate visualization of HUKM EEG recordings with
navigation, annotations, and AI-assisted flagging.

**B. VEEG clinical review:** Synchronized EEG/video playback for examining
patient movement alongside electrical brain activity, independent of whether
the video AI model can process the footage.

**C. Privacy-preserving decision support:** Secure management of sensitive
recordings with traceable AI outputs and clinically useful review evidence.

The separate VSViG demonstration uses compatible research data. Its output is
not presented as synchronized with HUKM EEG.

## Success criteria

The project succeeds when:

- EEG is accurately displayed using clinical visualization conventions.
- Confidently matched HUKM EEG and video can be reviewed synchronously.
- Clinicians can navigate events and observe patient behavior.
- EEG model findings are traceable to the signal that was processed.
- Reviewers can see what was flagged, when it was flagged, and what evidence is
  available.
- Patient recordings are protected by appropriate security controls.
- The local prototype workflow is reliable and tested.
- Technical documentation accurately describes implementation, tests, and
  limitations.

## Scope

**Primary focus:** EEG/VEEG clinical visualization, synchronization, privacy
preservation, and reviewable decision support.

**Supporting capabilities:** Existing EEG seizure inference and event
annotation.

**Experimental capability:** Independent VSViG video-seizure demonstration.

**Outside scope:** Autonomous diagnosis, guaranteed seizure-onset
lateralization, training a new seizure model, and complete hospital-grade
production deployment.

## Project vision

> Build a secure, explainable EEG/VEEG clinical review platform that combines
> accurate brain-signal visualization, synchronized patient video, and
> AI-assisted seizure analysis to help neurologists investigate seizure events
> while protecting sensitive patient information.
