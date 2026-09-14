"use client";

import Link from "next/link";
import { useMemo, useRef, useState, type PointerEvent } from "react";
import { formatSubmittedAt } from "@/lib/format";
import { toDisplayStatus } from "@/lib/api";
import type { Recording, Session } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Icon } from "./Icon";
import { StatusBadge } from "./StatusBadge";

const ACTIVE_SESSION_STATUSES = new Set([
  "queued",
  "validating",
  "deidentifying",
  "preprocessing",
  "inference",
  "explaining",
]);

function isAnalysisReady(session: Session): boolean {
  return (
    !ACTIVE_SESSION_STATUSES.has(session.status) &&
    session.progress.finishedRecordings >= session.progress.totalRecordings
  );
}

/** Render the recordings in one session without exposing submitted filenames. */
export function SessionRecordings({ session }: { session: Session }) {
  const {
    processedRecordings,
    failedRecordings,
    completedRecordings,
    alertRecordings,
    alertCount,
    development,
    calibrated,
  } = useMemo(() => {
    const processed = session.recordings.filter(
      (recording) =>
        recording.status === "inferred" || recording.status === "failed",
    );
    const failed = processed.filter((recording) => recording.status === "failed");
    const completed = processed.filter(
      (recording) => recording.status === "inferred",
    );
    const alerts = completed.filter(
      (recording) => recording.modelAlertWindowCount > 0,
    );
    return {
      processedRecordings: processed,
      failedRecordings: failed,
      completedRecordings: completed,
      alertRecordings: alerts,
      alertCount: alerts.length,
      development: completed.some(
        (recording) => recording.scoreType === "development_score",
      ),
      calibrated: completed.some(
        (recording) => recording.scoreType === "calibrated_probability",
      ),
    };
  }, [session.recordings]);
  const alertLabel = development
    ? "Development flags"
    : calibrated
      ? "Model alerts"
      : "Research flags";
  const [filter, setFilter] = useState<RecordingFilter | null>(null);
  const activeFilter = filter ?? (alertCount > 0 ? "alerts" : "all");
  const visibleRecordings = useMemo(() => {
    if (activeFilter === "alerts") return alertRecordings;
    if (activeFilter === "review")
      return processedRecordings.filter(
        (recording) => recording.status === "failed",
      );
    return processedRecordings;
  }, [activeFilter, alertRecordings, processedRecordings]);
  const pendingCount = session.recordings.length - processedRecordings.length;
  return (
    <div>
      <div className="border-b border-rule bg-surface">
        <Tabs
          value={activeFilter}
          onValueChange={(value) => {
            if (value === "alerts" || value === "review" || value === "all")
              setFilter(value);
          }}
          className="!block"
        >
          <TabsList
            variant="line"
            className="w-full max-w-full justify-start gap-1 overflow-x-auto rounded-none px-4 py-3 sm:px-5"
          >
            <TabsTrigger
              value="alerts"
              className="h-9 flex-none rounded-full px-3 text-xs font-semibold data-[state=active]:bg-teal-soft data-[state=active]:text-teal-dark"
            >
              {alertLabel}{" "}
              <span className="font-mono tabular-nums">{alertCount}</span>
            </TabsTrigger>
            <TabsTrigger
              value="review"
              className="h-9 flex-none rounded-full px-3 text-xs font-semibold data-[state=active]:bg-amber-soft data-[state=active]:text-amber"
            >
              Needs review{" "}
              <span className="font-mono tabular-nums">
                {failedRecordings.length}
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="all"
              className="h-9 flex-none rounded-full px-3 text-xs font-semibold data-[state=active]:bg-surface-muted"
            >
              All processed{" "}
              <span className="font-mono tabular-nums">
                {processedRecordings.length}
              </span>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      {pendingCount > 0 && (
        <div
          className="min-h-11 border-b border-rule bg-surface-soft px-4 py-3 text-xs text-ink-muted sm:px-5"
          aria-live="polite"
        >
          <Icon
            name="spinner"
            className="mr-1.5 inline size-3.5 animate-spin text-teal"
          />
          {pendingCount} recording{pendingCount === 1 ? "" : "s"} still
          processing. Only completed results are shown.
        </div>
      )}
      {visibleRecordings.length > 0 ? (
        <div className="divide-y divide-rule">
          {visibleRecordings.map((recording) => (
            <RecordingRow
              key={recording.recordId}
              recording={recording}
              total={session.recordings.length}
            />
          ))}
        </div>
      ) : (
        <div className="px-5 py-10 text-center sm:px-7">
          <p className="text-sm font-bold text-ink">
            {activeFilter === "alerts"
              ? `No ${development ? "development flags" : "model alerts"} detected.`
              : activeFilter === "review"
                ? "No recordings need review."
                : "No processed recordings yet."}
          </p>
          <p className="mt-2 text-xs leading-5 text-ink-muted">
            {activeFilter === "alerts"
              ? "Use All processed to inspect recordings that did not cross the model threshold."
              : "The list will update as processing continues."}
          </p>
        </div>
      )}
    </div>
  );
}

type RecordingFilter = "alerts" | "review" | "all";

/** Render one recording and link only recordings with stored inference results. */
function RecordingRow({
  recording,
  total,
}: {
  recording: Recording;
  total: number;
}) {
  const label = `Recording ${String(recording.sequenceIndex).padStart(2, "0")} of ${total}`;
  const hasModelAlert =
    recording.status === "inferred" && recording.modelAlertWindowCount > 0;
  const development = recording.scoreType === "development_score";
  const calibrated = recording.scoreType === "calibrated_probability";
  const alertClass =
    development || !calibrated
      ? "bg-amber-soft/75 text-amber"
      : "bg-red-soft/60 text-red";
  const content = (
    <>
      <div className="flex min-w-0 items-start gap-3">
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-md ${hasModelAlert ? (development || !calibrated ? "bg-amber text-white" : "bg-red text-white") : "bg-surface-muted text-teal"}`}
          aria-hidden="true"
        >
          <Icon name={hasModelAlert ? "alert" : "file"} className="size-4" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{label}</p>
          <p className="mt-1 text-xs text-ink-muted">
            Privacy-safe display label
            {recording.durationSeconds !== null && (
              <>
                {" "}
                <span className="mx-1 text-rule-strong">·</span>{" "}
                {formatDuration(recording.durationSeconds)}
              </>
            )}
          </p>
          <ModelLabel recording={recording} />
        </div>
      </div>
      <div className="text-xs text-ink-muted">
        {recording.samplingRate ? `${recording.samplingRate} Hz` : "—"}
        {recording.channelCount ? ` · ${recording.channelCount} channels` : ""}
      </div>
      <div>
        <StatusBadge status={toDisplayStatus(recording.status)} />
        {recording.errorMessage && (
          <p className="mt-1 max-w-sm text-xs leading-5 text-red">
            {recording.errorMessage}
          </p>
        )}
      </div>
      <div className="text-teal-dark">
        {recording.status === "inferred" && (
          <Icon name="chevron" className="size-4" aria-hidden="true" />
        )}
      </div>
    </>
  );

  const rowClass = `grid gap-3 px-4 py-4 sm:grid-cols-[minmax(0,1.6fr)_minmax(110px,0.8fr)_minmax(150px,1fr)_20px] sm:items-center sm:px-5 ${hasModelAlert ? alertClass : ""}`;
  if (recording.status !== "inferred")
    return <div className={rowClass}>{content}</div>;
  return (
    <Link
      className={`${rowClass} transition-colors ${hasModelAlert ? (development || !calibrated ? "hover:bg-amber-soft" : "hover:bg-red-soft") : "hover:bg-teal-soft/20"}`}
      href={`/results/${encodeURIComponent(recording.recordId)}`}
      aria-label={`Open ${label} results`}
    >
      {content}
    </Link>
  );
}

/** Format duration without showing unnecessary decimal precision. */
function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${String(remainingSeconds).padStart(2, "0")}s`;
}

/** Render one dashboard session card that opens the full session detail page. */
export function SessionGroup({
  session,
  onDelete,
}: {
  session: Session;
  onDelete?: (sessionId: string) => Promise<void>;
}) {
  const [swiped, setSwiped] = useState(false);
  const pointerStart = useRef<number | null>(null);
  const analysisReady = isAnalysisReady(session);
  const completedRecordings = session.recordings.filter(
    (recording) => recording.status === "inferred",
  );
  const alertCount = completedRecordings.filter(
    (recording) => recording.modelAlertWindowCount > 0,
  ).length;
  const development = completedRecordings.some(
    (recording) => recording.scoreType === "development_score",
  );
  const calibrated = completedRecordings.some(
    (recording) => recording.scoreType === "calibrated_probability",
  );
  const alertLabel = development
    ? "development flag"
    : calibrated
      ? "model alert"
      : "research flag";
  const alertToneClass =
    development || !calibrated
      ? "font-semibold text-amber"
      : "font-semibold text-red";
  const modelSummary = analysisReady
    ? alertCount === 0
      ? `No ${alertLabel}s detected`
      : `${alertCount} recording${alertCount === 1 ? "" : "s"} with ${alertLabel}s`
    : "Results pending";
  const alertSummary = sessionAlertSummary(session);
  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === "touch") pointerStart.current = event.clientX;
  };
  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (pointerStart.current === null) return;
    setSwiped(pointerStart.current - event.clientX > 48);
    pointerStart.current = null;
  };

  return (
    <div
      className="relative touch-pan-y overflow-hidden rounded-xl"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerCancel={() => {
        pointerStart.current = null;
      }}
    >
      {onDelete && (
        <div className="absolute inset-y-0 right-0 flex w-24 items-center justify-center bg-red-soft">
          <DeleteSessionButton
            session={session}
            onDelete={onDelete}
            variant="swipe"
          />
        </div>
      )}
      <section
        className={`panel relative overflow-hidden transition-transform duration-200 ${swiped ? "-translate-x-24" : ""}`}
        aria-labelledby={`session-${session.sessionId}`}
      >
        <Link
          className="group block bg-surface-soft px-4 py-5 transition-colors hover:bg-surface sm:px-5 sm:py-6"
          href={`/sessions/${encodeURIComponent(session.sessionId)}`}
          aria-label={`Open session ${session.sessionId}`}
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
                Analysis session
              </p>
              <h2
                id={`session-${session.sessionId}`}
                className="mt-2 truncate font-mono text-sm font-bold text-ink"
              >
                {session.sessionId}
              </h2>
              <p className="mt-2 text-xs text-ink-muted">
                Submitted {formatSubmittedAt(session.createdAt)}{" "}
                <span className="mx-1 text-rule-strong">·</span>{" "}
                {session.progress.finishedRecordings}/
                {session.progress.totalRecordings || "—"} processed
              </p>
            </div>
            <div className="flex items-center gap-3 sm:pt-1">
              <span className="text-xs text-ink-muted">
                {session.privacyMethod.label}
              </span>
              <StatusBadge status={toDisplayStatus(session.status)} />
              <Icon
                name="chevron"
                className="size-4 text-ink-muted transition-transform group-hover:translate-x-0.5"
              />
            </div>
          </div>
          <div className="mt-5 grid gap-4 border-t border-rule pt-4 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,0.8fr)] sm:gap-8">
            <div>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="font-semibold text-ink">
                  Processing progress
                </span>
                <span className="font-mono text-ink-muted">
                  {session.progress.percent}%
                </span>
              </div>
              <Progress
                value={session.progress.percent}
                className="mt-2 h-2 bg-surface-muted [&_[data-slot=progress-indicator]]:rounded-full [&_[data-slot=progress-indicator]]:bg-teal"
                aria-label={`Processing progress for ${session.sessionId}`}
              />
              <p className="mt-2 text-xs text-ink-muted">
                {session.progress.finishedRecordings} of{" "}
                {session.progress.totalRecordings || "—"} recordings processed
              </p>
            </div>
            <div className="text-xs leading-5 sm:border-l sm:border-rule sm:pl-6">
              <p className="font-semibold text-ink">Analysis summary</p>
              <p
                className={`mt-1 ${analysisReady && alertCount > 0 ? alertToneClass : "text-ink-muted"}`}
              >
                {modelSummary}
              </p>
              {analysisReady && alertCount > 0 && (
                <p className="mt-2 text-xs text-ink-muted">
                  Flagged times: {alertSummary.values.join(", ")}
                  {alertSummary.remaining > 0
                    ? ` +${alertSummary.remaining} more intervals`
                    : ""}
                </p>
              )}
            </div>
          </div>
        </Link>
        {onDelete && (
          <div className="flex items-center justify-between gap-4 border-t border-rule px-4 py-2.5 sm:px-5">
            <span className="text-xs text-ink-muted">
              Open the session to review its recordings.
            </span>
            <DeleteSessionButton session={session} onDelete={onDelete} />
          </div>
        )}
      </section>
    </div>
  );
}

/** Show only the persisted model result, never a dataset reference label. */
function ModelLabel({ recording }: { recording: Recording }) {
  const development = recording.scoreType === "development_score";
  const calibrated = recording.scoreType === "calibrated_probability";
  const alertLabel = development
    ? "Development flag"
    : calibrated
      ? "Model alert"
      : "Research threshold flag";
  const modelLabel =
    recording.status !== "inferred"
      ? "Result pending"
      : recording.modelAlertWindowCount > 0
        ? `${alertLabel} · ${recording.modelAlertWindowCount} ${recording.modelAlertWindowCount === 1 ? "window" : "windows"} flagged`
        : "No flagged windows";
  const modelClass =
    recording.status !== "inferred"
      ? "text-ink-muted"
      : recording.modelAlertWindowCount > 0
        ? development || !calibrated
          ? "font-semibold text-amber"
          : "font-semibold text-red"
        : "text-ink-muted";
  return (
    <>
      <p className={`mt-1 text-xs ${modelClass}`}>{modelLabel}</p>
      {recording.status === "inferred" &&
        recording.modelAlertWindowCount > 0 &&
        recording.alertIntervals.length > 0 && (
          <p className="mt-1 text-xs text-ink-muted">
            First flagged interval:{" "}
            {formatInterval(
              recording.alertIntervals[0].startSeconds,
              recording.alertIntervals[0].endSeconds,
            )}
            {recording.alertIntervals.length > 1
              ? ` +${recording.alertIntervals.length - 1} more`
              : ""}
          </p>
        )}
    </>
  );
}

/** Return compact model-alert times and a count of omitted intervals. */
function sessionAlertSummary(session: Session): {
  values: string[];
  remaining: number;
} {
  const values = session.recordings
    .filter(
      (recording) =>
        recording.status === "inferred" && recording.modelAlertWindowCount > 0,
    )
    .flatMap((recording) => {
      const interval = recording.alertIntervals[0];
      return interval
        ? [
            `Recording ${String(recording.sequenceIndex).padStart(2, "0")} · ${formatInterval(interval.startSeconds, interval.endSeconds)}`,
          ]
        : [];
    });
  return {
    values: values.slice(0, 3),
    remaining: Math.max(0, values.length - 3),
  };
}

/** Format a model-alert interval as a recording-relative time range. */
function formatInterval(startSeconds: number, endSeconds: number): string {
  return `${formatOffset(startSeconds)}-${formatOffset(endSeconds)}`;
}

/** Format a recording-relative offset as minutes and seconds. */
function formatOffset(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

/** Render a destructive session action with a safe processing guard. */
export function DeleteSessionButton({
  session,
  onDelete,
  variant = "inline",
}: {
  session: Session;
  onDelete: (sessionId: string) => Promise<void>;
  variant?: "inline" | "swipe";
}) {
  const active = ACTIVE_SESSION_STATUSES.has(session.status);
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(session.sessionId);
      setOpen(false);
    } catch {
      // The parent displays the API error and keeps the dialog available.
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!deleting) setOpen(nextOpen);
      }}
    >
      <AlertDialogTrigger asChild>
        <button
          className={
            variant === "swipe"
              ? "inline-flex flex-col items-center gap-1 text-xs font-bold text-red disabled:cursor-not-allowed disabled:text-ink-muted"
              : "inline-flex min-h-9 items-center gap-1.5 text-xs font-bold text-red underline decoration-red/30 underline-offset-4 disabled:cursor-not-allowed disabled:text-ink-muted disabled:no-underline"
          }
          type="button"
          disabled={active}
          title={
            active
              ? "Available after processing finishes"
              : "Delete this session"
          }
          onPointerDown={(event) => event.stopPropagation()}
          onPointerUp={(event) => event.stopPropagation()}
          onClick={(event) => event.stopPropagation()}
        >
          <Icon
            name="trash"
            className={variant === "swipe" ? "size-5" : "size-3.5"}
          />
          {active ? "Delete after processing" : "Delete session"}
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <div className="flex items-start gap-3">
          <span
            className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-red-soft text-red"
            aria-hidden="true"
          >
            <Icon name="trash" className="size-4" weight="bold" />
          </span>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this session?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the session results and retained private
              artifacts. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
        </div>
        <dl className="grid gap-x-5 gap-y-3 border-y border-rule py-4 text-xs sm:grid-cols-[minmax(0,1fr)_auto]">
          <div className="min-w-0">
            <dt className="text-ink-muted">Session</dt>
            <dd className="mt-1 truncate font-mono font-medium text-ink">
              {session.sessionId}
            </dd>
          </div>
          <div>
            <dt className="text-ink-muted">Recordings</dt>
            <dd className="mt-1 font-medium tabular-nums text-ink">
              {session.progress.totalRecordings}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-ink-muted">Submitted</dt>
            <dd className="mt-1 font-medium text-ink">
              {formatSubmittedAt(session.createdAt)}
            </dd>
          </div>
        </dl>
        <AlertDialogFooter>
          <AlertDialogCancel
            className="h-9 w-full px-4 sm:w-auto"
            disabled={deleting}
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            className="h-9 w-full bg-red px-4 text-white hover:bg-red/90 focus-visible:border-red focus-visible:ring-red/30 sm:w-auto"
            disabled={deleting}
            aria-busy={deleting}
            onClick={(event) => {
              event.preventDefault();
              void confirmDelete();
            }}
          >
            <Icon
              name={deleting ? "spinner" : "trash"}
              className={`size-4 ${deleting ? "animate-spin" : ""}`}
              weight="bold"
            />
            {deleting ? "Deleting…" : "Delete session"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
