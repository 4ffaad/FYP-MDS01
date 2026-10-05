"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { getSessions, toDisplayStatus } from "@/lib/api";
import { formatSubmittedAt } from "@/lib/format";
import type { Session } from "@/lib/types";
import { Icon } from "./Icon";
import { StatusBadge } from "./StatusBadge";
import { ModalityWorkspaceTabs } from "./ModalityWorkspaceTabs";

export function EegSessionsScreen() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void getSessions(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setSessions(items);
        setError(null);
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "EEG sessions could not be loaded.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [refreshKey]);

  return (
    <div className="page-frame">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">EEG tools</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            EEG reviews
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
            Past EEG uploads, score timelines, and model sensitivity output.
          </p>
          <ModalityWorkspaceTabs modality="eeg" active="reviews" />
        </div>
      </header>

      {error ? (
        <section className="panel p-6" role="alert">
          <h2 className="font-semibold text-ink">Sessions unavailable</h2>
          <p className="mt-2 text-sm text-ink-muted">{error}</p>
          <Button
            className="mt-4"
            variant="outline"
            onClick={() => {
              setLoading(true);
              setRefreshKey((value) => value + 1);
            }}
          >
            <Icon name="refresh" className="size-4" />
            Try again
          </Button>
        </section>
      ) : loading ? (
        <section className="panel p-6" aria-live="polite">
          <p className="text-sm text-ink-muted">Loading EEG sessions…</p>
        </section>
      ) : sessions.length === 0 ? (
        <section className="panel p-7 text-center">
          <Icon name="activity" className="mx-auto size-8 text-teal-dark" />
          <h2 className="mt-3 text-lg font-semibold text-ink">
            No EEG sessions yet
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-ink-muted">
            EEG analysis appears here after a patient review is submitted.
          </p>
          <Button asChild className="mt-5">
            <Link href="/upload/eeg">Start EEG analysis</Link>
          </Button>
        </section>
      ) : (
        <section className="panel overflow-hidden" aria-label="EEG sessions">
          <ul className="divide-y divide-rule">
            {sessions.map((session) => (
              <li
                key={session.sessionId}
                className="flex flex-wrap items-center justify-between gap-4 p-5 sm:px-6"
              >
                <div className="flex min-w-0 items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-soft text-teal-dark shadow-hard-sm">
                    <Icon name="activity" className="size-5" />
                  </span>
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-semibold text-ink">
                      {session.progress.totalRecordings} EEG recordings
                    </h2>
                    <p className="mt-1 text-xs text-ink-muted">
                      {formatSubmittedAt(session.createdAt)}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {session.progress.completedRecordings} complete ·{" "}
                      {session.progress.failedRecordings} need review
                    </p>
                  </div>
                </div>
                <div className="flex w-full items-center justify-between gap-3 sm:w-auto sm:justify-end">
                  <StatusBadge status={toDisplayStatus(session.status)} />
                  <Button asChild variant="outline">
                    <Link
                      href={`/sessions/${encodeURIComponent(session.sessionId)}`}
                    >
                      Open session
                      <Icon name="arrow" className="size-4" />
                    </Link>
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
