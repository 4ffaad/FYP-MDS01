"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { WorkspacePatients } from "@/components/WorkspacePatients";
import { deleteCase, getCases } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { Icon } from "./Icon";

export function VeegWorkspaceScreen() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void getCases(controller.signal)
      .then((caseItems) => {
        if (controller.signal.aborted) return;
        setCases(caseItems);
        setError(null);
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Patient cases could not be loaded.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [refreshKey]);

  const retry = useCallback(() => {
    setLoading(true);
    setRefreshKey((value) => value + 1);
  }, []);

  async function removeCase(caseId: string) {
    await deleteCase(caseId);
    setCases((items) => items.filter((item) => item.caseId !== caseId));
  }

  return (
    <div className="page-frame space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Patient workspace</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Patient cases
          </h1>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Browse combined, EEG-only, and video-only reviews.
          </p>
        </div>
        <Button asChild className="min-h-11 bg-teal-dark text-white">
          <Link href="/upload">
            <Icon name="upload" className="size-4" />
            New combined review
          </Link>
        </Button>
      </header>

      <WorkspacePatients
        items={cases}
        loading={loading}
        error={error}
        onRetry={retry}
        onDelete={removeCase}
        heading="All patient cases"
      />
    </div>
  );
}
