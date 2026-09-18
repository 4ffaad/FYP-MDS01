"use client";

import { Label, ProgressBar, Spinner } from "@primer/react";
import { AnimatePresence, motion, MotionConfig } from "motion/react";
import { Icon } from "@/components/Icon";
import type { DetectionJob } from "@/lib/video-detection";

type StageIcon = "video" | "shield" | "activity" | "list";
type StageId =
  | "preflight"
  | "privacy-transform"
  | "pose-and-inference"
  | "complete";

type StageDefinition = {
  id: StageId;
  label: string;
  detail: string;
  icon: StageIcon;
  checkpoint: number;
};

const stages: StageDefinition[] = [
  {
    id: "preflight",
    label: "Check video",
    detail: "Validate the file, duration and frame rate.",
    icon: "video",
    checkpoint: 16,
  },
  {
    id: "privacy-transform",
    label: "Face redaction",
    detail: "Encrypt the source and protect frames before model input.",
    icon: "shield",
    checkpoint: 44,
  },
  {
    id: "pose-and-inference",
    label: "Pose + VSViG",
    detail: "Extract pose keypoints and score the protected visual windows.",
    icon: "activity",
    checkpoint: 78,
  },
  {
    id: "complete",
    label: "Evidence timeline",
    detail: "Assemble scores, flagged intervals and model evidence.",
    icon: "list",
    checkpoint: 100,
  },
];

const knownStageIds = new Set<string>(stages.map((stage) => stage.id));

function clampProgress(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function stageIndex(stageId: string) {
  return stages.findIndex((stage) => stage.id === stageId);
}

function getJobStage(job: DetectionJob): StageDefinition {
  if (job.status === "ready" || job.current_stage === "complete") {
    return stages[stages.length - 1];
  }

  if (knownStageIds.has(job.current_stage)) {
    return stages[stages.findIndex((stage) => stage.id === job.current_stage)];
  }

  return stages[0];
}

function getStatusLabel(job: DetectionJob) {
  if (job.status === "ready") return "Complete";
  if (job.status === "failed") return "Stopped";
  if (job.status === "expired") return "Expired";
  if (job.status === "queued") return "Queued";
  return "Processing";
}

function getLabelVariant(job: DetectionJob) {
  if (job.status === "ready") return "success" as const;
  if (job.status === "failed") return "danger" as const;
  if (job.status === "expired") return "attention" as const;
  return "accent" as const;
}

function isTerminal(job: DetectionJob) {
  return job.status === "failed" || job.status === "expired";
}

export function VideoJobLoadingState() {
  return (
    <MotionConfig reducedMotion="user">
      <motion.section
        className="video-job-loading-state panel mt-6 overflow-hidden p-5 sm:p-7"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        aria-live="polite"
      >
        <div className="flex items-center gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-teal-soft text-teal">
            <Spinner size="medium" srText="Loading video review" />
          </span>
          <div>
            <p className="eyebrow">Secure review queue</p>
            <h2 className="mt-1 text-lg font-semibold">
              Connecting to the job
            </h2>
          </div>
        </div>
        <p className="mt-5 text-sm leading-6 text-ink-muted">
          Loading the server status. The model will not receive the video until
          the private processing pipeline accepts it.
        </p>
        <ProgressTrack
          progress={8}
          label="Connecting to the video review queue"
          valueText="Starting"
          animated
        />
      </motion.section>
    </MotionConfig>
  );
}

export function VideoUploadStatus({
  progress,
  phase = "uploading",
}: {
  progress: number;
  phase?: "preparing" | "uploading";
}) {
  const currentProgress = clampProgress(progress);
  const preparing = phase === "preparing";
  const uploadAcknowledged = !preparing && currentProgress >= 100;

  return (
    <MotionConfig reducedMotion="user">
      <motion.section
        className="video-upload-status panel overflow-hidden p-5 sm:p-7"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        aria-live="polite"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Secure video handoff</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">
              {preparing
                ? "Preparing the paired review"
                : uploadAcknowledged
                  ? "Waiting for the private API"
                  : "Sending video securely"}
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-ink-muted">
              {preparing
                ? "The selected EEG analysis is being handed off first. Video upload begins next."
                : uploadAcknowledged
                  ? "The upload is complete. The backend is acknowledging the file and creating the processing job."
                  : "The selected video is moving from your browser to the private backend. Audio is not used by the visual model."}
            </p>
          </div>
          <StatusMark
            label={
              preparing
                ? "Preparing"
                : uploadAcknowledged
                  ? "Received"
                  : "Uploading"
            }
            variant={
              preparing
                ? "attention"
                : uploadAcknowledged
                  ? "success"
                  : "accent"
            }
            spinning={!uploadAcknowledged}
          />
        </div>

        <ProgressTrack
          progress={preparing ? 0 : currentProgress}
          label="Video upload progress"
          valueText={preparing ? "Waiting" : `${currentProgress}%`}
          animated={!uploadAcknowledged}
        />

        <ol
          className="mt-6 grid gap-3 sm:grid-cols-3"
          aria-label="Video upload steps"
        >
          <UploadStep
            index="01"
            title="Browser transfer"
            detail="Upload bytes"
            state={
              preparing ? "pending" : uploadAcknowledged ? "complete" : "active"
            }
          />
          <UploadStep
            index="02"
            title="Private receipt"
            detail="Encrypt and validate"
            state={preparing || !uploadAcknowledged ? "pending" : "active"}
          />
          <UploadStep
            index="03"
            title="Review queue"
            detail="Start model pipeline"
            state="pending"
          />
        </ol>
      </motion.section>
    </MotionConfig>
  );
}

export function VideoProcessingStatus({ job }: { job: DetectionJob }) {
  const activeStage = getJobStage(job);
  const activeIndex = stageIndex(activeStage.id);
  const complete = job.status === "ready";
  const terminal = isTerminal(job);
  const progress = complete
    ? 100
    : terminal
      ? 0
      : Math.min(activeStage.checkpoint, 99);
  const stagePosition = complete ? stages.length : Math.max(activeIndex + 1, 1);
  const statusLabel = getStatusLabel(job);
  const statusDescription = complete
    ? "The protected video has been scored and the evidence timeline is ready for review."
    : terminal
      ? "No active processing remains. Review the message below before submitting another clip."
      : activeStage.detail;

  return (
    <MotionConfig reducedMotion="user">
      <motion.section
        className="video-processing-card panel mt-6 overflow-hidden"
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.36, ease: "easeOut" }}
        aria-labelledby="video-processing-heading"
      >
        <div className="border-b border-rule bg-surface-soft/80 px-5 py-5 sm:px-7">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-2xl">
              <p className="eyebrow">Live processing pipeline</p>
              <h2
                id="video-processing-heading"
                className="mt-1 text-xl font-semibold tracking-tight sm:text-2xl"
              >
                {complete
                  ? "Video review is ready"
                  : "Building your video review"}
              </h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">
                {complete
                  ? "Review the timeline below. Scores remain uncalibrated research evidence and require human review."
                  : "The server reports each handoff as it completes. This percentage represents pipeline checkpoints; model inference does not currently expose frame-by-frame progress."}
              </p>
            </div>
            <StatusMark
              label={statusLabel}
              variant={getLabelVariant(job)}
              spinning={!complete && !terminal}
            />
          </div>

          <ProgressTrack
            progress={progress}
            label="Video review completion"
            valueText={terminal ? "Unavailable" : `${progress}%`}
            animated={!complete && !terminal}
          />

          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={`${job.status}-${activeStage.id}`}
              className="mt-5 flex items-start gap-3 rounded-xl border border-teal/20 bg-teal-soft/45 px-4 py-3"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              <Icon
                name={
                  complete ? "check" : terminal ? "alert" : activeStage.icon
                }
                className="mt-0.5 size-5 shrink-0 text-teal"
                weight="bold"
              />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">
                  {complete
                    ? "Evidence timeline assembled"
                    : terminal
                      ? statusLabel
                      : activeStage.label}
                </p>
                <p className="mt-1 text-xs leading-5 text-ink-muted">
                  {terminal
                    ? "The server did not publish a detection result."
                    : statusDescription}
                </p>
              </div>
              {!terminal && (
                <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-teal-dark">
                  {stagePosition}/{stages.length}
                </span>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <motion.ol
          className="grid gap-3 px-5 py-5 sm:grid-cols-2 sm:px-7 lg:grid-cols-4"
          aria-label="Video review processing steps"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.07 } },
          }}
        >
          {stages.map((stage, index) => {
            const state =
              complete || index < activeIndex
                ? "complete"
                : !terminal && index === activeIndex
                  ? "active"
                  : "pending";

            return (
              <ProcessingStep
                key={stage.id}
                stage={stage}
                state={state}
                index={index}
              />
            );
          })}
        </motion.ol>

        <div className="border-t border-rule bg-surface-soft px-5 py-4 sm:px-7">
          <p className="flex items-start gap-2 text-xs leading-5 text-ink-muted">
            <Icon name="info" className="mt-0.5 size-4 shrink-0 text-teal" />
            <span>
              <span className="font-semibold text-ink">Model handoff:</span>{" "}
              VSViG is selected and run on the protected server after pose
              extraction. You do not need to choose a checkpoint or enter a
              filesystem path. Its scores are not a diagnosis.
            </span>
          </p>
        </div>
      </motion.section>
    </MotionConfig>
  );
}

function ProgressTrack({
  progress,
  label,
  valueText,
  animated,
}: {
  progress: number;
  label: string;
  valueText: string;
  animated: boolean;
}) {
  return (
    <div className="mt-6" aria-live="polite">
      <div className="flex items-center justify-between gap-3 text-xs text-ink-muted">
        <span>{label}</span>
        <strong className="font-mono tabular-nums text-ink">{valueText}</strong>
      </div>
      <div className="video-progress-primer mt-2">
        <ProgressBar
          progress={clampProgress(progress)}
          animated={animated}
          barSize="large"
          aria-label={label}
          aria-valuetext={valueText}
        />
      </div>
    </div>
  );
}

function StatusMark({
  label,
  variant,
  spinning,
}: {
  label: string;
  variant: "accent" | "attention" | "danger" | "success";
  spinning: boolean;
}) {
  return (
    <div className="video-status-mark flex items-center gap-2">
      {spinning && <Spinner size="small" srText={label} />}
      <Label variant={variant} size="large">
        {label}
      </Label>
    </div>
  );
}

function UploadStep({
  index,
  title,
  detail,
  state,
}: {
  index: string;
  title: string;
  detail: string;
  state: "active" | "complete" | "pending";
}) {
  return (
    <motion.li
      className={`rounded-xl border px-3 py-3 ${state === "active" ? "border-teal/35 bg-teal-soft/45" : state === "complete" ? "border-teal/20 bg-surface" : "border-rule bg-surface-soft"}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      <div className="flex items-start gap-3">
        <span
          className={`font-mono text-xs font-semibold ${state === "pending" ? "text-ink-faint" : "text-teal-dark"}`}
        >
          {state === "complete" ? "✓" : index}
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink">{title}</span>
          <span className="mt-1 block text-xs text-ink-muted">{detail}</span>
        </span>
      </div>
    </motion.li>
  );
}

function ProcessingStep({
  stage,
  state,
  index,
}: {
  stage: StageDefinition;
  state: "active" | "complete" | "pending";
  index: number;
}) {
  return (
    <motion.li
      className={`relative rounded-xl border px-3 py-3 ${state === "active" ? "border-teal/35 bg-teal-soft/45" : state === "complete" ? "border-teal/20 bg-surface" : "border-rule bg-surface-soft"}`}
      variants={{
        hidden: { opacity: 0, y: 8 },
        visible: { opacity: 1, y: 0 },
      }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      <div className="flex items-start gap-3">
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-lg ${state === "active" ? "bg-teal text-white" : state === "complete" ? "bg-teal-soft text-teal-dark" : "bg-surface text-ink-faint"}`}
        >
          {state === "complete" ? (
            <Icon name="check" className="size-4" weight="bold" />
          ) : state === "active" ? (
            <motion.span
              animate={{ scale: [1, 1.08, 1] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            >
              <Icon name={stage.icon} className="size-4" weight="bold" />
            </motion.span>
          ) : (
            <span className="font-mono text-xs">0{index + 1}</span>
          )}
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink">
            {stage.label}
          </span>
          <span className="mt-1 block text-xs leading-5 text-ink-muted">
            {stage.detail}
          </span>
        </span>
      </div>
      {state === "active" && (
        <span className="mt-3 block text-[0.65rem] font-bold tracking-[0.08em] text-teal-dark uppercase">
          In progress
        </span>
      )}
    </motion.li>
  );
}
