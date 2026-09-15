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
import { Progress } from "@/components/ui/progress";

const ACTIVE_SESSION_STATUSES = new Set([
  "queued",
  "validating",
  "deidentifying",
  "preprocessing",
  "inference",
  "explaining",
]);
const POLL_INTERVAL_MS = 4000;

/** Render one session’s timestamp, processing summary, and complete recording list. */
export function SessionDetailScreen({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  const removeSession = async (id: string) => {
    try {
      await deleteSession(id);
      router.push("/dashboard");
    } catch (deleteError: unknown) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The session could not be deleted.",
      );
      throw deleteError;
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    let timer: number | undefined;
    const load = async () => {
      if (document.hidden) {
        timer = window.setTimeout(() => void load(), POLL_INTERVAL_MS);
        return;
      }
      let shouldPoll = false;
      try {
        const nextSession = await getSession(sessionId, controller.signal);
        if (!mounted) return;
        setSession(nextSession);
        setError(null);
        shouldPoll = ACTIVE_SESSION_STATUSES.has(nextSession.status);
      } catch (loadError: unknown) {
        if (
          loadError instanceof DOMException &&
          loadError.name === "AbortError"
        )
          return;
        if (mounted)
          setError(
            loadError instanceof Error
              ? loadError.message
              : "The session could not be loaded.",
          );
      } finally {
        if (mounted && shouldPoll && !controller.signal.aborted)
          timer = window.setTimeout(() => void load(), POLL_INTERVAL_MS);
      }
    };
    void load();
    return () => {
      mounted = false;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [sessionId]);

  if (error) return <SessionError message={error} />;
  if (!session)
    return (
      <div className="page-frame">
        <div
          className="h-64 animate-pulse rounded-lg border border-rule bg-surface"
          aria-label="Loading session"
        />
      </div>
    );

  const failedCount = session.recordings.filter(
    (recording) => recording.status === "failed",
  ).length;
  const completedCount = session.recordings.filter(
    (recording) => recording.status === "inferred",
  ).length;
  const completedRecordings = session.recordings.filter(
    (recording) => recording.status === "inferred",
  );
  const alertRecordings = completedRecordings.filter(
    (recording) => recording.modelAlertWindowCount > 0,
  );
  const development = completedRecordings.some(
    (recording) => recording.scoreType === "development_score",
  );
  const calibrated = completedRecordings.some(
    (recording) => recording.scoreType === "calibrated_probability",
  );
  const alertLabel = development
    ? "development flags"
    : calibrated
      ? "model alerts"
      : "research flags";
  const alertToneClass =
    development || !calibrated
      ? "border-amber/30 bg-amber-soft font-semibold text-amber"
      : "border-red/20 bg-red-soft font-semibold text-red";
  const analysisReady =
    !ACTIVE_SESSION_STATUSES.has(session.status) &&
    session.progress.finishedRecordings >= session.progress.totalRecordings;
  const visibleModelFlagCount = analysisReady ? alertRecordings.length : null;
  const alertTimes = alertRecordings.flatMap((recording) =>
    recording.alertIntervals.map(
      (interval) =>
        formatOffset(interval.startSeconds) +
        "-" +
        formatOffset(interval.endSeconds),
    ),
  );

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link
          className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
          href="/dashboard"
        >
          <Icon name="back" className="size-4" />
          Back to VEEG analysis
        </Link>

        <section
          className="mt-5 panel overflow-hidden"
          aria-labelledby="session-heading"
        >
          <div className="flex flex-col justify-between gap-5 px-5 py-6 sm:flex-row sm:items-start sm:px-7">
            <div>
              <h1
                id="session-heading"
                className="text-2xl font-semibold tracking-[-0.03em] text-ink"
              >
                Analysis session
              </h1>
              <p className="mt-2 font-mono text-sm text-ink-muted">
                {session.sessionId}
              </p>
              <p className="mt-3 text-sm text-ink-muted">
                Submitted {formatSubmittedAt(session.createdAt)}{" "}
                <span className="mx-1 text-rule-strong">·</span>{" "}
                {session.privacyMethod.label}
              </p>
              {analysisReady && alertTimes.length > 0 && (
                <p className="mt-2 text-xs text-ink-muted">
                  Alert times:{" "}
                  <span className="font-mono text-ink">
                    {alertTimes.slice(0, 6).join(", ")}
                    {alertTimes.length > 6
                      ? ` +${alertTimes.length - 6} more`
                      : ""}
                  </span>
                </p>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <StatusBadge status={toDisplayStatus(session.status)} />
              <DeleteSessionButton session={session} onDelete={removeSession} />
            </div>
          </div>
          <div className="grid border-t border-rule bg-surface-soft sm:grid-cols-4">
            <Summary
              label="Recordings"
              value={String(session.recordings.length)}
            />
            <Summary label="Completed" value={String(completedCount)} />
            <Summary label="Needs review" value={String(failedCount)} />
            <Summary
              label={
                development
                  ? "Development flags"
                  : calibrated
                    ? "Model alerts"
                    : "Research flags"
              }
              value={
                visibleModelFlagCount === null
                  ? "—"
                  : String(visibleModelFlagCount)
              }
            />
          </div>
          <ProgressSummary session={session} />
          <p
            className={`border-t px-5 py-3 text-xs leading-5 sm:px-7 ${visibleModelFlagCount !== null && visibleModelFlagCount > 0 ? alertToneClass : "border-rule text-ink-muted"}`}
          >
            {!analysisReady
              ? "Results will be summarized after all recordings finish processing."
              : visibleModelFlagCount !== null && visibleModelFlagCount > 0
                ? `${visibleModelFlagCount} recording${visibleModelFlagCount === 1 ? "" : "s"} contain ${alertLabel}.`
                : `No ${alertLabel} were found.`}
          </p>
          {session.currentStage && (
            <p className="border-t border-rule px-5 py-3 text-xs text-ink-muted sm:px-7">
              Current stage:{" "}
              <span className="font-semibold text-ink">
                {session.currentStage}
              </span>
            </p>
          )}
        </section>

        <section
          className="mt-6 panel overflow-hidden"
          aria-labelledby="recordings-heading"
        >
          <div className="border-b border-rule px-5 py-5 sm:px-7">
            <h2
              id="recordings-heading"
              className="text-base font-bold tracking-[-0.015em]"
            >
              Recordings in this session
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              Open a completed recording to review its prediction. Display
              numbers are sequential privacy-safe labels and may differ from
              source dataset numbering.
            </p>
          </div>
          {session.recordings.length > 0 ? (
            <SessionRecordings session={session} />
          ) : (
            <p className="px-5 py-6 text-sm text-ink-muted sm:px-7">
              No recordings were extracted from this upload.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-rule px-5 py-4 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
      <p className="text-xs font-bold uppercase tracking-[0.1em] text-ink-muted">
        {label}
      </p>
      <p className="mt-1 font-mono text-xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function ProgressSummary({ session }: { session: Session }) {
  const { progress } = session;
  const label =
    progress.totalRecordings === 0
      ? "Preparing recording list"
      : `${progress.finishedRecordings} of ${progress.totalRecordings} recordings processed`;
  return (
    <div className="border-t border-rule px-5 py-4 sm:px-7">
      <div className="flex items-center justify-between gap-4 text-xs">
        <span className="font-semibold text-ink">Processing progress</span>
        <span className="font-mono text-ink-muted">{progress.percent}%</span>
      </div>
      <Progress
        value={progress.percent}
        className="mt-2 h-2 bg-surface-muted [&_[data-slot=progress-indicator]]:rounded-full [&_[data-slot=progress-indicator]]:bg-teal"
        aria-label="Session processing progress"
      />
      <p className="mt-2 text-xs text-ink-muted">
        {label}
        {progress.failedRecordings > 0 &&
          ` · ${progress.failedRecordings} need review`}
      </p>
    </div>
  );
}

/** Format a recording-relative time offset for alert summaries. */
function formatOffset(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function SessionError({ message }: { message: string }) {
  return (
    <div className="page-frame">
      <div
        className="max-w-xl rounded-lg border border-red/30 bg-red-soft px-5 py-6"
        role="alert"
      >
        <Icon name="alert" className="size-5 text-red" />
        <h1 className="mt-4 text-xl font-bold text-ink">Session unavailable</h1>
        <p className="mt-2 text-sm leading-6 text-red">{message}</p>
        <Link
          className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4"
          href="/dashboard"
        >
          Return to VEEG analysis <Icon name="arrow" className="size-4" />
        </Link>
      </div>
    </div>
  );
}
