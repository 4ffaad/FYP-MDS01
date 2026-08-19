"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import type { Recording, Session } from "@/lib/types";
import { Icon } from "./Icon";

/** Render the scalable, privacy-safe recording index for one result session. */
export function RecordingNavigator({ session, activeRecordId }: { session: Session; activeRecordId: string }) {
  const activeLink = useRef<HTMLAnchorElement>(null);
  const recordingList = useRef<HTMLDivElement>(null);
  const readyCount = session.recordings.filter((recording) => recording.status === "inferred").length;
  const failedCount = session.recordings.filter((recording) => recording.status === "failed").length;

  useEffect(() => {
    if (!activeLink.current || !recordingList.current) return;
    recordingList.current.scrollTop = Math.max(0, activeLink.current.offsetTop - recordingList.current.clientHeight / 2 + activeLink.current.clientHeight / 2);
  }, [activeRecordId]);

  return <nav className="panel overflow-hidden" aria-label="Recordings in this session"><div className="border-b border-rule px-4 py-4"><h2 className="text-sm font-bold tracking-[-0.015em]">Recordings in this session</h2><p className="mt-1 text-xs leading-5 text-ink-muted"><span className="font-mono text-ink">{session.sessionId}</span> <span className="mx-1 text-rule-strong">·</span> {readyCount} ready{failedCount > 0 && <> <span className="mx-1 text-rule-strong">·</span> {failedCount} need review</>}</p></div><div ref={recordingList} className="max-h-[30rem] divide-y divide-rule overflow-y-auto">{session.recordings.map((recording) => <RecordingLink key={recording.recordId} recording={recording} total={session.recordings.length} active={recording.recordId === activeRecordId} activeRef={recording.recordId === activeRecordId ? activeLink : undefined} />)}</div></nav>;
}

/** Render one safe recording entry, linking only when its result exists. */
function RecordingLink({ recording, total, active, activeRef }: { recording: Recording; total: number; active: boolean; activeRef?: React.Ref<HTMLAnchorElement> }) {
  const status = recording.status === "failed" ? "Needs review" : recording.status === "inferred" ? "Complete" : recording.status === "uploaded" ? "Queued" : "Processing";
  const statusClass = recording.status === "failed" ? "text-red" : recording.status === "inferred" ? "text-teal-dark" : "text-ink-muted";
 const referenceCount = recording.referenceAnnotation?.intervals.length;
 const label = `Recording ${String(recording.sequenceIndex).padStart(2, "0")} of ${total}`;
  const hasDatasetSeizure = (referenceCount ?? 0) > 0;
  const content = <><span className={`grid size-8 shrink-0 place-items-center rounded-md ${active ? "bg-teal text-white" : hasDatasetSeizure ? "bg-red text-white" : "bg-surface-muted text-teal"}`} aria-hidden="true"><Icon name={recording.status === "failed" ? "alert" : hasDatasetSeizure ? "alert" : recording.status === "inferred" ? "check" : "file"} className="size-4" /></span><span className="min-w-0"><span className="block truncate text-xs font-bold text-ink">{label}</span><span className={`mt-1 block text-[0.68rem] leading-4 ${statusClass}`}>{status}</span>{referenceCount !== undefined && <span className={`mt-1 block text-[0.68rem] leading-4 ${hasDatasetSeizure ? "font-semibold text-red" : "text-ink-faint"}`}>{hasDatasetSeizure ? "Dataset seizure" : "No dataset seizure"}</span>}{recording.errorMessage && <span className="mt-1 block text-[0.68rem] leading-4 text-red">{recording.errorMessage}</span>}</span></>;
  const className = `flex min-h-16 items-center gap-3 px-4 py-3 ${active ? "bg-teal-soft" : hasDatasetSeizure ? "bg-red-soft/55" : "bg-surface hover:bg-surface-soft"}`;
  if (recording.status !== "inferred") return <div className={className}>{content}</div>;
  return <Link ref={activeRef} className={className} href={`/results/${encodeURIComponent(recording.recordId)}`} aria-current={active ? "page" : undefined} aria-label={`Open ${label} results`}>{content}</Link>;
}
