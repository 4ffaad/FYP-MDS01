"use client";

import Link from "next/link";
import { MotionConfig, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { deletePatientProfile, getCase, getPatientProfile } from "@/lib/api";
import type { CaseDetail, PatientProfileDetail } from "@/lib/types";
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
import { CaseStatusBadge } from "./CaseStatusBadge";

type CaseDetailScreenProps = {
  caseId: string;
  videoRejectedCount?: number;
  videoUnconfirmedCount?: number;
};

export function CaseDetailScreen(props: CaseDetailScreenProps) {
  return <CaseDetailScreenContent key={props.caseId} {...props} />;
}

function CaseDetailScreenContent({
  caseId,
  videoRejectedCount = 0,
  videoUnconfirmedCount = 0,
}: CaseDetailScreenProps) {
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [patientProfileLoad, setPatientProfileLoad] =
    useState<PatientProfileLoad | null>(null);
  const currentProfileLoad = profileLoadForCase(caseId, patientProfileLoad);
  const patientProfile = currentProfileLoad?.profile ?? null;
  const profileError = currentProfileLoad?.error ?? null;
  const caseIdRef = useRef(caseId);
  const caseLifecycleRef = useRef({ caseId, active: true });
  const [error, setError] = useState<string | null>(null);
  const [profileActionError, setProfileActionError] = useState<string | null>(
    null,
  );

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

  useEffect(() => {
    caseIdRef.current = caseId;
    const lifecycle = { caseId, active: true };
    caseLifecycleRef.current = lifecycle;
    return () => {
      lifecycle.active = false;
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
            error: "The patient report details are unavailable.",
          });
        }
      });
    return () => controller.abort();
  }, [caseId]);

  async function removePatientProfile() {
    if (
      !window.confirm(
        "Delete the encrypted patient details and any retained source document for this case?",
      )
    )
      return;
    const lifecycle = caseLifecycleRef.current;
    setProfileActionError(null);
    try {
      await deletePatientProfile(caseId);
      if (!isCurrentCase(caseId, lifecycle)) return;
      setPatientProfileLoad({ caseId, profile: null, error: null });
      setProfileActionError(null);
    } catch {
      if (!isCurrentCase(caseId, lifecycle)) return;
      setPatientProfileLoad({
        caseId,
        profile: patientProfile,
        error: "The patient report details could not be deleted.",
      });
      setProfileActionError("The patient report details could not be deleted.");
    }
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

  const caseReference = `Case ${caseData.caseId.slice(-8)}`;
  const displayName = patientDisplayName(
    patientProfile,
    caseData.patientName,
    caseReference,
  );
  const report = reportDetails(patientProfile);

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
            href="/dashboard"
            className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline underline-offset-4"
          >
            <Icon name="back" className="size-4" />
            Back to Workspace
          </Link>
          <header className="mt-6 border-b border-rule pb-7">
            <p className="eyebrow">Patient review</p>
            <h1 className="mt-3 break-words text-[clamp(2rem,5vw,3rem)] font-semibold tracking-[-0.05em] text-ink">
              {displayName}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">
              Report details and independent EEG and video review history.
            </p>
            <div className="mt-5 flex flex-wrap gap-2 text-xs font-medium text-ink-muted">
              {displayName !== caseReference && (
                <span className="rounded-full bg-surface-soft px-3 py-1.5">
                  {caseReference}
                </span>
              )}
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
            className="panel mt-6 overflow-hidden"
            aria-labelledby="patient-report-heading"
          >
            <div className="border-b border-rule px-5 py-5 sm:px-7">
              <div>
                <p className="eyebrow">Patient report · owner-only</p>
                <h2
                  id="patient-report-heading"
                  className="mt-2 text-lg font-bold"
                >
                  Report overview
                </h2>
                <p className="mt-1 text-sm leading-6 text-ink-muted">
                  {patientProfile
                    ? "Report fields were extracted on this device from the selected Word document and saved to this patient review."
                    : "Patient report details are unavailable. The Word document is read during patient-folder intake."}
                </p>
                <p className="mt-2 max-w-2xl text-xs leading-5 text-ink-muted">
                  The source document is not retained. All extracted fields
                  appear below in this owner-only view. The fields are copied
                  from the report automatically and may contain extraction
                  errors.
                </p>
              </div>
            </div>

            {patientProfile ? (
              <div className="space-y-5 p-5 sm:p-7">
                <div className="grid gap-4 md:grid-cols-2">
                  <ReportSection
                    title="Patient and recording details"
                    details={report.patientRecording}
                  />
                  <ReportSection
                    title="Interictal EEG"
                    details={report.interictal}
                  />
                  <ReportSection title="Ictal EEG" details={report.ictal} />
                  <ReportSection title="Attacks" details={report.attacks} />
                  <ReportSection
                    title="EEG findings"
                    details={report.findings}
                  />
                  <ReportSection
                    title="Conclusion"
                    details={report.conclusion}
                  />
                  <ReportSection
                    title="Report sign-off"
                    details={report.reportSignoff}
                  />
                  <ReportSection
                    title="Other extracted details"
                    details={report.other}
                  />
                </div>

                {!Object.values(report).some((details) => details.length) && (
                  <p className="rounded-xl bg-surface-soft p-4 text-sm leading-6 text-ink-muted shadow-hard-sm">
                    The report was saved, but no readable details were
                    extracted.
                  </p>
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
                    Automatically extracted from the report
                  </p>
                  <button
                    type="button"
                    onClick={() => void removePatientProfile()}
                    className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-rule px-3 py-2 text-xs font-semibold text-ink-muted hover:border-red/40 hover:text-red"
                  >
                    <Icon name="trash" className="size-4" />
                    Delete patient details
                  </button>
                </div>
              </div>
            ) : (
              <p className="px-5 py-5 text-sm text-ink-muted sm:px-7">
                {profileError ?? "Patient report details are not available."}
              </p>
            )}
          </section>

          <section
            className="panel mt-8 overflow-hidden"
            aria-labelledby="history-heading"
          >
            <div className="border-b border-rule px-5 py-5 sm:px-7">
              <h2 id="history-heading" className="text-base font-bold">
                Review timeline
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                EEG and video results for this patient.
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
                    <CaseStatusBadge status={analysis.status} />
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
                      <>
                        <Link
                          href={`/analysis?videoJobId=${encodeURIComponent(analysis.id)}`}
                          className="text-xs font-bold text-teal-dark underline underline-offset-4"
                        >
                          Open EEG/video sync review
                        </Link>
                        <Link
                          href={`/video-detection/${encodeURIComponent(analysis.id)}`}
                          className="text-xs font-bold text-teal-dark underline underline-offset-4"
                        >
                          Open VSViG player
                        </Link>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {!caseData.analyses.some(
                (analysis) => analysis.modality === "video",
              ) && (
                <p className="px-5 py-8 text-sm leading-6 text-ink-muted sm:px-7">
                  Upload a video analysis to add its protected player and model
                  scores here.
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
  if (!details.length) return null;
  return (
    <section className="rounded-2xl border border-rule bg-surface/70 p-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <ReportDetailsList details={details} className="mt-4 space-y-4" />
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
