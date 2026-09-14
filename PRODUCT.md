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

- EEG follows `privacy → model` with metadata scrubbing and optional signal
  obfuscation before research-only model review.
- Video follows `privacy → model` with face redaction before VSViG visual
  inference; detection playback is muted and privacy playback retains audio
  only in the encrypted owner-only output.
- A unified upload may contain one or both modalities. Missing modalities are
  skipped and reported; the workflows remain independent internally.
- Results are research-only and never a diagnosis or treatment recommendation.
- Accounts, owner filtering, encrypted storage, acknowledgement states, and
  existing privacy warnings remain mandatory.

## Brand Commitments

The product name is MDS01. The interface is light-only, evidence-led, calm,
and direct. Apple Liquid Glass is inspiration for material and motion, not an
official web design system; the existing MDS01 blue accent, system sans, and
Hugeicons wrapper remain the visual foundation.

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
