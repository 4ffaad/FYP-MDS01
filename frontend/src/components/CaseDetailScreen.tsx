"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCase } from "@/lib/api";
import type { CaseDetail } from "@/lib/types";
import { Icon } from "./Icon";
import { Status } from "./CasesScreen";

export function CaseDetailScreen({ caseId }: { caseId: string }) {
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getCase(caseId, controller.signal)
      .then(setCaseData)
      .catch((loadError) => {
        if (
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        )
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Case could not be loaded.",
          );
      });
    return () => controller.abort();
  }, [caseId]);

  if (error)
    return (
      <div className="page-frame">
        <div
          className="rounded-xl border border-red/30 bg-red-soft p-5 text-sm text-red"
          role="alert"
        >
          {error}
        </div>
      </div>
    );
  if (!caseData)
    return (
      <div className="page-frame">
        <div
          className="h-64 animate-pulse rounded-2xl border border-rule bg-surface"
          aria-label="Loading case"
        />
      </div>
    );

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link
          href="/cases"
          className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline underline-offset-4"
        >
          <Icon name="back" className="size-4" />
          Back to cases
        </Link>
        <header className="mt-6 max-w-3xl">
          <p className="eyebrow">Case history</p>
          <h1 className="mt-3 font-mono text-[clamp(2rem,5vw,3rem)] font-semibold tracking-[-0.05em]">
            {caseData.caseId}
          </h1>
          <p className="mt-4 text-[0.98rem] leading-7 text-ink-muted">
            A privacy-safe timeline of analyses associated with this workspace
            case. Patient identifiers and original source metadata are
            intentionally unavailable here.
          </p>
        </header>

        <section
          className="panel mt-8 overflow-hidden"
          aria-labelledby="history-heading"
        >
          <div className="border-b border-rule px-5 py-5 sm:px-7">
            <h2 id="history-heading" className="text-base font-bold">
              Analysis history
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              {caseData.analyses.length}{" "}
              {caseData.analyses.length === 1 ? "analysis" : "analyses"} ·
              independent privacy and model pipelines
            </p>
          </div>
          <div className="divide-y divide-rule">
            {caseData.analyses.map((analysis) => (
              <div
                key={analysis.id}
                className="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7"
              >
                <div className="flex items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-soft text-teal">
                    <Icon
                      name={analysis.modality === "eeg" ? "activity" : "file"}
                      className="size-5"
                    />
                  </span>
                  <div>
                    <p className="font-semibold text-ink">
                      {analysis.modality === "eeg"
                        ? "EEG analysis"
                        : "Video analysis"}
                    </p>
                    <p className="mt-1 font-mono text-xs text-ink-faint">
                      {analysis.id}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {formatDate(analysis.createdAt)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 sm:text-right">
                  <Status status={analysis.status} />
                  <span className="text-xs text-ink-muted">
                    {analysis.reviewReady ? "Review ready" : "Still processing"}
                  </span>
                  {analysis.modality === "eeg" && (
                    <Link
                      href={`/sessions/${encodeURIComponent(analysis.id)}`}
                      className="text-xs font-bold text-teal-dark underline underline-offset-4"
                    >
                      Open
                    </Link>
                  )}
                  {analysis.modality === "video" && (
                    <Link
                      href={`/video-detection/${encodeURIComponent(analysis.id)}`}
                      className="text-xs font-bold text-teal-dark underline underline-offset-4"
                    >
                      Open
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
