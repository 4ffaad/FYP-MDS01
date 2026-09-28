"use client";

import Link from "next/link";
import type { CaseSummary } from "@/lib/types";
import { Icon } from "./Icon";

export type WorkspaceCaseSummary = Pick<
  CaseSummary,
  | "caseId"
  | "patientName"
  | "patientNameVerificationStatus"
  | "modalities"
  | "latestCreatedAt"
  | "status"
  | "flaggedIntervalCount"
>;

interface RecentPatientHistoryProps {
  items: WorkspaceCaseSummary[];
  loading: boolean;
  error: string | null;
}

/** Owner-scoped patient-name shortcuts for the workspace landing page. */
export function RecentPatientHistory({
  items,
  loading,
  error,
}: RecentPatientHistoryProps) {
  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="recent-patient-history-heading"
    >
      <div className="flex items-start justify-between gap-4 border-b border-rule px-5 py-5 sm:px-6">
        <div>
          <p className="eyebrow">Longitudinal review</p>
          <h2
            id="recent-patient-history-heading"
            className="mt-1 text-lg font-bold"
          >
            Recent patient history
          </h2>
          <p className="mt-1 text-xs leading-5 text-ink-muted">
            Owner-scoped names and recent EEG/video review status.
          </p>
        </div>
        <Link
          href="/cases"
          className="shrink-0 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
        >
          Patient History
        </Link>
      </div>

      {loading ? (
        <div className="px-5 py-8 text-sm text-ink-muted" role="status">
          Loading patient history…
        </div>
      ) : error ? (
        <div className="px-5 py-6 text-sm text-ink-muted" role="alert">
          <p>Recent patient history is temporarily unavailable.</p>
          <Link
            href="/cases"
            className="mt-3 inline-flex min-h-10 items-center gap-2 font-bold text-teal-dark underline underline-offset-4"
          >
            Open Patient History <Icon name="arrow" className="size-4" />
          </Link>
        </div>
      ) : items.length === 0 ? (
        <div className="px-5 py-8 text-sm text-ink-muted">
          <p>No patient reviews yet.</p>
          <Link
            href="/upload"
            className="mt-3 inline-flex min-h-10 items-center gap-2 font-bold text-teal-dark underline underline-offset-4"
          >
            Start a patient review <Icon name="arrow" className="size-4" />
          </Link>
        </div>
      ) : (
        <ol className="divide-y divide-rule">
          {items.map((item) => (
            <li key={item.caseId}>
              <Link
                href={`/cases/${encodeURIComponent(item.caseId)}`}
                className="group block px-5 py-4 transition-colors hover:bg-surface-soft/70 focus-visible:bg-surface-soft sm:px-6"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-ink group-hover:text-teal-dark">
                    {item.patientName?.trim() || "Patient name unavailable"}
                  </span>
                  {item.patientNameVerificationStatus === "auto_extracted" && (
                    <span className="rounded-full bg-amber-soft/60 px-2.5 py-1 text-[0.65rem] font-semibold text-ink-muted">
                      Name auto-extracted · not verified
                    </span>
                  )}
                  <span className="ml-auto rounded-full bg-surface-soft px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
                    {item.status.replace("_", " ")}
                  </span>
                </div>
                <p className="mt-2 text-xs text-ink-muted">
                  {item.modalities
                    .map((modality) => modality.toUpperCase())
                    .join(" + ")}
                </p>
                <p className="mt-1 text-xs text-ink-faint">
                  Updated {formatDate(item.latestCreatedAt)}
                  {item.flaggedIntervalCount > 0
                    ? ` · ${item.flaggedIntervalCount} flagged windows`
                    : " · No flagged windows"}
                </p>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value));
}
