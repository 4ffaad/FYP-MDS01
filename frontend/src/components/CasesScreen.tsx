"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MotionConfig, motion } from "motion/react";
import { getCases } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { Icon } from "./Icon";
import { LoadingOrb } from "./LoadingOrb";
import { Button } from "@/components/ui/button";

export function CasesScreen() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void getCases(controller.signal)
      .then(setCases)
      .catch((loadError) => {
        if (
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        )
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Cases could not be loaded.",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [loadAttempt]);

  function retryCases() {
    setCases([]);
    setLoading(true);
    setError(null);
    setLoadAttempt((attempt) => attempt + 1);
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame">
        <motion.main
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <header className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <div className="max-w-2xl">
              <p className="eyebrow">Longitudinal review</p>
              <h1 className="mt-3 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.04] tracking-[-0.05em]">
                Patient history
              </h1>
              <p className="mt-4 text-[0.98rem] leading-7 text-ink-muted">
                Find a patient by name, scan the report summary, and open the
                complete review history. Internal case identifiers stay out of
                the interface.
              </p>
            </div>
            <Button asChild>
              <Link href="/upload">
                <Icon name="upload" className="size-4" />
                New patient review
              </Link>
            </Button>
          </header>

          <section
            className="panel mt-8 overflow-hidden"
            aria-labelledby="cases-heading"
          >
            <div className="flex items-center justify-between border-b border-rule px-5 py-5 sm:px-7">
              <div>
                <h2 id="cases-heading" className="text-base font-bold">
                  All patient reviews
                </h2>
                <p className="mt-1 text-sm text-ink-muted">
                  {cases.length}{" "}
                  {cases.length === 1 ? "patient review" : "patient reviews"}
                </p>
              </div>
            </div>
            {loading ? (
              <div className="flex min-h-64 items-center justify-center px-5 py-12">
                <LoadingOrb
                  label="Loading patient history…"
                  state="searching"
                  size={64}
                />
              </div>
            ) : error ? (
              <div
                className="px-5 py-12 sm:px-7"
                role="alert"
                aria-live="assertive"
              >
                <h3 className="text-lg font-semibold tracking-tight">
                  Patient history could not be loaded
                </h3>
                <p className="mt-2 max-w-xl text-sm leading-6 text-ink-muted">
                  {error} Try again before treating this workspace as empty.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  className="mt-5"
                  onClick={retryCases}
                >
                  Retry loading patients
                  <Icon name="arrow" className="size-4" />
                </Button>
              </div>
            ) : cases.length === 0 ? (
              <div className="px-5 py-16 sm:px-7">
                <p className="eyebrow">Your workspace</p>
                <h3 className="mt-3 text-xl font-semibold tracking-tight">
                  No patient reviews yet
                </h3>
                <p className="mt-2 max-w-md text-sm leading-6 text-ink-muted">
                  Start with one patient folder. Reports, every supported EEG
                  recording, and VSViG video analyses stay together in its
                  review history.
                </p>
                <Button asChild variant="outline" className="mt-6">
                  <Link href="/upload">
                    Create first patient review{" "}
                    <Icon name="arrow" className="size-4" />
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-rule">
                {cases.map((item) => (
                  <CaseRow key={item.caseId} item={item} />
                ))}
              </div>
            )}
          </section>
          <p className="mt-5 text-xs leading-5 text-ink-muted">
            Patient names and report summaries are shown only inside this
            owner-scoped workspace.
          </p>
        </motion.main>
      </div>
    </MotionConfig>
  );
}

function CaseRow({ item }: { item: CaseSummary }) {
  return (
    <Link
      href={`/cases/${encodeURIComponent(item.caseId)}`}
      className="group grid gap-4 px-5 py-5 transition-colors hover:bg-surface-soft/75 focus-visible:bg-surface-soft sm:px-7"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold tracking-tight text-ink">
              {item.patientName?.trim() || "Patient review"}
            </h3>
            {item.patientNameVerificationStatus === "auto_extracted" && (
              <span className="rounded-full bg-amber-soft/60 px-2.5 py-1 text-[0.65rem] font-semibold text-ink-muted">
                Name auto-extracted · not verified
              </span>
            )}
            <Status status={item.status} />
          </div>
          <p className="mt-2 line-clamp-2 max-w-4xl text-sm leading-6 text-ink-muted">
            {item.reportSummary?.trim() ||
              "Open the report and analysis history."}
          </p>
        </div>
        <Icon
          name="arrow"
          className="mt-1 size-4 shrink-0 text-teal transition-transform group-hover:translate-x-1"
        />
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-muted">
        <span>
          {item.modalities
            .map((modality) => modality.toUpperCase())
            .join(" + ")}
        </span>
        <span>
          {item.analysisCount}{" "}
          {item.analysisCount === 1 ? "analysis" : "analyses"}
        </span>
        <span>Updated {formatDate(item.latestCreatedAt)}</span>
        <span>
          {item.flaggedIntervalCount > 0
            ? `${item.flaggedIntervalCount} flagged windows`
            : "No flagged windows"}
        </span>
        <span>{item.explanationReady ? "Report ready" : "Processing"}</span>
      </div>
    </Link>
  );
}

export function Status({ status }: { status: CaseSummary["status"] }) {
  return (
    <span className="rounded-full bg-surface-soft px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-wide text-ink-muted">
      {status.replace("_", " ")}
    </span>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value));
}
