"use client";

import { useCallback, useContext, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { getCases, getSessions } from "@/lib/api";
import { listDetections, type DetectionJob } from "@/lib/video-detection";
import type { CaseSummary } from "@/lib/types";
import { Icon } from "./Icon";
import { WorkspaceUserContext } from "./AppShell";

type RecentCase = Pick<
  CaseSummary,
  "caseId" | "modalities" | "latestCreatedAt" | "status"
>;

function shortCaseId(caseId: string) {
  return `PT-${caseId.slice(-8)}`;
}

function displayDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat(undefined, {
        day: "2-digit",
        month: "short",
      }).format(date);
}

function statusLabel(status: CaseSummary["status"]) {
  return {
    processing: "Processing",
    complete: "Ready",
    needs_review: "Issues",
  }[status];
}

export function DashboardScreen() {
  const user = useContext(WorkspaceUserContext);
  const [cases, setCases] = useState<RecentCase[]>([]);
  const [eegSessionCount, setEegSessionCount] = useState(0);
  const [videoJobs, setVideoJobs] = useState<DetectionJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const requestNumber = useRef(0);
  const requestController = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    const currentRequest = ++requestNumber.current;

    try {
      const [caseItems, sessions, { jobs }] = await Promise.all([
        getCases(controller.signal),
        getSessions(controller.signal),
        listDetections(controller.signal),
      ]);
      if (controller.signal.aborted || currentRequest !== requestNumber.current)
        return;
      setCases(
        [...caseItems]
          .sort(
            (left, right) =>
              Date.parse(right.latestCreatedAt) -
              Date.parse(left.latestCreatedAt),
          )
          .map(({ caseId, modalities, latestCreatedAt, status }) => ({
            caseId,
            modalities,
            latestCreatedAt,
            status,
          })),
      );
      setEegSessionCount(sessions.length);
      setVideoJobs(jobs);
      setError(null);
    } catch (loadError) {
      if (
        controller.signal.aborted ||
        (loadError instanceof DOMException && loadError.name === "AbortError")
      )
        return;
      if (currentRequest !== requestNumber.current) return;
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Dashboard data could not be loaded.",
      );
    } finally {
      if (
        !controller.signal.aborted &&
        currentRequest === requestNumber.current
      )
        setLoading(false);
      if (requestController.current === controller)
        requestController.current = null;
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void refresh(), 0);
    return () => {
      window.clearTimeout(initialLoad);
      requestNumber.current += 1;
      requestController.current?.abort();
    };
  }, [refresh]);

  const linkedCaseIds = new Set(
    videoJobs.flatMap((job) =>
      job.case_id && job.sync?.status === "linked" ? [job.case_id] : [],
    ),
  );
  const processingCount = cases.filter(
    (item) => item.status === "processing",
  ).length;
  const readyCount = cases.filter((item) => item.status === "complete").length;
  const issueCount = cases.filter(
    (item) => item.status === "needs_review",
  ).length;
  const workspaces = [
    {
      label: "VEEG",
      detail: "Synced cases",
      count: linkedCaseIds.size,
      href: "/cases",
    },
    {
      label: "EEG",
      detail: "EEG sessions",
      count: eegSessionCount,
      href: "/upload/eeg?view=reviews",
    },
    {
      label: "VIDEO",
      detail: "Video files",
      count: videoJobs.length,
      href: "/video-reviews",
    },
  ];
  const metrics = [
    { label: "Total patients", value: cases.length },
    { label: "Active processing", value: processingCount },
    { label: "Ready", value: readyCount },
    { label: "Issues", value: issueCount },
  ];
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const recentCases = cases
    .filter((item) =>
      shortCaseId(item.caseId).toLocaleLowerCase().includes(normalizedQuery),
    )
    .slice(0, 5);

  return (
    <div className="page-frame space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">
            Dashboard
          </h1>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Overview of patient recordings and processing status
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-xs font-medium text-ink-muted">
            Search
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.currentTarget.value)}
              placeholder="Patient ID"
              className="min-h-11 w-44 rounded-lg border border-rule-strong bg-surface px-3 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-teal focus:ring-2 focus:ring-teal/20"
            />
          </label>
          {user && (
            <div
              aria-label={`Profile: ${user.displayName}`}
              className="flex min-h-11 items-center gap-2 rounded-lg border border-rule bg-surface px-3"
            >
              <span className="grid size-7 place-items-center rounded-full bg-teal-soft text-xs font-bold text-teal-dark">
                {user.displayName.slice(0, 1).toUpperCase()}
              </span>
              <span className="text-sm font-semibold text-ink">
                {user.displayName}
              </span>
            </div>
          )}
          <Button
            asChild
            className="min-h-11 bg-teal-dark text-white hover:bg-teal-dark/90"
          >
            <Link href="/upload">
              <Icon name="upload" className="size-4" />
              New review
            </Link>
          </Button>
        </div>
      </header>

      <section
        aria-label="Analysis workspaces"
        className="grid gap-4 md:grid-cols-3"
      >
        {workspaces.map((workspace) => (
          <Link
            key={workspace.label}
            href={workspace.href}
            className="group rounded-2xl border border-rule bg-surface p-5 shadow-hard transition-shadow hover:shadow-hard-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-bold tracking-[0.14em] text-ink-muted">
                {workspace.label}
              </span>
              <Icon
                name={workspace.label === "VIDEO" ? "video" : "activity"}
                className="size-5 text-teal-dark"
              />
            </div>
            <p className="mt-3 text-sm text-ink-muted">{workspace.detail}</p>
            <p className="mt-1 text-4xl font-semibold tabular-nums tracking-tight text-ink">
              {loading || error ? "—" : workspace.count}
            </p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-teal-dark">
              View workspace <Icon name="arrow" className="size-4" />
            </span>
          </Link>
        ))}
      </section>

      <dl
        className="grid grid-cols-2 divide-x divide-y divide-rule overflow-hidden rounded-2xl border border-rule bg-surface shadow-hard md:grid-cols-4 md:divide-y-0"
        aria-label="Patient processing totals"
        aria-busy={loading}
      >
        {metrics.map(({ label, value }) => (
          <div key={label} className="px-5 py-4 sm:px-6">
            <dt className="text-xs font-medium text-ink-muted">{label}</dt>
            <dd className="mt-2 text-2xl font-semibold tabular-nums text-ink">
              {loading || error ? "—" : value}
            </dd>
          </div>
        ))}
      </dl>

      <section
        className="overflow-hidden rounded-2xl border border-rule bg-surface shadow-hard"
        aria-labelledby="recent-cases-heading"
      >
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule px-5 py-4 sm:px-6">
          <div>
            <h2
              id="recent-cases-heading"
              className="text-lg font-semibold text-ink"
            >
              Recent patients / sessions
            </h2>
            <p className="mt-1 text-xs text-ink-muted">Newest activity first</p>
          </div>
        </div>

        {error ? (
          <div
            className="flex flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-6"
            role="alert"
          >
            <p className="text-sm text-ink-muted">
              Dashboard records could not be loaded.
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={() => void refresh()}
            >
              Try again
            </Button>
          </div>
        ) : loading ? (
          <p className="px-5 py-6 text-sm text-ink-muted" role="status">
            Loading records…
          </p>
        ) : recentCases.length === 0 ? (
          <p className="px-5 py-6 text-sm text-ink-muted" role="status">
            {cases.length === 0
              ? "No patient cases yet. Start a new review to add recordings."
              : "No patient IDs match this search."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[42rem] text-left text-sm">
              <thead className="bg-surface-soft text-xs text-ink-muted">
                <tr>
                  <th className="px-5 py-3 font-semibold sm:px-6">
                    Patient ID
                  </th>
                  <th className="px-5 py-3 font-semibold">Date</th>
                  <th className="px-5 py-3 font-semibold">Data</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  <th
                    className="px-5 py-3 text-right font-semibold sm:px-6"
                    aria-label="Open case"
                  />
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {recentCases.map((item) => {
                  const hasEeg = item.modalities.includes("eeg");
                  const hasVideo = item.modalities.includes("video");
                  const dataLabels = [
                    hasEeg ? "EEG" : null,
                    hasVideo ? "Video" : null,
                    linkedCaseIds.has(item.caseId) ? "VEEG" : null,
                  ].filter((label): label is string => Boolean(label));
                  return (
                    <tr
                      key={item.caseId}
                      className="transition-colors hover:bg-surface-soft/70"
                    >
                      <td className="px-5 py-4 font-mono font-semibold tabular-nums text-ink sm:px-6">
                        {shortCaseId(item.caseId)}
                      </td>
                      <td className="px-5 py-4 text-ink-muted">
                        {displayDate(item.latestCreatedAt)}
                      </td>
                      <td className="px-5 py-4 text-ink">
                        {dataLabels.length ? dataLabels.join(" · ") : "—"}
                      </td>
                      <td className="px-5 py-4">
                        <span className="rounded-full border border-rule bg-surface-soft px-2.5 py-1 text-xs font-semibold text-ink">
                          {statusLabel(item.status)}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right sm:px-6">
                        <Link
                          href={`/cases/${encodeURIComponent(item.caseId)}`}
                          className="inline-flex min-h-10 items-center gap-1 rounded-md px-2 font-semibold text-teal-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
                        >
                          Open <Icon name="arrow" className="size-4" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
