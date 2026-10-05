"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
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
import { Button } from "@/components/ui/button";
import type { CaseSummary } from "@/lib/types";
import { CaseStatusBadge } from "./CaseStatusBadge";
import { Icon } from "./Icon";

export type WorkspacePatient = Pick<
  CaseSummary,
  | "caseId"
  | "patientName"
  | "patientNameVerificationStatus"
  | "modalities"
  | "analysisCount"
  | "eegRecordingCount"
  | "videoClipCount"
  | "latestCreatedAt"
  | "status"
  | "flaggedIntervalCount"
  | "explanationReady"
>;

type CaseStatusFilter = "all" | CaseSummary["status"];

interface WorkspacePatientsProps {
  items: WorkspacePatient[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onDelete: (caseId: string) => Promise<void>;
  heading?: string;
  emptyTitle?: string;
  emptyDescription?: string;
}

function formatCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Activity time unavailable";
  return `${new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date)} UTC`;
}

function DeleteCaseAction({
  patientName,
  onDelete,
}: {
  patientName: string;
  onDelete: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmDelete() {
    setDeleting(true);
    setError(null);
    try {
      await onDelete();
      setOpen(false);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The patient case could not be deleted.",
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!deleting) {
          setOpen(nextOpen);
          if (nextOpen) setError(null);
        }
      }}
    >
      <AlertDialogTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="min-h-11 min-w-11 text-red hover:bg-red-soft hover:text-red"
          aria-label={`Delete case for ${patientName}`}
          title="Delete this patient case"
        >
          <Icon name="trash" className="size-4" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this patient case?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently deletes {patientName}, including all linked EEG
            sessions and results, video jobs and previews, patient details,
            source report, and retained media. You cannot undo this. Cases with
            processing work must finish before they can be deleted.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && (
          <p className="text-sm leading-6 text-red" role="alert">
            {error}
          </p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-red text-white hover:bg-red/90 focus-visible:border-red focus-visible:ring-red/30"
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
            {deleting ? "Deleting…" : "Delete case"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function WorkspacePatients({
  items,
  loading,
  error,
  onRetry,
  onDelete,
  heading = "Patient cases",
  emptyTitle = "No patient cases yet",
  emptyDescription = "Start a review with a report, supported EEG recordings, and video clips. The files and results stay grouped under one case.",
}: WorkspacePatientsProps) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<CaseStatusFilter>("all");
  const [modalityFilter, setModalityFilter] = useState("all");
  const statusCounts = useMemo(
    () => ({
      all: items.length,
      needs_review: items.filter((patient) => patient.status === "needs_review")
        .length,
      processing: items.filter((patient) => patient.status === "processing")
        .length,
      complete: items.filter((patient) => patient.status === "complete").length,
    }),
    [items],
  );
  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return items.filter((patient) => {
      const matchesQuery =
        !normalizedQuery ||
        `${patient.patientName ?? ""} ${patient.caseId}`
          .toLocaleLowerCase()
          .includes(normalizedQuery);
      const matchesStatus =
        statusFilter === "all" || patient.status === statusFilter;
      const matchesModality =
        modalityFilter === "all" ||
        patient.modalities.includes(modalityFilter as "eeg" | "video");
      return matchesQuery && matchesStatus && matchesModality;
    });
  }, [items, modalityFilter, query, statusFilter]);

  function clearFilters() {
    setQuery("");
    setStatusFilter("all");
    setModalityFilter("all");
  }

  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="workspace-patients-heading"
    >
      <div className="border-b border-rule px-5 py-5 sm:px-7">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2
                id="workspace-patients-heading"
                className="text-xl font-semibold tracking-tight text-ink"
              >
                {heading}
              </h2>
              {!loading && !error && (
                <p className="mt-1 text-sm text-ink-muted" aria-live="polite">
                  Showing {filteredItems.length} of {items.length} cases
                </p>
              )}
            </div>
            <span className="text-xs font-medium text-ink-faint">
              Sorted by newest upload or job
            </span>
          </div>

          <div
            className="flex flex-wrap gap-1.5"
            role="group"
            aria-label="Filter cases by status"
          >
            {(
              [
                ["all", "All cases"],
                ["needs_review", "Needs review"],
                ["processing", "Processing"],
                ["complete", "Complete"],
              ] as const
            ).map(([value, label]) => (
              <Button
                key={value}
                type="button"
                variant={statusFilter === value ? "secondary" : "ghost"}
                size="sm"
                className="min-h-11 rounded-md px-3"
                aria-pressed={statusFilter === value}
                disabled={loading || Boolean(error)}
                onClick={() => setStatusFilter(value)}
              >
                {label}
                <span className="ml-1 rounded-full bg-black/5 px-1.5 py-0.5 text-xs tabular-nums">
                  {loading || error ? "—" : statusCounts[value]}
                </span>
              </Button>
            ))}
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(14rem,1fr)_12rem]">
          <div>
            <label
              htmlFor="patient-case-search"
              className="mb-1.5 block text-sm font-semibold text-ink"
            >
              Search patients
            </label>
            <input
              id="patient-case-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name or case reference"
              className="min-h-11 w-full rounded-lg border border-rule-strong bg-white px-3 text-sm text-ink placeholder:text-ink-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
            />
          </div>
          <div>
            <label
              htmlFor="patient-case-modality"
              className="mb-1.5 block text-sm font-semibold text-ink"
            >
              Modality
            </label>
            <select
              id="patient-case-modality"
              value={modalityFilter}
              onChange={(event) => setModalityFilter(event.target.value)}
              className="min-h-11 w-full rounded-lg border border-rule-strong bg-white px-3 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
            >
              <option value="all">EEG and video</option>
              <option value="eeg">EEG</option>
              <option value="video">Video</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <p className="px-5 py-6 text-sm text-ink-muted" role="status">
          Loading patient cases…
        </p>
      ) : error ? (
        <div className="px-5 py-6" role="alert">
          <p className="text-sm leading-6 text-ink-muted">{error}</p>
          <Button
            type="button"
            variant="outline"
            className="mt-4 min-h-11"
            onClick={onRetry}
          >
            Retry loading patients
          </Button>
        </div>
      ) : items.length === 0 ? (
        <div className="px-5 py-8 sm:px-7" role="status">
          <p className="text-base font-semibold text-ink">{emptyTitle}</p>
          <p className="mt-1 max-w-xl text-sm leading-6 text-ink-muted">
            {emptyDescription}
          </p>
          <Button
            asChild
            className="mt-4 min-h-11 bg-teal-dark text-white hover:bg-teal-dark/90"
          >
            <Link href="/upload">
              <Icon name="upload" className="size-4" />
              Start a patient review
            </Link>
          </Button>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="px-5 py-7" role="status">
          <p className="text-base font-semibold text-ink">
            No cases match these filters.
          </p>
          <Button
            type="button"
            variant="outline"
            className="mt-3 min-h-11"
            onClick={clearFilters}
          >
            Clear search and filters
          </Button>
        </div>
      ) : (
        <ul className="divide-y divide-rule">
          {filteredItems.map((patient) => {
            const name =
              patient.patientName?.trim() || `Case ${patient.caseId.slice(-8)}`;
            return (
              <li
                key={patient.caseId}
                className="px-4 py-3 transition-colors hover:bg-surface-soft/70 sm:px-6 sm:py-4"
              >
                <div className="flex items-center gap-2 sm:gap-3">
                  <Link
                    href={`/cases/${encodeURIComponent(patient.caseId)}`}
                    className="group grid min-w-0 flex-1 gap-3 rounded-lg px-1 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 md:grid-cols-[minmax(0,1.45fr)_minmax(11rem,1fr)_minmax(10rem,0.9fr)_minmax(10rem,1fr)] md:items-center md:gap-4"
                  >
                    <div className="min-w-0">
                      <span className="block break-words text-base font-semibold text-ink group-hover:text-teal-dark">
                        {name}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-ink-muted">
                        {patient.patientName
                          ? `Case ${patient.caseId.slice(-8)} · Name from report`
                          : "Patient name not found in report"}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted md:sr-only">
                        Evidence
                      </span>
                      <p className="mt-0.5 text-sm font-medium text-ink">
                        {patient.eegRecordingCount ?? "—"} EEG ·{" "}
                        {patient.videoClipCount ?? "—"} video
                      </p>
                    </div>
                    <div className="min-w-0">
                      <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted md:sr-only">
                        Review status
                      </span>
                      <div className="mt-0.5 flex flex-wrap items-center gap-2">
                        <CaseStatusBadge status={patient.status} />
                        {patient.flaggedIntervalCount > 0 && (
                          <span className="text-xs font-semibold text-amber">
                            {patient.flaggedIntervalCount} EEG{" "}
                            {patient.flaggedIntervalCount === 1
                              ? "window"
                              : "windows"}{" "}
                            flagged
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs leading-5 text-ink-muted">
                        {patient.explanationReady
                          ? "Results available"
                          : "Results not ready"}
                      </p>
                    </div>
                    <div className="flex min-w-0 items-center justify-between gap-3 md:block">
                      <div className="min-w-0">
                        <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted md:sr-only">
                          Latest upload or job
                        </span>
                        <p className="mt-0.5 truncate text-xs text-ink-muted">
                          {formatCreatedAt(patient.latestCreatedAt)}
                        </p>
                      </div>
                      <span className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-teal-dark">
                        Open <Icon name="arrow" className="size-4" />
                      </span>
                    </div>
                  </Link>
                  <DeleteCaseAction
                    patientName={name}
                    onDelete={() => onDelete(patient.caseId)}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
