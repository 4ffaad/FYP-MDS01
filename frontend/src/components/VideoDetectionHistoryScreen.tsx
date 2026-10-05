"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import {
  listDetections,
  type DetectionJob,
  videoJobFailureMessage,
} from "@/lib/video-detection";
import { ModalityWorkspaceTabs } from "./ModalityWorkspaceTabs";

function submittedLabel(value: string) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/** List owner-scoped video analyses and their protected review outputs. */
export function VideoDetectionHistoryScreen() {
  const [jobs, setJobs] = useState<DetectionJob[]>([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void listDetections(controller.signal)
      .then(({ jobs: items }) => {
        if (!controller.signal.aborted) {
          setJobs(items);
          setError(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [refreshKey]);

  return (
    <div className="page-frame">
      <header>
        <p className="eyebrow">Video workspace</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Video reviews
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
          Past uploads, model scores, and protected review videos.
        </p>
        <ModalityWorkspaceTabs modality="video" active="reviews" />
      </header>

      {error ? (
        <section className="panel mt-6 p-6" role="alert">
          <h2 className="font-semibold text-ink">Reviews unavailable</h2>
          <p className="mt-2 text-sm text-ink-muted">
            Video reviews could not be loaded.
          </p>
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
        <section className="panel mt-6 p-6" aria-live="polite">
          <p className="text-sm text-ink-muted">Loading video reviews…</p>
        </section>
      ) : jobs.length ? (
        <ul className="mt-6 divide-y divide-rule overflow-hidden rounded-2xl border border-rule bg-surface">
          {jobs.map((job) => (
            <li key={job.job_id}>
              <Link
                href={`/video-detection/${encodeURIComponent(job.job_id)}`}
                className="flex min-h-20 flex-wrap items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-ink">
                    {job.label}
                  </span>
                  <span className="mt-1 block text-xs text-ink-muted">
                    {submittedLabel(job.created_at)}
                    {job.duration_seconds > 0 &&
                      ` · ${Math.floor(job.duration_seconds / 60)}:${String(Math.floor(job.duration_seconds % 60)).padStart(2, "0")}`}
                  </span>
                  {job.error && (
                    <span className="mt-2 block max-w-2xl text-xs leading-5 text-red">
                      {videoJobFailureMessage(
                        job.status === "expired" ? "expired" : "failed",
                        job.error,
                      )}
                    </span>
                  )}
                </span>
                <span className="inline-flex items-center gap-2 text-xs font-semibold capitalize text-ink-muted">
                  {job.status.replaceAll("_", " ")}
                  <Icon name="arrow" className="size-4" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <section className="panel mt-6 p-7 text-center">
          <Icon name="video" className="mx-auto size-8 text-teal-dark" />
          <h2 className="mt-3 text-lg font-semibold text-ink">
            No video reviews yet
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-ink-muted">
            Upload a clip to see its score timeline and protected review video
            here.
          </p>
          <Button asChild className="mt-5">
            <Link href="/video-detection">Upload a video</Link>
          </Button>
        </section>
      )}

      <p className="mt-8 text-xs leading-5 text-ink-muted">
        Research output only · not a diagnosis.
      </p>
    </div>
  );
}
