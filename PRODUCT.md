# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Clinical researchers and doctors reviewing EEG and patient-video evidence,
with project teammates running local demonstrations and technical checks.

## Product Purpose

MDS01 provides one research workspace for submitting EEG archives and patient
video, applying the appropriate privacy pipeline, reviewing model scores and
evidence, and generating a combined technical report. The first upload flow
must accept EEG, video, or both and clearly show which independent pipelines
are running.

## Positioning

MDS01 keeps privacy treatment, model evidence, and review limitations visible
in the same workflow. It does not hide modality-specific processing behind a
single unexplained result.

## Operating Context

The prototype runs locally for a small team. EEG and video may arrive as
separate files, while a future collection flow may submit both in one visit.
Researchers review flagged intervals and technical metadata; patient data and
model assets remain outside Git.

## Capabilities and Constraints

- EEG source files and complete readable signals are retained encrypted for
  owner-only review until case deletion. A separate de-identified model input
  follows the reviewed preprocessing contract; new analyses do not obfuscate
  the signal.
- Video detection follows `unblurred transient source → Lightweight OpenPose
  keypoints → 15 extracted RGB patches → VSViG inference`. Combined uploads
  can create an unblurred, audio-free owner reference copy independently of
  pose readiness and model inference only when the clinical-video review gate
  is enabled. Local setup enables owner-only review; an unconfigured backend
  keeps the gate off. Original and review files stay encrypted until case
  deletion. The separate video-privacy utility retains its own documented
  transformation policy.
- A unified upload may contain one or both modalities. Missing modalities are
  skipped and reported; the workflows remain independent internally.
- Results are research-only and never a diagnosis or treatment recommendation.
- Accounts, owner filtering, encrypted storage, acknowledgement states, and
  existing privacy warnings remain mandatory.
- A conservative, unique VEEG metadata match can synchronize reference video
  with the EEG source clock when reference review is enabled.
  Unmatched clips remain separate with their status; EEG and VSViG scores
  remain independent.
- Time-stamped human observations are stored separately from model flags and
  do not infer seizure onset or diagnosis. Current access is uploader-only;
  shared clinician roles are not implemented.

## Brand Commitments

The product name is MDS01. The interface is light-only, evidence-led, and
direct, with a neumorphic visual language: soft raised panels, inset controls,
rounded corners, neutral dividers, and the existing MDS01 blue accent. Keep the
system sans and Hugeicons wrapper. Visual weight must
support scanning and must not obscure research limitations or evidence status.

## Evidence on Hand

The repository contains synthetic browser fixtures and local development
configuration. Real patient EEG/video data, hospital annotations, VSViG
weights, and clinical claims are not repository assets and must not be
fabricated in the interface.

## Product Principles

1. Show the pipeline before the output.
2. Keep EEG and video independent while making the submission feel unified.
3. Make model evidence inspectable and limitations hard to miss.
4. Keep sensitive data owner-scoped and encrypted throughout its retention.

## Accessibility & Inclusion

Use semantic headings and labels, keyboard-accessible controls, visible focus,
readable contrast, reduced-motion support, and layouts that remain usable on
desktop and mobile.
