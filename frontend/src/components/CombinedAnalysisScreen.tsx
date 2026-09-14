"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/api";
import { getDetection, type DetectionJob } from "@/lib/video-detection";
import type { Session } from "@/lib/types";
import { Icon } from "./Icon";
import { Button } from "@/components/ui/button";

const ACTIVE_EEG = new Set([
  "queued",
  "validating",
  "deidentifying",
  "preprocessing",
  "inference",
  "explaining",
]);
const ACTIVE_VIDEO = new Set([
  "queued",
  "preflight",
  "processing",
  "validating",
]);

/** Present the two existing owner-scoped jobs as one review hand-off. */
export function CombinedAnalysisScreen({
  sessionId,
  videoJobId,
}: {
  sessionId?: string;
  videoJobId?: string;
}) {
  const [session, setSession] = useState<Session | null>(null);
  const [videoJob, setVideoJob] = useState<DetectionJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId && !videoJobId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let mounted = true;

    async function load() {
      try {
        const [eegResult, videoResult] = await Promise.all([
          sessionId
            ? getSession(sessionId, controller.signal)
            : Promise.resolve(null),
          videoJobId
            ? getDetection(videoJobId, controller.signal)
            : Promise.resolve(null),
        ]);
        if (!mounted) return;
        setSession(eegResult);
        const nextVideoJob = videoResult?.job ?? null;
        setVideoJob(nextVideoJob);
        setError(null);
        if (
          (eegResult && ACTIVE_EEG.has(eegResult.status)) ||
          (nextVideoJob && ACTIVE_VIDEO.has(nextVideoJob.status))
        ) {
          timer = setTimeout(() => void load(), 2500);
        }
      } catch (loadError) {
        if (
          mounted &&
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        )
          setError(
            loadError instanceof Error
              ? loadError.message
              : "The combined analysis could not be loaded.",
          );
      }
    }

    void load();
    return () => {
      mounted = false;
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [sessionId, videoJobId]);

  if (!sessionId && !videoJobId)
    return (
      <AnalysisError message="This review link is missing its analysis IDs." />
    );

  return (
    <div className="page-frame">
      <div className="animate-enter-up">
        <Link
          className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
          href="/dashboard"
        >
          <Icon name="back" className="size-4" />
          Back to workspace
        </Link>
        <header className="mt-5 max-w-3xl">
          <p className="eyebrow">Combined review</p>
          <h1 className="mt-3 text-[clamp(2rem,5vw,2.8rem)] font-semibold leading-[1.05] tracking-[-0.05em]">
            Analysis report
          </h1>
          <p className="mt-4 text-[0.98rem] leading-7 text-ink-muted">
            EEG and video are processed independently, then brought together
            here so a reviewer can see the privacy and model state for each
            modality.
          </p>
        </header>

        {error && (
          <div
            className="mt-6 rounded-xl border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
            role="alert"
          >
            {error}
          </div>
        )}
        <div className="mt-9 grid gap-5 lg:grid-cols-2">
          {sessionId && (
            <AnalysisCard
              icon="activity"
              title="EEG analysis"
              status={session ? eegStatus(session.status) : "Loading"}
              detail={
                session
                  ? `${session.progress.completedRecordings} of ${session.progress.totalRecordings} recordings complete`
                  : "Loading the owner-scoped EEG session…"
              }
              steps={["Metadata scrub", "H5 model", "EEG report"]}
              href={
                session
                  ? `/sessions/${encodeURIComponent(session.sessionId)}`
                  : undefined
              }
              action="Open EEG session"
            />
          )}
          {videoJobId && (
            <AnalysisCard
              icon="activity"
              title="Video seizure review"
              status={videoJob ? videoStatus(videoJob.status) : "Loading"}
              detail={
                videoJob
                  ? videoJob.current_stage.replaceAll("-", " ")
                  : "Loading the owner-scoped video job…"
              }
              steps={["Face redaction", "VSViG model", "Evidence timeline"]}
              href={
                videoJob
                  ? `/video-detection/${encodeURIComponent(videoJob.job_id)}`
                  : undefined
              }
              action="Open video review"
            />
          )}
        </div>

        <section
          className="glass-panel mt-6 rounded-2xl border border-rule p-5 sm:p-6"
          aria-labelledby="report-note-heading"
        >
          <div className="flex items-start gap-3">
            <Icon name="info" className="mt-0.5 size-5 shrink-0 text-teal" />
            <div>
              <h2 id="report-note-heading" className="text-sm font-bold">
                How to read this report
              </h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">
                The cards are a shared status view, not a combined clinical
                result. Open each modality to review its own windows, intervals,
                model details, and privacy caveats.
              </p>
            </div>
          </div>
        </section>
        <p className="mt-6 text-xs leading-5 text-ink-muted">
          Research only · model output is not a diagnosis · no recording-level
          confidence is shown.
        </p>
      </div>
    </div>
  );
}

function AnalysisCard({
  icon,
  title,
  status,
  detail,
  steps,
  href,
  action,
}: {
  icon: "activity";
  title: string;
  status: string;
  detail: string;
  steps: string[];
  href?: string;
  action: string;
}) {
  return (
    <section className="panel glass-panel rounded-2xl border border-rule p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-ink text-white">
            <Icon name={icon} className="size-5" weight="bold" />
          </span>
          <div>
            <h2 className="text-lg font-bold">{title}</h2>
            <p className="mt-1 text-sm text-ink-muted">{detail}</p>
          </div>
        </div>
        <span className="rounded-full bg-surface-soft px-3 py-1 text-xs font-bold capitalize text-ink-muted">
          {status}
        </span>
      </div>
      <ol className="mt-7 grid gap-2 sm:grid-cols-3">
        {steps.map((step, index) => (
          <li
            key={step}
            className="rounded-xl border border-rule bg-surface-soft px-3 py-3 text-xs font-semibold text-ink-muted"
          >
            <span className="mr-2 text-teal">0{index + 1}</span>
            {step}
          </li>
        ))}
      </ol>
      {href ? (
        <Button asChild variant="outline" className="mt-6">
          <Link href={href}>
            {action}
            <Icon name="arrow" className="size-4" />
          </Link>
        </Button>
      ) : (
        <p className="mt-6 text-xs text-ink-faint">
          Waiting for the backend response…
        </p>
      )}
    </section>
  );
}

function eegStatus(status: Session["status"]) {
  if (status === "completed") return "Complete";
  if (status === "completed_with_errors") return "Needs review";
  if (status === "failed") return "Failed";
  return "Processing";
}

function videoStatus(status: DetectionJob["status"]) {
  if (status === "ready") return "Complete";
  if (status === "failed" || status === "expired")
    return status === "failed" ? "Failed" : "Expired";
  return "Processing";
}

function AnalysisError({ message }: { message: string }) {
  return (
    <div className="page-frame">
      <div
        className="max-w-xl rounded-2xl border border-red/30 bg-red-soft p-6"
        role="alert"
      >
        <Icon name="alert" className="size-6 text-red" />
        <h1 className="mt-4 text-xl font-bold">Analysis unavailable</h1>
        <p className="mt-2 text-sm leading-6 text-red">{message}</p>
        <Link
          className="mt-5 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-teal-dark underline underline-offset-4"
          href="/upload"
        >
          Start a new analysis <Icon name="arrow" className="size-4" />
        </Link>
      </div>
    </div>
  );
}
