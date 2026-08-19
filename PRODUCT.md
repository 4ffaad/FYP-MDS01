# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js App Router, TypeScript, and Tailwind CSS for the frontend; FastAPI
REST API for the backend.

## Users

The primary users are clinicians and clinical researchers who are moderately
comfortable with software but are not developers. They use the product at a
desktop clinical workstation, sometimes on a tablet, while under time
pressure.

Their job is to submit an EEG recording, understand its processing state,
review a seizure detection result, and evaluate the evidence behind that
result before deciding how much to trust it.

## Product Purpose

MDS01 is a clinical decision-support tool for privacy-preserving EEG seizure
detection. It lets a clinician upload an EEG recording, select a configurable
privacy method, follow the analysis job, and review a seizure prediction with
confidence and visual model evidence.

Success means the clinician can complete the workflow quickly, understand how
the patient data was handled, and evaluate the model output rather than
blindly accepting a verdict.

## Positioning

MDS01 combines privacy-method visibility with an inspectable seizure-detection
result. The product is positioned as decision support: it helps a clinician
evaluate an output and its evidence, and does not replace clinical judgment or
claim autonomous diagnosis.

## Operating Context

- The primary workflow is one focused screen per task: upload, monitor jobs,
  then review a result.
- Users need immediate clarity about queued, processing, and completed jobs.
- Completed jobs open a results view with the prediction first and the model
  explanation immediately available below or beside it.
- The frontend will initially use a stubbed REST fetch layer so the interface
  can be built independently of the final FastAPI response shape.

## Capabilities and Constraints

- `/upload` accepts an EEG file, a privacy-method choice, and one prominent
  submit action.
- The privacy-method selector must accept a configuration list; the initial
  the research modes are Control and Cancellable Signal Projection. They
  separate metadata-only handling from an experimental, shared EEG
  transformation and must not be presented as an anonymity guarantee.
- `/dashboard` shows submitted jobs with a generated safe recording label, submitted time, status,
  state icon, and state label. Users can submit another job without waiting.
- `/results/[jobId]` shows prediction, confidence, selected privacy method,
  and an attention-weight overlay component that accepts time-series data and
  attention weights.
- The interface is desktop-first and must remain functional on tablet.
- Status must never be communicated by color alone; icons and labels are
  required.
- Authentication is not implemented yet.
- The repository currently uses a deterministic development inference stub.
  Until a validated model and explanation method are supplied, all outputs
  must be labelled development-only and non-clinical.
- Patient-identifying values, original file paths, and unrestricted original
  files must not be exposed in public responses or UI.

## Brand Commitments

- Product name: MDS01.
- Voice is calm, precise, and reassuring without being promotional or
  consumer-oriented.
- Trust, privacy handling, evidence visibility, and clinical clarity are more
  important than decorative novelty.
- The interface must help users question and evaluate model output rather than
  encourage unquestioning acceptance.

## Evidence on Hand

- Existing FastAPI backend routes and privacy-safe session/recording data are
  available in `backend/app/`.
- Existing development preprocessing and deterministic stub inference are
  available in the repository.
- No validated clinical model, clinical performance evidence, testimonials,
  regulatory claims, or brand asset package has been supplied.

## Product Principles

1. Put the next clinical action and current job state in the first visual
   read.
2. Make privacy handling visible and understandable without exposing private
   data.
3. Show evidence beside the result so confidence is inspectable, not magical.
4. Use precise, calm communication and avoid claims the system cannot prove.
5. Keep the workflow focused: fewer decisions, clear progress, reversible
   review.

## Accessibility & Inclusion

- Design for desktop clinical workstations first and preserve usability on
  tablet widths.
- Meet WCAG AA contrast expectations for text and status indicators.
- Pair every status color with an icon and readable label.
- Keep keyboard focus visible, form labels explicit, and error messages
  actionable.
