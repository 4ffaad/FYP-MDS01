"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getJobs } from "@/lib/api";
import { formatSubmittedAt } from "@/lib/format";
import type { Job, JobStatus } from "@/lib/types";
import { Icon } from "./Icon";
import { StatusBadge } from "./StatusBadge";

/** Render the scannable run list and keep active analyses up to date. */
export function DashboardScreen() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState<"all" | JobStatus>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Fetch the latest safe run summaries and preserve abort behavior on navigation. */
  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const nextJobs = await getJobs(signal);
      setJobs(nextJobs);
      setError(null);
    } catch (refreshError) {
      if (refreshError instanceof DOMException && refreshError.name === "AbortError") return;
      setError(refreshError instanceof Error ? refreshError.message : "The dashboard could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const initialLoad = window.setTimeout(() => void refresh(controller.signal), 0);
    const timer = window.setInterval(() => void refresh(controller.signal), 2000);
    return () => { controller.abort(); window.clearTimeout(initialLoad); window.clearInterval(timer); };
  }, [refresh]);

  const visibleJobs = filter === "all" ? jobs : jobs.filter((job) => job.status === filter);

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <div className="flex flex-col justify-between gap-6 border-b border-rule pb-7 sm:flex-row sm:items-end">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1 className="mt-3 text-[clamp(2rem,4vw,3.15rem)] font-semibold leading-[1.06] tracking-[-0.05em] text-ink">Analysis dashboard</h1>
            <p className="mt-4 max-w-xl text-[0.94rem] leading-6 text-ink-muted">See what is queued, what is processing, and which completed runs are ready for review.</p>
          </div>
          <Link className="button-primary shrink-0" href="/upload"><Icon name="upload" className="size-4" />New analysis</Link>
        </div>

        <div className="flex flex-col justify-between gap-4 border-b border-rule py-5 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3 text-sm text-ink-muted"><span className="font-semibold text-ink">{jobs.length}</span> {jobs.length === 1 ? "analysis" : "analyses"}<span className="inline-flex items-center gap-1.5 text-xs text-ink-faint"><span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Updates automatically</span></div>
          <label className="flex items-center gap-2 text-xs text-ink-muted" htmlFor="status-filter"><span>Filter</span><select className="min-h-9 rounded-md border border-rule-strong bg-surface px-3 text-xs font-semibold text-ink outline-none transition focus:border-teal" id="status-filter" value={filter} onChange={(event) => setFilter(event.target.value as "all" | JobStatus)}><option value="all">All statuses</option><option value="queued">Queued</option><option value="processing">Processing</option><option value="complete">Complete</option><option value="failed">Needs review</option></select></label>
        </div>

        {error && <div className="mt-6 flex items-start justify-between gap-4 rounded-lg border border-red/30 bg-red-soft px-4 py-3 text-sm text-red" role="alert"><span className="flex gap-2"><Icon name="alert" className="mt-0.5 size-4 shrink-0" />{error}</span><button className="text-xs font-bold underline underline-offset-4" type="button" onClick={() => { setLoading(true); void refresh(); }}>Try again</button></div>}

        {loading ? <LoadingRows /> : visibleJobs.length === 0 ? <EmptyDashboard filtered={filter !== "all"} /> : <JobTable jobs={visibleJobs} />}
      </div>
    </div>
  );
}

function LoadingRows() {
  return <div className="mt-6 space-y-2" aria-label="Loading analyses"><div className="h-20 animate-pulse rounded-lg border border-rule bg-surface" /><div className="h-20 animate-pulse rounded-lg border border-rule bg-surface" /></div>;
}

function EmptyDashboard({ filtered }: { filtered: boolean }) {
  return <div className="mt-8 panel px-6 py-14 text-center"><div className="mx-auto grid size-10 place-items-center rounded-md bg-teal-soft text-teal"><Icon name={filtered ? "list" : "upload"} className="size-5" /></div><h2 className="mt-5 text-lg font-bold tracking-[-0.02em]">{filtered ? "No analyses match this filter." : "No analyses submitted yet."}</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">{filtered ? "Choose another status to see more runs." : "Start with an EEG recording. Its status and results will appear here."}</p>{!filtered && <Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" href="/upload">Submit an EEG recording <Icon name="arrow" className="size-4" /></Link>}</div>;
}

function JobTable({ jobs }: { jobs: Job[] }) {
  return <div className="mt-6" role="region" aria-label="Analysis runs"><div className="hidden grid-cols-[minmax(0,1.7fr)_minmax(130px,0.85fr)_150px_130px_20px] gap-4 px-4 pb-2 text-[0.66rem] font-bold uppercase tracking-[0.12em] text-ink-faint lg:grid"><span>Run</span><span>Submitted</span><span>Requested configuration</span><span>Status</span><span /></div><div className="space-y-2">{jobs.map((job) => <JobRow key={job.jobId} job={job} />)}</div></div>;
}

function JobRow({ job }: { job: Job }) {
  const content = <><div className="flex min-w-0 items-start gap-3.5"><div className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-md bg-surface-muted text-teal"><Icon name="file" className="size-4" /></div><div className="min-w-0"><p className="truncate text-sm font-bold text-ink">{job.recordingLabel}</p><p className="mt-1 text-xs text-ink-muted"><span className="font-mono">{job.jobId}</span><span className="mx-2 text-rule-strong">·</span><span className="lg:hidden">{formatSubmittedAt(job.submittedAt)}</span></p></div></div><div className="hidden text-xs text-ink-muted lg:block">{formatSubmittedAt(job.submittedAt)}</div><div className="text-xs text-ink-muted">{job.privacyMethod.label}</div><div><StatusBadge status={job.status} />{job.status === "failed" && <span className="mt-1 block max-w-[180px] text-xs text-red">{job.errorMessage ?? "Open details"}</span>}</div><div className="hidden text-teal-dark lg:block">{job.status === "complete" && <Icon name="chevron" className="size-4" />}</div></>;
  const rowClass = "grid gap-4 rounded-lg border border-rule bg-surface px-4 py-4 transition-colors hover:border-rule-strong sm:px-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(130px,0.85fr)_150px_130px_20px] lg:items-center";
  return job.status === "complete" ? <Link className={`${rowClass} hover:bg-teal-soft/20`} href={`/results/${encodeURIComponent(job.jobId)}`} aria-label={`Open ${job.recordingLabel} results`}>{content}</Link> : <div className={rowClass}>{content}</div>;
}
