"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { deleteSession, getSession, toDisplayStatus } from "@/lib/api";
import { formatSubmittedAt } from "@/lib/format";
import type { Session } from "@/lib/types";
import { Icon } from "./Icon";
import { DeleteSessionButton, SessionRecordings } from "./SessionRecordings";
import { StatusBadge } from "./StatusBadge";

const ACTIVE_SESSION_STATUSES = new Set(["queued", "validating", "deidentifying", "preprocessing", "inference", "explaining"]);

/** Render one session’s timestamp, processing summary, and complete recording list. */
export function SessionDetailScreen({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  const removeSession = async (id: string) => {
    if (!window.confirm("Delete this analysis session and its results? This cannot be undone.")) return;
    try {
      await deleteSession(id);
      router.push("/dashboard");
    } catch (deleteError: unknown) {
      setError(deleteError instanceof Error ? deleteError.message : "The session could not be deleted.");
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    let timer: number | undefined;
    const load = async () => {
      try {
        const nextSession = await getSession(sessionId, controller.signal);
        if (!mounted) return;
        setSession(nextSession);
        setError(null);
        if (ACTIVE_SESSION_STATUSES.has(nextSession.status) && timer === undefined) timer = window.setInterval(() => void load(), 2000);
        if (!ACTIVE_SESSION_STATUSES.has(nextSession.status) && timer !== undefined) {
          window.clearInterval(timer);
          timer = undefined;
        }
      } catch (loadError: unknown) {
        if (loadError instanceof DOMException && loadError.name === "AbortError") return;
        if (mounted) setError(loadError instanceof Error ? loadError.message : "The session could not be loaded.");
      }
    };
    void load();
    return () => { mounted = false; controller.abort(); if (timer !== undefined) window.clearInterval(timer); };
  }, [sessionId]);

  if (error) return <SessionError message={error} />;
  if (!session) return <div className="page-frame"><div className="h-64 animate-pulse rounded-lg border border-rule bg-surface" aria-label="Loading session" /></div>;

 const failedCount = session.recordings.filter((recording) => recording.status === "failed").length;
 const completedCount = session.recordings.filter((recording) => recording.status === "inferred").length;
 const annotatedCount = session.recordings.filter((recording) => (recording.referenceAnnotation?.intervals.length ?? 0) > 0).length;
 const labelledCount = session.recordings.filter((recording) => recording.referenceAnnotation !== null).length;
 const datasetFindingsReady = !ACTIVE_SESSION_STATUSES.has(session.status) && session.progress.finishedRecordings >= session.progress.totalRecordings;
 const visibleDatasetCount = datasetFindingsReady && labelledCount > 0 ? annotatedCount : null;
  const visibleModelFlagCount = datasetFindingsReady ? session.summary.modelAlertRecordings : null;

 return (
   <div className="page-frame">
      <div className="animate-enter-up">
        <Link className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" href="/dashboard"><Icon name="back" className="size-4" />Back to dashboard</Link>

        <section className="mt-5 panel overflow-hidden" aria-labelledby="session-heading">
          <div className="flex flex-col justify-between gap-5 px-5 py-6 sm:flex-row sm:items-start sm:px-7">
            <div>
              <p className="eyebrow">Analysis session</p>
              <h1 id="session-heading" className="mt-2 font-mono text-2xl font-semibold tracking-[-0.04em] text-ink">{session.sessionId}</h1>
              <p className="mt-3 text-sm text-ink-muted">Submitted {formatSubmittedAt(session.createdAt)} <span className="mx-1 text-rule-strong">·</span> {session.privacyMethod.label}</p>
            </div>
            <div className="flex flex-wrap items-center gap-4"><StatusBadge status={toDisplayStatus(session.status)} /><DeleteSessionButton session={session} onDelete={removeSession} /></div>
          </div>
          <div className="grid border-t border-rule bg-surface-soft sm:grid-cols-5">
            <Summary label="Recordings" value={String(session.recordings.length)} />
            <Summary label="Completed" value={String(completedCount)} />
            <Summary label="Needs review" value={String(failedCount)} />
            <Summary label="Development flags" value={visibleModelFlagCount === null ? "—" : String(visibleModelFlagCount)} />
            <Summary label="Dataset seizures" value={visibleDatasetCount === null ? "—" : String(visibleDatasetCount)} />
         </div>
         <ProgressSummary session={session} />
          <p className={`border-t px-5 py-3 text-xs leading-5 sm:px-7 ${visibleDatasetCount !== null && visibleDatasetCount > 0 ? "border-red/20 bg-red-soft font-semibold text-red" : "border-rule text-ink-muted"}`}>{!datasetFindingsReady ? "Dataset seizure annotations will be summarized after all recordings finish processing." : visibleDatasetCount !== null && visibleDatasetCount > 0 ? `${visibleDatasetCount} recording${visibleDatasetCount === 1 ? "" : "s"} have supplied dataset seizure annotations.` : labelledCount > 0 ? "No supplied dataset seizure annotations were found in this session." : "Dataset seizure annotations were not available for this session."} Development score flags are shown separately and are not seizure accuracy.</p>
          {session.currentStage && <p className="border-t border-rule px-5 py-3 text-xs text-ink-muted sm:px-7">Current stage: <span className="font-semibold text-ink">{session.currentStage}</span></p>}
        </section>

        <section className="mt-6 panel overflow-hidden" aria-labelledby="recordings-heading">
          <div className="border-b border-rule px-5 py-5 sm:px-7"><h2 id="recordings-heading" className="text-base font-bold tracking-[-0.015em]">Recordings in this session</h2><p className="mt-1 text-sm text-ink-muted">Open a completed recording to review its prediction. Display numbers are sequential privacy-safe labels and may differ from source dataset numbering.</p></div>
          {session.recordings.length > 0 ? <SessionRecordings session={session} /> : <p className="px-5 py-6 text-sm text-ink-muted sm:px-7">No recordings were extracted from this upload.</p>}
        </section>
      </div>
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div className="border-b border-rule px-5 py-4 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"><p className="text-[0.68rem] font-bold uppercase tracking-[0.12em] text-ink-faint">{label}</p><p className="mt-1 font-mono text-xl font-semibold text-ink">{value}</p></div>;
}

function ProgressSummary({ session }: { session: Session }) {
  const { progress } = session;
  const label = progress.totalRecordings === 0
    ? "Preparing recording list"
    : `${progress.finishedRecordings} of ${progress.totalRecordings} recordings processed`;
  return <div className="border-t border-rule px-5 py-4 sm:px-7"><div className="flex items-center justify-between gap-4 text-xs"><span className="font-semibold text-ink">Processing progress</span><span className="font-mono text-ink-muted">{progress.percent}%</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-label="Session processing progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.percent}><div className="h-full rounded-full bg-teal transition-[width] duration-500" style={{ width: `${progress.percent}%` }} /></div><p className="mt-2 text-xs text-ink-muted">{label}{progress.failedRecordings > 0 && ` · ${progress.failedRecordings} need review`}</p></div>;
}

function SessionError({ message }: { message: string }) {
  return <div className="page-frame"><div className="max-w-xl rounded-lg border border-red/30 bg-red-soft px-5 py-6" role="alert"><Icon name="alert" className="size-5 text-red" /><h1 className="mt-4 text-xl font-bold text-ink">Session unavailable</h1><p className="mt-2 text-sm leading-6 text-red">{message}</p><Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4" href="/dashboard">Return to dashboard <Icon name="arrow" className="size-4" /></Link></div></div>;
}
