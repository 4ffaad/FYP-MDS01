"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCases } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { Icon } from "./Icon";
import { Button } from "@/components/ui/button";

export function CasesScreen() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <header className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div className="max-w-2xl">
            <p className="eyebrow">Longitudinal review</p>
            <h1 className="mt-3 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.04] tracking-[-0.05em]">
              Cases
            </h1>
            <p className="mt-4 text-[0.98rem] leading-7 text-ink-muted">
              Follow privacy-safe analysis history across VEEG, video, and model
              explanations. Case IDs are opaque and contain no patient
              information.
            </p>
          </div>
          <Button asChild>
            <Link href="/upload">
              <Icon name="upload" className="size-4" />
              New analysis
            </Link>
          </Button>
        </header>

        {error && (
          <div
            className="mt-7 rounded-xl border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
            role="alert"
          >
            {error}
          </div>
        )}
        <section
          className="panel mt-8 overflow-hidden"
          aria-labelledby="cases-heading"
        >
          <div className="flex items-center justify-between border-b border-rule px-5 py-5 sm:px-7">
            <div>
              <h2 id="cases-heading" className="text-base font-bold">
                Analysis history
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                {cases.length} {cases.length === 1 ? "case" : "cases"} in this
                workspace
              </p>
            </div>
            <Icon name="shield" className="size-5 text-teal" />
          </div>
          {loading ? (
            <div
              className="h-64 animate-pulse bg-surface-soft"
              aria-label="Loading cases"
            />
          ) : cases.length === 0 ? (
            <div className="px-5 py-16 sm:px-7">
              <h3 className="text-lg font-semibold">No cases yet.</h3>
              <p className="mt-2 max-w-md text-sm leading-6 text-ink-muted">
                Start an analysis with VEEG, video, or both. Your case will
                appear here with its privacy and explanation trail.
              </p>
              <Button asChild variant="outline" className="mt-6">
                <Link href="/upload">
                  Start a new analysis <Icon name="arrow" className="size-4" />
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
          Research only · cases use de-identified workspace IDs. Original
          patient identifiers are never displayed.
        </p>
      </div>
    </div>
  );
}

function CaseRow({ item }: { item: CaseSummary }) {
  return (
    <Link
      href={`/cases/${encodeURIComponent(item.caseId)}`}
      className="flex flex-col gap-4 px-5 py-5 transition-colors hover:bg-surface-soft sm:flex-row sm:items-center sm:justify-between sm:px-7"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-mono text-sm font-bold text-ink">
            {item.caseId}
          </h3>
          <Status status={item.status} />
        </div>
        <p className="mt-2 text-sm text-ink-muted">
          {item.modalities
            .map((modality) => modality.toUpperCase())
            .join(" + ")}{" "}
          · {item.analysisCount}{" "}
          {item.analysisCount === 1 ? "analysis" : "analyses"}
        </p>
      </div>
      <div className="flex items-center gap-6 text-xs text-ink-muted sm:text-right">
        <span>
          {item.flaggedIntervalCount > 0
            ? `${item.flaggedIntervalCount} flagged`
            : "No flags reported"}
        </span>
        <span>
          {item.explanationReady ? "Explanation ready" : "Processing"}
        </span>
        <Icon name="arrow" className="size-4 text-teal" />
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
