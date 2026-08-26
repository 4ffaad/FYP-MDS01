"use client";

import Link from "next/link";
import type { Recording, Session } from "@/lib/types";
import { Icon } from "./Icon";

/** Keep the session recording list available without permanently narrowing the EEG view. */
export function RecordingNavigator({ session, activeRecordId }: { session: Session; activeRecordId: string }) {
  const readyCount = session.recordings.filter((recording) => recording.status === "inferred").length;
  const failedCount = session.recordings.filter((recording) => recording.status === "failed").length;
  const active = session.recordings.find((recording) => recording.recordId === activeRecordId);
  const activeNumber = active?.sequenceIndex ?? 1;

  if (session.recordings.length === 1) {
    const hasAlert = Boolean(active?.modelAlertWindowCount);
    const calibrated = active?.scoreType === "calibrated_probability";
    const alertTone = calibrated ? "bg-red-soft text-red" : "bg-amber-soft text-amber";
    return (
      <nav className="panel flex items-center gap-3 px-5 py-4 sm:px-7" aria-label="Recordings in this session">
        <span className={`grid size-9 shrink-0 place-items-center rounded-lg ${hasAlert ? alertTone : "bg-teal-soft text-teal-dark"}`}><Icon name={hasAlert ? "alert" : "check"} className="size-4" /></span>
        <span>
          <span className="block text-sm font-bold text-ink">Recording 01 of 1</span>
          <span className="mt-0.5 block text-xs text-ink-muted">{hasAlert ? `${active?.modelAlertWindowCount} flagged windows` : "No flagged windows"}</span>
        </span>
      </nav>
    );
  }

  return (
    <nav className="panel overflow-hidden" aria-label="Recordings in this session">
      <details open={session.recordings.length <= 6}>
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 marker:hidden sm:px-7 [&::-webkit-details-marker]:hidden">
          <span className="flex min-w-0 items-center gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-teal-soft text-teal-dark"><Icon name="list" className="size-4" /></span>
            <span className="min-w-0">
              <span className="block text-sm font-bold text-ink">Recording {String(activeNumber).padStart(2, "0")} of {session.recordings.length}</span>
              <span className="mt-0.5 block truncate text-xs text-ink-muted">{readyCount} ready{failedCount > 0 ? ` · ${failedCount} need review` : ""}</span>
            </span>
          </span>
          <span className="inline-flex shrink-0 items-center gap-2 text-xs font-semibold text-teal-dark">Change recording <Icon name="chevron" className="size-4 transition-transform in-open:rotate-90" /></span>
        </summary>
        <div className="max-h-80 divide-y divide-rule overflow-y-auto border-t border-rule bg-surface-soft">
          {session.recordings.map((recording) => (
            <RecordingLink key={recording.recordId} recording={recording} total={session.recordings.length} active={recording.recordId === activeRecordId} />
          ))}
        </div>
      </details>
    </nav>
  );
}

/** Render one safe recording entry, linking only when its result exists. */
function RecordingLink({ recording, total, active }: { recording: Recording; total: number; active: boolean }) {
  const status = recording.status === "failed" ? "Needs review" : recording.status === "inferred" ? "Complete" : recording.status === "uploaded" ? "Queued" : "Processing";
  const hasModelAlert = recording.status === "inferred" && recording.modelAlertWindowCount > 0;
  const development = recording.scoreType === "development_score";
  const calibrated = recording.scoreType === "calibrated_probability";
  const alertLabel = development ? "Development flag" : calibrated ? "Model alert" : "Research threshold flag";
  const label = `Recording ${String(recording.sequenceIndex).padStart(2, "0")} of ${total}`;
  const firstInterval = recording.alertIntervals[0];
  const summary = hasModelAlert
    ? `${alertLabel} · ${recording.modelAlertWindowCount} window${recording.modelAlertWindowCount === 1 ? "" : "s"}${firstInterval ? ` · ${formatTime(firstInterval.startSeconds)}–${formatTime(firstInterval.endSeconds)}` : ""}`
    : recording.status === "inferred" ? "No flagged windows" : status;
  const tone = hasModelAlert
    ? development || !calibrated ? "bg-amber-soft text-amber" : "bg-red-soft text-red"
    : active ? "bg-teal-soft text-teal-dark" : "bg-surface text-ink-muted";
  const content = (
    <>
      <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${tone}`} aria-hidden="true"><Icon name={recording.status === "failed" || hasModelAlert ? "alert" : recording.status === "inferred" ? "check" : "file"} className="size-4" /></span>
      <span className="min-w-0 flex-1">
        <span className="block text-xs font-bold text-ink">{label}</span>
        <span className={`mt-1 block text-xs leading-5 ${hasModelAlert ? development || !calibrated ? "font-semibold text-amber" : "font-semibold text-red" : "text-ink-muted"}`}>{summary}</span>
        {recording.errorMessage && <span className="mt-1 block text-xs leading-5 text-red">{recording.errorMessage}</span>}
      </span>
      {recording.status === "inferred" && <Icon name="chevron" className="size-4 shrink-0 text-ink-faint" />}
    </>
  );
  const className = `flex min-h-16 items-center gap-3 px-5 py-3 sm:px-7 ${active ? "bg-teal-soft/70" : "hover:bg-surface"}`;
  if (recording.status !== "inferred") return <div className={className}>{content}</div>;
  return <Link className={className} href={`/results/${encodeURIComponent(recording.recordId)}`} aria-current={active ? "page" : undefined} aria-label={`Open ${label} results`}>{content}</Link>;
}

function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}
