"use client";
/* eslint-disable @next/next/no-img-element -- Authenticated protected media must bypass Next's optimizer/cache. */

import Link from "next/link";
import { MotionConfig, motion } from "motion/react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  ApiError,
  deletePatientProfile,
  getCase,
  getCaseSourceReportPdf,
  getPatientProfile,
  getVideoPrivacyJobs,
  saveCaseSourceReportPdf,
} from "@/lib/api";
import type {
  CaseDetail,
  PatientProfile,
  PatientProfileDetail,
  VideoPrivacyJob,
} from "@/lib/types";
import {
  profileLoadForCase,
  type PatientProfileLoad,
} from "@/lib/case-profile-state";
import {
  normalizedLabel,
  patientDisplayName,
  reportDetails,
} from "@/lib/patient-profile-privacy";
import { Icon } from "./Icon";
import { LoadingOrb } from "./LoadingOrb";
import { Status } from "./CasesScreen";

type LoadedVideoPrivacyJobs = {
  caseId: string;
  jobs: VideoPrivacyJob[];
  error: string | null;
};

type LoadedSourceReport = {
  caseId: string;
  url: string | null;
  loading: boolean;
  uploading: boolean;
  error: string | null;
  available?: boolean;
};

export function CaseDetailScreen({
  caseId,
  videoRejectedCount = 0,
  videoUnconfirmedCount = 0,
}: {
  caseId: string;
  videoRejectedCount?: number;
  videoUnconfirmedCount?: number;
}) {
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [patientProfileLoad, setPatientProfileLoad] =
    useState<PatientProfileLoad | null>(null);
  const currentProfileLoad = profileLoadForCase(caseId, patientProfileLoad);
  const patientProfile = currentProfileLoad?.profile ?? null;
  const profileError = currentProfileLoad?.error ?? null;
  const [videoPrivacyLoad, setVideoPrivacyLoad] =
    useState<LoadedVideoPrivacyJobs | null>(null);
  const [sourceReportLoad, setSourceReportLoad] =
    useState<LoadedSourceReport | null>(null);
  const reportPdfInput = useRef<HTMLInputElement>(null);
  const reportPdfUrl = useRef<string | null>(null);
  const reportPdfController = useRef<AbortController | null>(null);
  const caseIdRef = useRef(caseId);
  const caseLifecycleRef = useRef({ caseId, active: true });
  const [error, setError] = useState<string | null>(null);
  const [profileActionError, setProfileActionError] = useState<string | null>(
    null,
  );
  const currentSourceReport =
    sourceReportLoad?.caseId === caseId ? sourceReportLoad : null;
  const currentVideoPrivacy =
    videoPrivacyLoad?.caseId === caseId ? videoPrivacyLoad : null;

  function isCurrentCase(
    targetCaseId: string,
    lifecycle: { caseId: string; active: boolean },
  ): boolean {
    return (
      lifecycle.active &&
      lifecycle.caseId === targetCaseId &&
      caseLifecycleRef.current === lifecycle &&
      caseIdRef.current === targetCaseId
    );
  }

  function revokeReportPdfUrl() {
    const url = reportPdfUrl.current;
    reportPdfUrl.current = null;
    if (url) URL.revokeObjectURL(url);
  }

  function abortReportPdfLoad() {
    reportPdfController.current?.abort();
    reportPdfController.current = null;
  }

  useEffect(() => {
    caseIdRef.current = caseId;
    const lifecycle = { caseId, active: true };
    caseLifecycleRef.current = lifecycle;
    return () => {
      lifecycle.active = false;
      abortReportPdfLoad();
      revokeReportPdfUrl();
    };
  }, [caseId]);

  useEffect(() => {
    const controller = new AbortController();
    void getCase(caseId, controller.signal)
      .then(setCaseData)
      .catch((loadError) => {
        if (
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        )
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Case could not be loaded.",
          );
      });
    void getPatientProfile(caseId, controller.signal)
      .then((profile) => {
        if (controller.signal.aborted) return;
        setPatientProfileLoad({ caseId, profile, error: null });
      })
      .catch((loadError) => {
        if (
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        ) {
          setPatientProfileLoad({
            caseId,
            profile: null,
            error: "The reviewed patient profile is unavailable.",
          });
        }
      });
    return () => controller.abort();
  }, [caseId]);

  useEffect(() => {
    const controller = new AbortController();
    let retry: ReturnType<typeof setTimeout> | undefined;

    async function loadVideoPrivacyJobs() {
      try {
        const jobs = await getVideoPrivacyJobs(caseId, controller.signal);
        if (controller.signal.aborted) return;
        setVideoPrivacyLoad({ caseId, jobs, error: null });
        if (
          jobs.some(
            (job) =>
              !["ready", "needs_review", "failed", "expired"].includes(
                job.status,
              ),
          )
        ) {
          retry = setTimeout(() => void loadVideoPrivacyJobs(), 1500);
        }
      } catch (loadError) {
        if (
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        ) {
          setVideoPrivacyLoad({
            caseId,
            jobs: [],
            error: "Protected video evidence could not be loaded.",
          });
        }
      }
    }

    void loadVideoPrivacyJobs();
    return () => {
      controller.abort();
      if (retry) clearTimeout(retry);
    };
  }, [caseId]);

  async function removePatientProfile() {
    if (
      !window.confirm(
        "Delete the encrypted patient details and source-report PDF for this case?",
      )
    )
      return;
    const lifecycle = caseLifecycleRef.current;
    setProfileActionError(null);
    try {
      await deletePatientProfile(caseId);
      if (!isCurrentCase(caseId, lifecycle)) return;
      abortReportPdfLoad();
      revokeReportPdfUrl();
      setSourceReportLoad({
        caseId,
        url: null,
        loading: false,
        uploading: false,
        error: null,
        available: false,
      });
      setPatientProfileLoad({ caseId, profile: null, error: null });
      setProfileActionError(null);
    } catch {
      if (!isCurrentCase(caseId, lifecycle)) return;
      setPatientProfileLoad({
        caseId,
        profile: patientProfile,
        error: "The reviewed patient profile could not be deleted.",
      });
      setProfileActionError(
        "The reviewed patient profile could not be deleted.",
      );
    }
  }

  async function openSourceReport() {
    if (currentSourceReport?.url) return;
    abortReportPdfLoad();
    const lifecycle = caseLifecycleRef.current;
    const controller = new AbortController();
    reportPdfController.current = controller;
    setSourceReportLoad({
      caseId,
      url: null,
      loading: true,
      uploading: false,
      error: null,
    });
    try {
      const pdf = await getCaseSourceReportPdf(caseId, controller.signal);
      if (controller.signal.aborted || !isCurrentCase(caseId, lifecycle))
        return;
      if (pdf.type && pdf.type !== "application/pdf") {
        throw new Error("The stored source report is not a PDF.");
      }
      const url = URL.createObjectURL(pdf);
      reportPdfUrl.current = url;
      setSourceReportLoad({
        caseId,
        url,
        loading: false,
        uploading: false,
        error: null,
        available: true,
      });
    } catch (loadError) {
      if (controller.signal.aborted || !isCurrentCase(caseId, lifecycle))
        return;
      const message =
        loadError instanceof ApiError && loadError.status === 404
          ? "No PDF report is attached yet. Export the report as a PDF on this device, then attach it here."
          : "The original report PDF could not be opened.";
      setSourceReportLoad({
        caseId,
        url: null,
        loading: false,
        uploading: false,
        error: message,
        available: !(loadError instanceof ApiError && loadError.status === 404),
      });
    } finally {
      if (reportPdfController.current === controller)
        reportPdfController.current = null;
    }
  }

  async function attachSourceReport(event: ChangeEvent<HTMLInputElement>) {
    const pdf = event.target.files?.[0];
    event.target.value = "";
    if (!pdf) return;
    const lifecycle = caseLifecycleRef.current;
    abortReportPdfLoad();
    revokeReportPdfUrl();
    setSourceReportLoad({
      caseId,
      url: null,
      loading: false,
      uploading: true,
      error: null,
    });
    try {
      await saveCaseSourceReportPdf(caseId, pdf);
      if (!isCurrentCase(caseId, lifecycle)) return;
      setSourceReportLoad({
        caseId,
        url: null,
        loading: false,
        uploading: false,
        error: null,
        available: true,
      });
    } catch {
      if (!isCurrentCase(caseId, lifecycle)) return;
      setSourceReportLoad({
        caseId,
        url: null,
        loading: false,
        uploading: false,
        error: "The PDF report could not be attached to this case.",
      });
    }
  }

  function closeSourceReport() {
    abortReportPdfLoad();
    revokeReportPdfUrl();
    setSourceReportLoad({
      caseId,
      url: null,
      loading: false,
      uploading: false,
      error: null,
      available: true,
    });
  }

  if (error)
    return (
      <div className="page-frame">
        <div
          className="rounded-xl border border-red/30 bg-red-soft p-5 text-sm text-red"
          role="alert"
        >
          {error}
        </div>
      </div>
    );
  if (!caseData)
    return (
      <div className="page-frame">
        <div className="flex min-h-64 items-center justify-center px-5 py-12">
          <LoadingOrb
            label="Loading patient review…"
            state="searching"
            size={64}
          />
        </div>
      </div>
    );

  const displayName = patientDisplayName(patientProfile, caseData.patientName);
  const report = reportDetails(patientProfile);
  const reportSummary =
    report.conclusion[0] ?? report.technical[0] ?? report.events[0] ?? null;

  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame">
        <motion.main
          className="mx-auto max-w-6xl"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <Link
            href="/cases"
            className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline underline-offset-4"
          >
            <Icon name="back" className="size-4" />
            Back to Patient History
          </Link>
          <header className="mt-6 border-b border-rule pb-7">
            <p className="eyebrow">Patient review</p>
            <h1 className="mt-3 break-words text-[clamp(2rem,5vw,3rem)] font-semibold tracking-[-0.05em] text-ink">
              {displayName}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">
              Report overview and independent EEG and video review history.
              Internal case references are kept out of the screen.
            </p>
            <div className="mt-5 flex flex-wrap gap-2 text-xs font-medium text-ink-muted">
              <span className="rounded-full bg-surface-soft px-3 py-1.5">
                {caseData.analyses.length}{" "}
                {caseData.analyses.length === 1 ? "analysis" : "analyses"}
              </span>
              {Array.from(
                new Set(caseData.analyses.map((analysis) => analysis.modality)),
              ).map((modality) => (
                <span
                  key={modality}
                  className="rounded-full bg-surface-soft px-3 py-1.5"
                >
                  {modality === "eeg" ? "EEG" : "Video"} review
                </span>
              ))}
              <span className="rounded-full bg-surface-soft px-3 py-1.5">
                Updated{" "}
                {formatDate(
                  caseData.analyses.reduce(
                    (latest, analysis) =>
                      analysis.createdAt > latest ? analysis.createdAt : latest,
                    caseData.analyses[0]?.createdAt ?? new Date().toISOString(),
                  ),
                )}
              </span>
            </div>
          </header>

          {(videoRejectedCount > 0 || videoUnconfirmedCount > 0) && (
            <div
              className="mt-5 flex items-start gap-3 rounded-xl border border-red/30 bg-red-soft px-4 py-4 text-sm text-red"
              role="alert"
              aria-live="assertive"
            >
              <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
              <div>
                <h2 className="font-semibold">
                  Video processing needs attention
                </h2>
                {videoRejectedCount > 0 && (
                  <>
                    <p className="mt-1">
                      {videoRejectedCount} video{" "}
                      {videoRejectedCount === 1 ? "clip was" : "clips were"} not
                      accepted by VSViG.
                    </p>
                    <p className="mt-1">
                      No model result is available for those clips.
                    </p>
                  </>
                )}
                {videoUnconfirmedCount > 0 && (
                  <p className="mt-1">
                    {videoUnconfirmedCount} video{" "}
                    {videoUnconfirmedCount === 1 ? "job" : "jobs"} could not be
                    confirmed. Check the job rows below before relying on video
                    evidence.
                  </p>
                )}
                <p className="mt-2 text-xs leading-5">
                  Model output is research-only and is not a diagnosis.
                </p>
              </div>
            </div>
          )}

          <section
            className="panel glass-panel mt-6 overflow-hidden"
            aria-labelledby="patient-report-heading"
          >
            <div className="flex flex-col gap-4 border-b border-rule px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
              <div>
                <p className="eyebrow">Patient report · owner-only</p>
                <h2
                  id="patient-report-heading"
                  className="mt-2 text-lg font-bold"
                >
                  Report overview
                </h2>
                <p className="mt-1 text-sm leading-6 text-ink-muted">
                  Key report sections are grouped below. The original PDF
                  retains the full document for authorized review.
                </p>
                <p className="mt-2 max-w-2xl text-xs leading-5 text-ink-muted">
                  For a Word report, export a PDF on this device and attach it
                  here. The DOC/DOCX file is used for local text extraction; the
                  attached PDF is the only source-document file retained with
                  this case, encrypted and owner-scoped.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-rule bg-surface/80 px-4 text-sm font-semibold text-ink transition hover:border-teal/40 hover:text-teal-dark disabled:cursor-wait disabled:opacity-60"
                  onClick={() =>
                    currentSourceReport?.url
                      ? closeSourceReport()
                      : void openSourceReport()
                  }
                  disabled={
                    currentSourceReport?.loading ||
                    currentSourceReport?.uploading
                  }
                >
                  <Icon name="file" className="size-4" />
                  {currentSourceReport?.loading
                    ? "Opening PDF…"
                    : currentSourceReport?.url
                      ? "Close PDF viewer"
                      : "View original report PDF"}
                </button>
                <button
                  type="button"
                  className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-teal px-4 text-sm font-semibold text-white transition hover:bg-teal-dark disabled:cursor-wait disabled:opacity-60"
                  onClick={() => reportPdfInput.current?.click()}
                  disabled={currentSourceReport?.uploading}
                >
                  <Icon name="file" className="size-4" />
                  {currentSourceReport?.uploading
                    ? "Attaching PDF…"
                    : "Attach or replace PDF"}
                </button>
                <input
                  ref={reportPdfInput}
                  className="sr-only"
                  type="file"
                  accept="application/pdf,.pdf"
                  aria-label="Attach source report PDF"
                  onChange={(event) => void attachSourceReport(event)}
                />
              </div>
            </div>

            {patientProfile ? (
              <div className="space-y-5 p-5 sm:p-7">
                {reportSummary && (
                  <div className="rounded-2xl border border-teal/15 bg-teal-soft/40 p-4 sm:p-5">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-teal-dark">
                      Report at a glance · {reportSummary.label}
                    </p>
                    <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm leading-6 text-ink">
                      {reportSummary.value}
                    </p>
                  </div>
                )}

                <div className="grid gap-4 lg:grid-cols-3">
                  <ReportSection
                    title="Technical summary"
                    details={report.technical}
                  />
                  <ReportSection title="Events" details={report.events} />
                  <ReportSection
                    title="Conclusion"
                    details={report.conclusion}
                  />
                </div>

                {report.additional.length > 0 && (
                  <details className="rounded-xl border border-rule bg-surface/60 px-4 py-3">
                    <summary className="cursor-pointer text-sm font-semibold text-ink">
                      Other report details ({report.additional.length})
                    </summary>
                    <ReportDetailsList
                      details={report.additional}
                      className="mt-4 grid gap-4 sm:grid-cols-2"
                    />
                  </details>
                )}

                {!report.technical.length &&
                  !report.events.length &&
                  !report.conclusion.length &&
                  !report.additional.length && (
                    <p className="rounded-xl border border-dashed border-rule-strong p-4 text-sm leading-6 text-ink-muted">
                      No structured report sections are available. Attach or
                      open the original PDF to review the complete document.
                    </p>
                  )}

                <div className="border-t border-rule pt-4 text-xs leading-5 text-ink-muted">
                  {currentSourceReport?.uploading
                    ? "Uploading the PDF for encrypted, owner-scoped storage…"
                    : currentSourceReport?.error
                      ? currentSourceReport.error
                      : currentSourceReport?.url
                        ? "The original report is open below. It may include identifiers not shown in this summary."
                        : currentSourceReport?.available
                          ? "PDF report attached and stored encrypted for this case."
                          : "Address, phone, and record identifiers are intentionally omitted from this summary."}
                </div>
                {currentSourceReport?.url && (
                  <iframe
                    className="h-[min(78vh,900px)] w-full rounded-2xl border border-rule bg-white"
                    title="Original source report PDF"
                    src={currentSourceReport.url}
                    referrerPolicy="no-referrer"
                  />
                )}
                {profileActionError && (
                  <p
                    className="rounded-lg border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
                    role="alert"
                  >
                    {profileActionError}
                  </p>
                )}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-ink-muted">
                    Details reviewed {formatDate(patientProfile.reviewedAt)}
                  </p>
                  <button
                    type="button"
                    onClick={() => void removePatientProfile()}
                    className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-rule px-3 py-2 text-xs font-semibold text-ink-muted hover:border-red/40 hover:text-red"
                  >
                    <Icon name="trash" className="size-4" />
                    Delete patient record and PDF
                  </button>
                </div>
              </div>
            ) : (
              <p className="px-5 py-5 text-sm text-ink-muted sm:px-7">
                {profileError ?? "Patient report details are not available."}
              </p>
            )}
          </section>

          {(currentVideoPrivacy?.jobs.length || currentVideoPrivacy?.error) && (
            <section
              className="panel mt-6 overflow-hidden"
              aria-labelledby="video-privacy-heading"
            >
              <div className="border-b border-rule px-5 py-5 sm:px-7">
                <h2 id="video-privacy-heading" className="text-base font-bold">
                  Video de-identification and pose preview
                </h2>
                <p className="mt-1 text-sm leading-6 text-ink-muted">
                  Preview jobs stay separate from EEG inference. The full frame
                  is blurred before Lightweight OpenPose runs; no facial Action
                  Units or model prediction are generated.
                </p>
              </div>
              {currentVideoPrivacy.error ? (
                <p className="px-5 py-4 text-sm text-amber" role="status">
                  {currentVideoPrivacy.error}
                </p>
              ) : (
                <ul className="divide-y divide-rule">
                  {currentVideoPrivacy.jobs.map((job) => (
                    <li
                      key={job.jobId}
                      className="grid gap-4 px-5 py-5 sm:grid-cols-[minmax(0,1fr)_minmax(240px,0.8fr)] sm:px-7"
                    >
                      <div>
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <h3 className="text-sm font-bold">
                            {job.profileLabel} · privacy preview
                          </h3>
                          {job.status === "failed" ||
                          job.status === "expired" ? (
                            <span className="text-xs font-semibold text-amber">
                              {job.status === "failed"
                                ? "Unavailable"
                                : "Expired"}
                            </span>
                          ) : (
                            <Status
                              status={
                                job.status === "ready"
                                  ? "complete"
                                  : job.status === "needs_review"
                                    ? "needs_review"
                                    : "processing"
                              }
                            />
                          )}
                        </div>
                        <p className="mt-2 text-xs leading-5 text-ink-muted">
                          {job.profileDescription}
                        </p>
                        {job.poseEvidence && (
                          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                            <div>
                              <dt className="text-xs text-ink-muted">
                                Body-pose samples
                              </dt>
                              <dd className="mt-1 text-sm font-semibold text-ink">
                                {job.poseEvidence.detectedFrames} /{" "}
                                {job.poseEvidence.sampledFrames} sampled frames
                              </dd>
                            </div>
                            <div>
                              <dt className="text-xs text-ink-muted">
                                Facial Action Units
                              </dt>
                              <dd className="mt-1 text-sm font-semibold text-ink">
                                Not configured
                              </dd>
                            </div>
                          </dl>
                        )}
                        {job.poseEvidence?.trackingStopped && (
                          <p className="mt-3 text-xs leading-5 text-amber">
                            Pose overlay stopped after a missing or ambiguous
                            person frame; the preview never switches subjects
                            automatically.
                          </p>
                        )}
                        {job.error && (
                          <p className="mt-3 text-xs text-red" role="status">
                            {job.error}
                          </p>
                        )}
                      </div>
                      <div>
                        {job.previewUrl ? (
                          <img
                            className="aspect-video w-full rounded-lg border border-rule bg-black object-contain"
                            src={job.previewUrl}
                            alt="Full-frame-blurred video frame with body-keypoint overlay when detected"
                          />
                        ) : (
                          <div className="grid aspect-video place-items-center rounded-lg border border-rule bg-surface-soft px-4 text-center text-xs text-ink-muted">
                            Protected preview is being prepared.
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          <section
            className="panel mt-8 overflow-hidden"
            aria-labelledby="history-heading"
          >
            <div className="border-b border-rule px-5 py-5 sm:px-7">
              <h2 id="history-heading" className="text-base font-bold">
                Review timeline
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                EEG inference, VSViG analysis, and privacy previews are separate
                review paths.
              </p>
            </div>
            <div className="divide-y divide-rule">
              {caseData.analyses.map((analysis) => (
                <div
                  key={analysis.id}
                  className="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7"
                >
                  <div className="flex items-start gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-soft text-teal">
                      <Icon
                        name={analysis.modality === "eeg" ? "activity" : "file"}
                        className="size-5"
                      />
                    </span>
                    <div>
                      <p className="font-semibold text-ink">
                        {analysis.modality === "eeg"
                          ? "EEG analysis"
                          : "VSViG video analysis"}
                      </p>
                      <p className="mt-1 text-xs text-ink-muted">
                        {formatDate(analysis.createdAt)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 sm:text-right">
                    <Status status={analysis.status} />
                    <span className="text-xs text-ink-muted">
                      {analysis.reviewReady
                        ? "Review ready"
                        : "Still processing"}
                    </span>
                    {analysis.modality === "eeg" && (
                      <Link
                        href={`/sessions/${encodeURIComponent(analysis.id)}`}
                        className="text-xs font-bold text-teal-dark underline underline-offset-4"
                      >
                        Open EEG review
                      </Link>
                    )}
                    {analysis.modality === "video" && (
                      <Link
                        href={`/video-detection/${encodeURIComponent(analysis.id)}`}
                        className="text-xs font-bold text-teal-dark underline underline-offset-4"
                      >
                        Open VSViG player
                      </Link>
                    )}
                  </div>
                </div>
              ))}
              {!caseData.analyses.some(
                (analysis) => analysis.modality === "video",
              ) && (
                <p className="px-5 py-8 text-sm leading-6 text-ink-muted sm:px-7">
                  No VSViG player is attached to this case yet. A player appears
                  only after a video-detection job is admitted and submitted
                  under the current unmodified 1920×1080 contract. Privacy
                  previews are separate and do not create model scores.
                </p>
              )}
            </div>
          </section>
        </motion.main>
      </div>
    </MotionConfig>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
function ReportSection({
  title,
  details,
}: {
  title: string;
  details: PatientProfileDetail[];
}) {
  return (
    <section className="rounded-2xl border border-rule bg-surface/70 p-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {details.length ? (
        <ReportDetailsList details={details} className="mt-4 space-y-4" />
      ) : (
        <p className="mt-3 text-xs leading-5 text-ink-muted">
          Not available in the structured report details.
        </p>
      )}
    </section>
  );
}

function ReportDetailsList({
  details,
  className,
}: {
  details: PatientProfileDetail[];
  className: string;
}) {
  return (
    <dl className={className}>
      {details.map((detail, index) => (
        <div key={`${normalizedLabel(detail.label)}-${index}`}>
          <dt className="text-xs font-medium text-ink-muted">{detail.label}</dt>
          <dd className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-ink">
            {detail.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
