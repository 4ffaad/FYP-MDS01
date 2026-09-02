"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { deleteSession, getSessions, toDisplayStatus } from "@/lib/api";
import type { DisplayStatus, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { SessionGroup } from "./SessionRecordings";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const ACTIVE_SESSION_STATUSES = new Set(["queued", "validating", "deidentifying", "preprocessing", "inference", "explaining"]);
const POLL_INTERVAL_MS = 4000;

/** Render session cards and live processing state. */
export function DashboardScreen() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [filter, setFilter] = useState<"all" | DisplayStatus>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);
  const deletedSessionIds = useRef(new Set<string>());

  /** Fetch sessions and preserve abort behavior when the page is left. */
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const requestNumber = ++latestRequest.current;
    try {
      const nextSessions = await getSessions(signal);
      if (signal?.aborted || requestNumber !== latestRequest.current) return;
      setSessions(nextSessions.filter((session) => !deletedSessionIds.current.has(session.sessionId)));
      setError(null);
    } catch (refreshError) {
      if (refreshError instanceof DOMException && refreshError.name === "AbortError") return;
      if (requestNumber !== latestRequest.current) return;
      setError(refreshError instanceof Error ? refreshError.message : "EEG analyses could not be loaded.");
    } finally {
      if (!signal?.aborted && requestNumber === latestRequest.current) setLoading(false);
    }
  }, []);

  const removeSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      deletedSessionIds.current.add(sessionId);
      latestRequest.current += 1;
      setSessions((current) => current.filter((session) => session.sessionId !== sessionId));
    } catch (deleteError: unknown) {
      setError(deleteError instanceof Error ? deleteError.message : "The session could not be deleted.");
      throw deleteError;
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
    let timer: number | undefined;
    let stopped = false;
    const poll = async () => {
      if (!document.hidden) await refresh(controller.signal);
      if (!stopped && !controller.signal.aborted) timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    };
    timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    return () => { stopped = true; controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [hasActiveSessions, refresh]);

  const visibleSessions = useMemo(
    () => filter === "all" ? sessions : sessions.filter((session) => toDisplayStatus(session.status) === filter),
    [filter, sessions],
  );
  const recordingCount = sessions.reduce((total, session) => total + session.recordings.length, 0);

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <header className="flex flex-col justify-between gap-6 border-b border-rule pb-7 sm:flex-row sm:items-end">
          <div className="max-w-2xl">
            <h1 id="eeg-analysis-heading" className="text-[clamp(2rem,4vw,2.5rem)] font-semibold leading-[1.08] tracking-[-0.035em] text-ink">EEG analysis</h1>
            <p className="mt-3 max-w-xl text-[0.94rem] leading-6 text-ink-muted">Upload an archive, follow its processing, and review the model output with the original session context.</p>
          </div>
          <Button asChild size="lg" className="shrink-0 self-start"><Link href="/upload"><Icon name="upload" className="size-4" />New EEG analysis</Link></Button>
        </header>

        <div className="mt-5 flex flex-col justify-between gap-4 border-b border-rule py-4 sm:flex-row sm:items-center">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-ink-muted"><span><span className="font-semibold tabular-nums text-ink">{sessions.length}</span> EEG {sessions.length === 1 ? "session" : "sessions"}</span><span className="text-rule-strong" aria-hidden="true">·</span><span><span className="font-semibold tabular-nums text-ink">{recordingCount}</span> {recordingCount === 1 ? "recording" : "recordings"}</span>{hasActiveSessions && <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted"><span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Updating automatically</span>}</div>
          <label className="flex items-center gap-2 text-xs text-ink-muted" htmlFor="status-filter"><span>Status</span><select className="min-h-10 rounded-lg border border-rule-strong bg-surface px-3 text-xs font-semibold text-ink outline-none transition focus:border-teal focus:ring-3 focus:ring-teal/15" id="status-filter" value={filter} onChange={(event) => setFilter(event.target.value as "all" | DisplayStatus)}><option value="all">All statuses</option><option value="queued">Queued</option><option value="processing">Processing</option><option value="complete">Complete</option><option value="partial">Partial · review</option><option value="failed">Needs review</option></select></label>
        </div>

        <aside className="mt-5 flex flex-col justify-between gap-3 border-b border-rule pb-5 sm:flex-row sm:items-center" aria-label="Separate video privacy workflow">
          <p className="flex items-start gap-2 text-sm leading-6 text-ink-muted"><Icon name="shield" className="mt-1 size-4 shrink-0 text-teal" weight="bold" /><span><span className="font-semibold text-ink">Video privacy is separate.</span> Protect a patient video without sending it through the EEG model.</span></p>
          <Link className="inline-flex min-h-10 shrink-0 items-center gap-2 text-sm font-semibold text-teal-dark underline decoration-teal/30 underline-offset-4 hover:decoration-teal" href="/video-privacy">Open video privacy <Icon name="arrow" className="size-4" /></Link>
        </aside>

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
  return <Card className="mt-8 panel px-6 py-14 text-center"><Icon name={filtered ? "list" : "activity"} className="mx-auto size-6 text-teal" /><h2 className="mt-4 text-lg font-bold tracking-[-0.02em]">{filtered ? "No EEG sessions match this status." : "No EEG analyses yet."}</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">{filtered ? "Choose another status to see the rest of your EEG sessions." : "Use New EEG analysis above to upload an archive and create a session."}</p></Card>;
}
