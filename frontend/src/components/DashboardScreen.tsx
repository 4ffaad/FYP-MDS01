"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { deleteSession, getSessions, toDisplayStatus } from "@/lib/api";
import type { DisplayStatus, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { SessionGroup } from "./SessionRecordings";

const ACTIVE_SESSION_STATUSES = new Set(["queued", "validating", "deidentifying", "preprocessing", "inference", "explaining"]);

/** Render session cards and live processing state. */
export function DashboardScreen() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [filter, setFilter] = useState<"all" | DisplayStatus>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Fetch sessions and preserve abort behavior when the page is left. */
  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const nextSessions = await getSessions(signal);
      setSessions(nextSessions);
      setError(null);
    } catch (refreshError) {
      if (refreshError instanceof DOMException && refreshError.name === "AbortError") return;
      setError(refreshError instanceof Error ? refreshError.message : "The dashboard could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  const removeSession = useCallback(async (sessionId: string) => {
    if (!window.confirm("Delete this analysis session and its results? This cannot be undone.")) return;
    try {
      await deleteSession(sessionId);
      setSessions((current) => current.filter((session) => session.sessionId !== sessionId));
    } catch (deleteError: unknown) {
      setError(deleteError instanceof Error ? deleteError.message : "The session could not be deleted.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const initialLoad = window.setTimeout(() => void refresh(controller.signal), 0);
    return () => { controller.abort(); window.clearTimeout(initialLoad); };
  }, [refresh]);

  const hasActiveSessions = sessions.some((session) => ACTIVE_SESSION_STATUSES.has(session.status));
  useEffect(() => {
    if (!hasActiveSessions) return;
    const controller = new AbortController();
    const timer = window.setInterval(() => void refresh(controller.signal), 2000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [hasActiveSessions, refresh]);

  const visibleSessions = useMemo(
    () => filter === "all" ? sessions : sessions.filter((session) => toDisplayStatus(session.status) === filter),
    [filter, sessions],
  );
  const recordingCount = sessions.reduce((total, session) => total + session.recordings.length, 0);

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <div className="flex flex-col justify-between gap-6 border-b border-rule pb-7 sm:flex-row sm:items-end">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1 className="mt-3 text-[clamp(2rem,4vw,3.15rem)] font-semibold leading-[1.06] tracking-[-0.05em] text-ink">Analysis dashboard</h1>
            <p className="mt-4 max-w-xl text-[0.94rem] leading-6 text-ink-muted">Every upload is one session. Its recordings stay together so status, timing, and results are easy to follow.</p>
          </div>
          <Link className="button-primary shrink-0" href="/upload"><Icon name="upload" className="size-4" />New analysis</Link>
        </div>

        <div className="flex flex-col justify-between gap-4 border-b border-rule py-5 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3 text-sm text-ink-muted"><span className="font-semibold text-ink">{sessions.length}</span> {sessions.length === 1 ? "session" : "sessions"}<span className="text-ink-faint">·</span><span>{recordingCount} {recordingCount === 1 ? "recording" : "recordings"}</span>{hasActiveSessions && <span className="inline-flex items-center gap-1.5 text-xs text-ink-faint"><span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Updates automatically</span>}</div>
          <label className="flex items-center gap-2 text-xs text-ink-muted" htmlFor="status-filter"><span>Filter</span><select className="min-h-9 rounded-md border border-rule-strong bg-surface px-3 text-xs font-semibold text-ink outline-none transition focus:border-teal" id="status-filter" value={filter} onChange={(event) => setFilter(event.target.value as "all" | DisplayStatus)}><option value="all">All statuses</option><option value="queued">Queued</option><option value="processing">Processing</option><option value="complete">Complete</option><option value="partial">Partial · review</option><option value="failed">Needs review</option></select></label>
        </div>

        {error && <div className="mt-6 flex items-start justify-between gap-4 rounded-lg border border-red/30 bg-red-soft px-4 py-3 text-sm text-red" role="alert"><span className="flex gap-2"><Icon name="alert" className="mt-0.5 size-4 shrink-0" />{error}</span><button className="text-xs font-bold underline underline-offset-4" type="button" onClick={() => { setLoading(true); void refresh(); }}>Try again</button></div>}

        {loading ? <LoadingRows /> : visibleSessions.length === 0 ? <EmptyDashboard filtered={filter !== "all"} /> : <div className="mt-6 space-y-5">{visibleSessions.map((session) => <SessionGroup key={session.sessionId} session={session} onDelete={removeSession} />)}</div>}
      </div>
    </div>
  );
}

function LoadingRows() {
  return <div className="mt-6 space-y-3" aria-label="Loading sessions"><div className="h-28 animate-pulse rounded-lg border border-rule bg-surface" /><div className="h-28 animate-pulse rounded-lg border border-rule bg-surface" /></div>;
}

function EmptyDashboard({ filtered }: { filtered: boolean }) {
  return <div className="mt-8 panel px-6 py-14 text-center"><div className="mx-auto grid size-10 place-items-center rounded-md bg-teal-soft text-teal"><Icon name={filtered ? "list" : "upload"} className="size-5" /></div><h2 className="mt-5 text-lg font-bold tracking-[-0.02em]">{filtered ? "No sessions match this filter." : "No analyses submitted yet."}</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">{filtered ? "Choose another status to see more sessions." : "Start with an EEG recording. Its session and recording results will appear here."}</p>{!filtered && <Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" href="/upload">Submit an EEG recording <Icon name="arrow" className="size-4" /></Link>}</div>;
}
