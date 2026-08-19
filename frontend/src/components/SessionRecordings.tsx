"use client";

import Link from "next/link";
import { useRef, useState, type PointerEvent } from "react";
import { formatSubmittedAt } from "@/lib/format";
import { toDisplayStatus } from "@/lib/api";
import type { Recording, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { StatusBadge } from "./StatusBadge";

const ACTIVE_SESSION_STATUSES = new Set(["queued", "validating", "deidentifying", "preprocessing", "inference", "explaining"]);

/** Render the recordings in one session without exposing submitted filenames. */
export function SessionRecordings({ session }: { session: Session }) {
  const datasetFindingsReady = isAnalysisReady(session);
 return (
   <div className="divide-y divide-rule">
      {session.recordings.map((recording) => <RecordingRow key={recording.recordId} recording={recording} total={session.recordings.length} showDatasetAnnotation={datasetFindingsReady} />)}
   </div>
 );
}

/** Render one recording and link only recordings with stored inference results. */
function RecordingRow({ recording, total, showDatasetAnnotation }: { recording: Recording; total: number; showDatasetAnnotation: boolean }) {
 const label = `Recording ${String(recording.sequenceIndex).padStart(2, "0")} of ${total}`;
  const hasDatasetSeizure = showDatasetAnnotation && (recording.referenceAnnotation?.intervals.length ?? 0) > 0;
  const content = (
    <>
      <div className="flex min-w-0 items-start gap-3">
        <span className={`grid size-8 shrink-0 place-items-center rounded-md ${hasDatasetSeizure ? "bg-red text-white" : "bg-surface-muted text-teal"}`} aria-hidden="true">
          <Icon name={hasDatasetSeizure ? "alert" : "file"} className="size-4" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{label}</p>
          <p className="mt-1 text-xs text-ink-muted">
            Privacy-safe display label
            {recording.durationSeconds !== null && <> <span className="mx-1 text-rule-strong">·</span> {formatDuration(recording.durationSeconds)}</>}
          </p>
          <ReferenceLabel recording={recording} showDatasetAnnotation={showDatasetAnnotation} />
        </div>
      </div>
      <div className="text-xs text-ink-muted">
        {recording.samplingRate ? `${recording.samplingRate} Hz` : "—"}
        {recording.channelCount ? ` · ${recording.channelCount} channels` : ""}
      </div>
      <div>
        <StatusBadge status={toDisplayStatus(recording.status)} />
        {recording.errorMessage && <p className="mt-1 max-w-sm text-xs leading-5 text-red">{recording.errorMessage}</p>}
      </div>
      <div className="text-teal-dark">
        {recording.status === "inferred" && <Icon name="chevron" className="size-4" aria-hidden="true" />}
      </div>
    </>
  );

  const rowClass = `grid gap-3 px-4 py-4 sm:grid-cols-[minmax(0,1.6fr)_minmax(110px,0.8fr)_minmax(150px,1fr)_20px] sm:items-center sm:px-5 ${hasDatasetSeizure ? "bg-red-soft/55" : ""}`;
  if (recording.status !== "inferred") return <div className={rowClass}>{content}</div>;
  return <Link className={`${rowClass} transition-colors ${hasDatasetSeizure ? "hover:bg-red-soft" : "hover:bg-teal-soft/20"}`} href={`/results/${encodeURIComponent(recording.recordId)}`} aria-label={`Open ${label} results`}>{content}</Link>;
}

/** Format duration without showing unnecessary decimal precision. */
function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${String(remainingSeconds).padStart(2, "0")}s`;
}

/** Render one dashboard session card that opens the full session detail page. */
export function SessionGroup({ session, onDelete }: { session: Session; onDelete?: (sessionId: string) => Promise<void> }) {
  const [swiped, setSwiped] = useState(false);
  const pointerStart = useRef<number | null>(null);
  const analysisReady = isAnalysisReady(session);
  const annotationSummary = analysisReady
    ? session.summary.datasetSeizureRecordings === null
      ? "Dataset annotations unavailable"
      : `${session.summary.datasetSeizureRecordings} with dataset seizure annotations`
    : "Dataset findings available after processing";
  const modelSummary = analysisReady
    ? session.summary.modelAlertRecordings === 0
      ? "No development score flags"
      : `${session.summary.modelAlertRecordings} with development score flags`
    : "Development scores pending";
  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === "touch") pointerStart.current = event.clientX;
  };
  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (pointerStart.current === null) return;
    setSwiped(pointerStart.current - event.clientX > 48);
    pointerStart.current = null;
  };

  return (
    <div className="relative touch-pan-y overflow-hidden rounded-[1.125rem]" onPointerDown={handlePointerDown} onPointerUp={handlePointerUp} onPointerCancel={() => { pointerStart.current = null; }}>
      {onDelete && <div className="absolute inset-y-0 right-0 flex w-24 items-center justify-center bg-red-soft"><button className="inline-flex flex-col items-center gap-1 text-xs font-bold text-red disabled:cursor-not-allowed disabled:text-ink-faint" type="button" disabled={ACTIVE_SESSION_STATUSES.has(session.status)} aria-label={`Delete session ${session.sessionId}`} title={ACTIVE_SESSION_STATUSES.has(session.status) ? "Available after processing finishes" : "Delete this session"} onClick={() => void onDelete(session.sessionId)}><Icon name="trash" className="size-5" />Delete</button></div>}
      <section className={`panel relative overflow-hidden transition-transform duration-200 ${swiped ? "-translate-x-24" : ""}`} aria-labelledby={`session-${session.sessionId}`}>
        <Link className="group block bg-surface-soft px-4 py-5 transition-colors hover:bg-surface sm:px-5 sm:py-6" href={`/sessions/${encodeURIComponent(session.sessionId)}`} aria-label={`Open session ${session.sessionId}`}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-faint">Analysis session</p>
              <h2 id={`session-${session.sessionId}`} className="mt-2 truncate font-mono text-sm font-bold text-ink">{session.sessionId}</h2>
              <p className="mt-2 text-xs text-ink-muted">Submitted {formatSubmittedAt(session.createdAt)} <span className="mx-1 text-rule-strong">·</span> {session.progress.finishedRecordings}/{session.progress.totalRecordings || "—"} processed</p>
            </div>
            <div className="flex items-center gap-3 sm:pt-1">
              <span className="text-xs text-ink-muted">{session.privacyMethod.label}</span>
              <StatusBadge status={toDisplayStatus(session.status)} />
              <Icon name="chevron" className="size-4 text-ink-faint transition-transform group-hover:translate-x-0.5" />
            </div>
          </div>
          <div className="mt-5 grid gap-4 border-t border-rule pt-4 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,0.8fr)] sm:gap-8">
            <div>
              <div className="flex items-center justify-between gap-3 text-xs"><span className="font-semibold text-ink">Processing progress</span><span className="font-mono text-ink-muted">{session.progress.percent}%</span></div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-label={`Processing progress for ${session.sessionId}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={session.progress.percent}><div className="h-full rounded-full bg-teal transition-[width] duration-500" style={{ width: `${session.progress.percent}%` }} /></div>
              <p className="mt-2 text-xs text-ink-muted">{session.progress.finishedRecordings} of {session.progress.totalRecordings || "—"} recordings processed</p>
            </div>
            <div className="text-xs leading-5 sm:border-l sm:border-rule sm:pl-6">
              <p className="font-semibold text-ink">Analysis summary</p>
              <p className={`mt-1 ${analysisReady && (session.summary.datasetSeizureRecordings ?? 0) > 0 ? "font-semibold text-red" : "text-ink-muted"}`}>{annotationSummary}</p>
              <p className="mt-1 text-ink-faint">{modelSummary}</p>
            </div>
          </div>
        </Link>
        {onDelete && <div className="flex items-center justify-between gap-4 border-t border-rule px-4 py-2.5 sm:px-5"><span className="text-[0.68rem] text-ink-faint">Open the session to review its recordings.</span><DeleteSessionButton session={session} onDelete={onDelete} /></div>}
      </section>
    </div>
  );
}

/** Return true only when all recordings have reached a terminal result. */
function isAnalysisReady(session: Session): boolean {
  return !ACTIVE_SESSION_STATUSES.has(session.status) && session.progress.finishedRecordings >= session.progress.totalRecordings;
}

/** Show whether a research dataset supplied a seizure label for the recording. */
function ReferenceLabel({ recording, showDatasetAnnotation }: { recording: Recording; showDatasetAnnotation: boolean }) {
  if (!showDatasetAnnotation) return <p className="mt-1 text-[0.68rem] text-ink-faint">Dataset reference pending until processing completes</p>;
 const modelLabel = recording.status !== "inferred"
    ? "Development score pending"
    : recording.modelAlertWindowCount > 0
      ? `Development score: activity flagged · ${recording.modelAlertWindowCount} ${recording.modelAlertWindowCount === 1 ? "window" : "windows"}`
      : "Development score: no activity flagged";
  const modelClass = recording.status !== "inferred" ? "text-ink-faint" : "text-ink-muted";
  if (!recording.referenceAnnotation) return <div className="mt-1 space-y-0.5"><p className="text-[0.68rem] text-ink-faint">Dataset annotation unavailable</p><p className={`text-[0.68rem] ${modelClass}`}>{modelLabel}</p></div>;
  const count = recording.referenceAnnotation.intervals.length;
  return <div className="mt-1 space-y-0.5"><p className={`text-[0.68rem] ${count > 0 ? "font-semibold text-red" : "text-ink-muted"}`}>{count > 0 ? `Dataset seizure annotation · ${count} ${count === 1 ? "interval" : "intervals"}` : "Dataset reference: no seizure"}</p><p className={`text-[0.68rem] ${modelClass}`}>{modelLabel}</p></div>;
}

/** Render a destructive session action with a safe processing guard. */
export function DeleteSessionButton({ session, onDelete }: { session: Session; onDelete: (sessionId: string) => Promise<void> }) {
  const active = ACTIVE_SESSION_STATUSES.has(session.status);
  return <button className="inline-flex min-h-9 items-center gap-1.5 text-xs font-bold text-red underline decoration-red/30 underline-offset-4 disabled:cursor-not-allowed disabled:text-ink-faint disabled:no-underline" type="button" disabled={active} title={active ? "Available after processing finishes" : "Delete this session"} onClick={() => void onDelete(session.sessionId)}><Icon name="trash" className="size-3.5" />{active ? "Delete after processing" : "Delete session"}</button>;
}
