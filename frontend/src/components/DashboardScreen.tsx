"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { deleteSession, getSessions, toDisplayStatus } from "@/lib/api";
import type { DisplayStatus, Session } from "@/lib/types";
import { Icon } from "./Icon";
import { SessionGroup } from "./SessionRecordings";
import { Button } from "@/components/ui/button";

const ACTIVE_SESSION_STATUSES = new Set([
  "queued",
  "validating",
  "deidentifying",
  "preprocessing",
  "inference",
  "explaining",
]);
const POLL_INTERVAL_MS = 4000;

/** Home for both modalities; detailed review stays in the existing workflow routes. */
export function DashboardScreen() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [filter, setFilter] = useState<"all" | DisplayStatus>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);
  const deletedSessionIds = useRef(new Set<string>());

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const requestNumber = ++latestRequest.current;
    try {
      const nextSessions = await getSessions(signal);
      if (signal?.aborted || requestNumber !== latestRequest.current) return;
      setSessions(
        nextSessions.filter(
          (session) => !deletedSessionIds.current.has(session.sessionId),
        ),
      );
      setError(null);
    } catch (refreshError) {
      if (
        refreshError instanceof DOMException &&
        refreshError.name === "AbortError"
      )
        return;
      if (requestNumber !== latestRequest.current) return;
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Your analyses could not be loaded.",
      );
    } finally {
      if (!signal?.aborted && requestNumber === latestRequest.current)
        setLoading(false);
    }
  }, []);

  const removeSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      deletedSessionIds.current.add(sessionId);
      latestRequest.current += 1;
      setSessions((current) =>
        current.filter((session) => session.sessionId !== sessionId),
      );
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The session could not be deleted.",
      );
      throw deleteError;
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const initialLoad = window.setTimeout(
      () => void refresh(controller.signal),
      0,
    );
    return () => {
      controller.abort();
      window.clearTimeout(initialLoad);
    };
  }, [refresh]);

  const hasActiveSessions = sessions.some((session) =>
    ACTIVE_SESSION_STATUSES.has(session.status),
  );
  useEffect(() => {
    if (!hasActiveSessions) return;
    const controller = new AbortController();
    let timer: number | undefined;
    let stopped = false;
    const poll = async () => {
      if (!document.hidden) await refresh(controller.signal);
      if (!stopped && !controller.signal.aborted)
        timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    };
    timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [hasActiveSessions, refresh]);

  const visibleSessions = useMemo(
    () =>
      filter === "all"
        ? sessions
        : sessions.filter(
            (session) => toDisplayStatus(session.status) === filter,
          ),
    [filter, sessions],
  );
  const recordingCount = sessions.reduce(
    (total, session) => total + session.recordings.length,
    0,
  );
  const completedCount = sessions.filter(
    (session) =>
      session.status === "completed" ||
      session.status === "completed_with_errors",
  ).length;

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <header className="glass-panel rounded-3xl border border-rule px-6 py-7 sm:px-8 sm:py-9">
          <div className="flex flex-col justify-between gap-7 lg:flex-row lg:items-end">
            <div className="max-w-2xl">
              <p className="eyebrow">MDS01 workspace</p>
              <h1 className="mt-3 text-[clamp(2.2rem,5vw,3.3rem)] font-semibold leading-[1.03] tracking-[-0.055em] text-ink">
                Analysis workspace
              </h1>
              <p className="mt-4 max-w-xl text-[0.98rem] leading-7 text-ink-muted">
                Keep EEG and patient-video review in one place. Each modality
                keeps its own privacy treatment, model, and evidence trail.
              </p>
            </div>
            <Button
              asChild
              size="lg"
              className="shrink-0 self-start lg:self-end"
            >
              <Link href="/upload">
                <Icon name="upload" className="size-4" />
                New analysis
              </Link>
            </Button>
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <Metric
              label="EEG sessions"
              value={sessions.length}
              detail="Owner-scoped"
              icon="activity"
            />
            <Metric
              label="Recordings"
              value={recordingCount}
              detail={`${completedCount} complete`}
              icon="file"
            />
            <Metric
              label="Review paths"
              value="2"
              detail="EEG + video"
              icon="shield"
            />
          </div>
        </header>

        <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.75fr)]">
          <section
            className="panel overflow-hidden"
            aria-labelledby="eeg-analysis-heading"
          >
            <div className="flex flex-col justify-between gap-4 border-b border-rule px-5 py-5 sm:flex-row sm:items-center sm:px-7">
              <div>
                <p className="eyebrow">Modality one</p>
                <h2
                  id="eeg-analysis-heading"
                  className="mt-1 text-lg font-bold"
                >
                  EEG analysis
                </h2>
                <p className="mt-1 text-sm text-ink-muted">
                  {sessions.length} EEG{" "}
                  {sessions.length === 1 ? "session" : "sessions"} · Window
                  scores, flagged intervals, and optional waveform review.
                </p>
              </div>
              <label
                className="flex items-center gap-2 text-xs text-ink-muted"
                htmlFor="status-filter"
              >
                <span>Status</span>
                <select
                  className="min-h-10 rounded-lg border border-rule-strong bg-surface px-3 text-xs font-semibold text-ink outline-none transition focus:border-teal focus:ring-3 focus:ring-teal/15"
                  id="status-filter"
                  value={filter}
                  onChange={(event) =>
                    setFilter(event.target.value as "all" | DisplayStatus)
                  }
                >
                  <option value="all">All statuses</option>
                  <option value="queued">Queued</option>
                  <option value="processing">Processing</option>
                  <option value="complete">Complete</option>
                  <option value="partial">Partial · review</option>
                  <option value="failed">Needs review</option>
                </select>
              </label>
            </div>
            {error && (
              <div
                className="mx-5 mt-5 flex items-start justify-between gap-4 rounded-xl border border-red/30 bg-red-soft px-4 py-3 text-sm text-red sm:mx-7"
                role="alert"
              >
                <span className="flex gap-2">
                  <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
                  {error}
                </span>
                <button
                  className="text-xs font-bold underline underline-offset-4"
                  type="button"
                  onClick={() => {
                    setLoading(true);
                    void refresh();
                  }}
                >
                  Try again
                </button>
              </div>
            )}
            {loading ? (
              <LoadingRows />
            ) : visibleSessions.length === 0 ? (
              <EmptyDashboard filtered={filter !== "all"} />
            ) : (
              <div className="space-y-5 px-5 py-5 sm:px-7">
                {visibleSessions.map((session) => (
                  <SessionGroup
                    key={session.sessionId}
                    session={session}
                    onDelete={removeSession}
                  />
                ))}
              </div>
            )}
          </section>

          <aside className="space-y-5">
            <WorkflowCard
              icon="activity"
              eyebrow="Modality two"
              title="Video detection"
              description="Face-redacted frames → VSViG scores → evidence intervals, with no processed video retained."
              href="/video-detection"
              action="Open video detection"
            />
          </aside>
        </div>
        <p className="mt-6 text-xs leading-5 text-ink-muted">
          Research only · model output is not a diagnosis · raw patient files
          remain outside the public workspace.
        </p>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: "activity" | "file" | "shield";
}) {
  return (
    <div className="rounded-2xl border border-rule bg-surface/70 px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-faint">
          {label}
        </span>
        <Icon name={icon} className="size-5 text-teal" />
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-[-0.04em] tabular-nums text-ink">
        {value}
      </p>
      <p className="mt-1 text-xs text-ink-muted">{detail}</p>
    </div>
  );
}

function WorkflowCard({
  icon,
  eyebrow,
  title,
  description,
  href,
  action,
}: {
  icon: "activity" | "shield";
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  action: string;
}) {
  return (
    <motion.section
      className="premium-card p-5 sm:p-6"
      whileHover={{ y: -3 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
    >
      <Icon name={icon} className="size-6 text-teal" weight="bold" />
      <p className="eyebrow mt-5">{eyebrow}</p>
      <h2 className="mt-1 text-lg font-bold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-ink-muted">{description}</p>
      <Link
        href={href}
        className="mt-5 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
      >
        {action}
        <Icon name="arrow" className="size-4" />
      </Link>
    </motion.section>
  );
}

function LoadingRows() {
  return (
    <div className="space-y-3 px-5 py-5 sm:px-7" aria-label="Loading sessions">
      <div className="h-28 animate-pulse rounded-xl border border-rule bg-surface" />
      <div className="h-28 animate-pulse rounded-xl border border-rule bg-surface" />
    </div>
  );
}

function EmptyDashboard({ filtered }: { filtered: boolean }) {
  return (
    <div className="px-5 py-16 sm:px-7 sm:py-24">
      <h3 className="text-lg font-semibold">
        {filtered
          ? "No EEG sessions match this status."
          : "No EEG analyses yet."}
      </h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-ink-muted">
        {filtered
          ? "Choose another status to see the rest of your EEG sessions."
          : "Start with EEG, video, or both from New analysis above."}
      </p>
      <Link
        className="mt-5 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4"
        href="/upload"
      >
        Upload data <Icon name="arrow" className="size-4" />
      </Link>
    </div>
  );
}
