"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { formatSubmittedAt } from "@/lib/format";
import { apiMediaUrl, toDisplayStatus } from "@/lib/api";
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
    const failed = processed.filter(
      (recording) => recording.status === "failed",
    );
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
      {session.sourceAvailable && (
        <div className="flex flex-wrap gap-4 border-b border-rule px-5 py-3 text-sm">
          <a
            className="underline"
            href={apiMediaUrl(
              `/api/sessions/${encodeURIComponent(session.sessionId)}/original`,
            )}
          >
            Download original archive
          </a>
          <a
            className="underline"
            href={apiMediaUrl(
              `/api/sessions/${encodeURIComponent(session.sessionId)}/original-report`,
            )}
          >
            Download original report, if included
          </a>
          <span className="text-ink-muted">Retained until case deletion</span>
        </div>
      )}
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
  if (recording.status !== "inferred" && !recording.sourceAvailable)
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
    recording.status === "failed"
      ? "No EEG result saved"
      : recording.status !== "inferred"
        ? "Result pending"
        : recording.modelAlertWindowCount > 0
          ? `${alertLabel} · ${recording.modelAlertWindowCount} ${recording.modelAlertWindowCount === 1 ? "window" : "windows"} flagged`
          : "No flagged windows";
  const modelClass =
    recording.status === "failed"
      ? "font-semibold text-amber"
      : recording.status !== "inferred"
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
