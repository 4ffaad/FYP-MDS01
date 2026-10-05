import { expect, test } from "@playwright/test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

type SyntheticSessionStatus =
  | "processing"
  | "completed"
  | "completed_with_errors"
  | "failed";

type SyntheticSessionProgress = {
  total_recordings: number;
  finished_recordings: number;
  completed_recordings: number;
  failed_recordings: number;
  percent: number;
};

function syntheticSession({
  sessionId,
  caseId,
  createdAt,
  status,
  progress,
  currentStage,
  completedAt,
  errorMessage,
  processingAttempts = [],
}: {
  sessionId: string;
  caseId: string;
  createdAt: string;
  status: SyntheticSessionStatus;
  progress: SyntheticSessionProgress;
  currentStage?: string;
  completedAt?: string | null;
  errorMessage?: string | null;
  processingAttempts?: Array<{
    recording_sequence_index: number | null;
    stage: string;
    status: "pending" | "running" | "succeeded" | "failed";
    started_at: string | null;
    finished_at: string | null;
  }>;
}) {
  const terminal = status !== "processing";
  return {
    session_id: sessionId,
    case_id: caseId,
    privacy_method: "metadata-scrub",
    privacy_methods: ["metadata-scrub"],
    status,
    current_stage:
      currentStage ??
      (status === "failed" ? "failed" : terminal ? "complete" : "inference"),
    created_at: createdAt,
    completed_at:
      completedAt === undefined
        ? terminal && status !== "failed"
          ? createdAt
          : null
        : completedAt,
    error_message:
      errorMessage === undefined
        ? status === "failed"
          ? "Synthetic processing failure."
          : null
        : errorMessage,
    progress,
    summary: { model_alert_recordings: 0 },
    processing_attempts: processingAttempts,
    recordings: [],
  };
}

test("expired and rejected video outcomes stay distinct and show review issues", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted upload workflow.",
  );

  const createdAt = "2026-09-27T00:00:00Z";
  const expiresAt = "2026-09-28T00:00:00Z";
  let reportPosts = 0;
  let detectionPosts = 0;
  let draftPosts = 0;
  let profileSaves = 0;
  let profileVerificationStatus: string | null = null;
  const firstJob = {
    job_id: "VID-RECHECK-SYNTHETIC-1",
    case_id: "CASE-RECHECK-SYNTHETIC",
    label: "Video 1",
    status: "queued",
    current_stage: "preflight",
    duration_seconds: 10,
    fps: 30,
    created_at: createdAt,
    retention_expires_at: expiresAt,
    video_available: false,
    error: null as string | null,
  };

  await page.route("**/api/patient-report", (route) => {
    reportPosts += 1;
    return route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    });
  });
  await page.route("**/api/uploads/drafts", (route) => {
    if (route.request().method() === "POST") draftPosts += 1;
    return route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-RECHECK-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: expiresAt,
      },
    });
  });
  await page.route(
    "**/api/uploads/drafts/UPL-RECHECK-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-RECHECK-SYNTHETIC",
          case_id: "CASE-RECHECK-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-RECHECK-SYNTHETIC", (route) =>
    route.fulfill({
      json: syntheticSession({
        sessionId: "MDS-RECHECK-SYNTHETIC",
        caseId: "CASE-RECHECK-SYNTHETIC",
        createdAt,
        status: "completed_with_errors",
        progress: {
          total_recordings: 2,
          finished_recordings: 2,
          completed_recordings: 1,
          failed_recordings: 1,
          percent: 100,
        },
      }),
    }),
  );
  await page.route(
    "**/api/cases/CASE-RECHECK-SYNTHETIC/patient-profile/extracted",
    async (route) => {
      const body = route.request().postDataJSON() as {
        details?: Array<{ label: string; value: string }>;
      } | null;
      if (route.request().method() === "PUT") {
        profileSaves += 1;
        profileVerificationStatus = "auto_extracted";
      }
      return route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: body?.details ?? [],
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      });
    },
  );
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() !== "POST") {
      return route.fulfill({ json: { jobs: [firstJob] } });
    }
    detectionPosts += 1;
    if (detectionPosts === 1) {
      return route.fulfill({ status: 202, json: { job: firstJob } });
    }
    return route.fulfill({
      status: 429,
      json: {
        detail: "Queue busy at /srv/private/patient-review/source.mp4",
      },
    });
  });
  await page.route(
    "**/api/video-detection/jobs/VID-RECHECK-SYNTHETIC-1",
    (route) => {
      firstJob.status = "expired";
      firstJob.current_stage = "expired";
      firstJob.error = null;
      return route.fulfill({ json: { job: firstJob } });
    },
  );

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-recheck-safety-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "recording-two.e"), "synthetic-eeg-two");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "clip-one.avi"), "synthetic-video-one");
    writeFileSync(join(folder, "clip-two.avi"), "synthetic-video-two");

    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    const detailRegion = page.getByRole("region", { name: "Patient details" });
    const startButton = page.getByRole("button", { name: "Start processing" });
    await expect(detailRegion.getByRole("checkbox")).toHaveCount(0);
    await expect(
      detailRegion.getByText("Synthetic finding.", { exact: true }),
    ).toBeHidden();
    await detailRegion.getByText("View extracted details").click();
    await expect(
      detailRegion.getByText("Synthetic finding.", { exact: true }),
    ).toBeVisible();
    expect(reportPosts).toBe(1);
    await expect(startButton).toBeEnabled();
    expect(draftPosts).toBe(0);
    expect(profileSaves).toBe(0);
    await startButton.focus();
    await page.keyboard.press("Enter");

    const processingRegion = page.getByRole("region", {
      name: "Patient processing progress",
    });
    const processingHeading = processingRegion.getByRole("heading").first();
    await expect(processingHeading).toBeVisible();
    const eegProgress = page.getByRole("region", {
      name: "Recording analysis",
    });
    await expect(eegProgress).toContainText("1 of 2 EEG recordings complete");
    await expect(eegProgress).toContainText("1 need attention");
    await expect(eegProgress).toContainText("100% resolved");
    await expect
      .poll(() =>
        processingHeading.evaluate(
          (heading) => heading === document.activeElement,
        ),
      )
      .toBe(true);
    await expect
      .poll(() =>
        processingHeading.evaluate((heading) => {
          const headingBounds = heading.getBoundingClientRect();
          const headerBounds = document
            .querySelector(".app-header")
            ?.getBoundingClientRect();
          return (
            headingBounds.top >= (headerBounds?.bottom ?? 0) &&
            headingBounds.bottom <= window.innerHeight
          );
        }),
      )
      .toBe(true);
    const viewport = await page.evaluate(() => ({
      width: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
    }));
    expect(viewport.documentWidth).toBeLessThanOrEqual(viewport.width);
    await page.screenshot({
      path: test.info().outputPath("patient-processing-progress.png"),
    });

    const videoProgress = page.getByRole("region", {
      name: "Video processing",
    });
    await expect(videoProgress.getByRole("alert")).toHaveCount(2);
    await expect(
      videoProgress.getByText("Expired", { exact: true }),
    ).toBeVisible();
    await expect(
      videoProgress.getByText("Not submitted", { exact: true }),
    ).toBeVisible();
    await expect(
      videoProgress.getByText("Video job expired. No result is available."),
    ).toBeVisible();
    await expect(
      page.getByRole("alert").filter({
        hasText: "1 video clip needs attention.",
      }),
    ).toHaveText("1 video clip needs attention.");
    await expect(
      page.getByText(
        /\/srv\/private\/patient-review|source\.mp4|recording\.e|clip-one\.avi|clip-two\.avi/,
      ),
    ).toHaveCount(0);
    expect(detectionPosts).toBe(2);

    await expect(
      page.getByRole("heading", { name: "Processing finished with issues" }),
    ).toBeVisible();
    await expect(processingRegion.getByRole("status")).toHaveText(
      "All submitted processing jobs reached a terminal status.",
    );
    await expect(
      page.getByRole("button", { name: "Retry eligible video uploads" }),
    ).toBeVisible();
    expect(detectionPosts).toBe(2);
    expect(profileSaves).toBe(1);
    expect(profileVerificationStatus).toBe("auto_extracted");
    await expect(videoProgress.getByRole("alert")).toHaveCount(2);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("continues EEG processing when local report extraction fails", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted upload workflow.",
  );

  const createdAt = "2026-09-27T00:00:00Z";
  let reportPosts = 0;
  let draftPosts = 0;
  let finalizePosts = 0;
  await page.route("**/api/patient-report", (route) => {
    reportPosts += 1;
    return route.fulfill({
      status: 422,
      json: { detail: "The report could not be read locally." },
    });
  });
  await page.route("**/api/uploads/drafts", (route) => {
    if (route.request().method() !== "POST") return route.continue();
    draftPosts += 1;
    return route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-REPORT-ERROR-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: "2026-09-28T00:00:00Z",
      },
    });
  });
  await page.route(
    "**/api/uploads/drafts/UPL-REPORT-ERROR-SYNTHETIC/finalize",
    (route) => {
      finalizePosts += 1;
      return route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-REPORT-ERROR-SYNTHETIC",
          case_id: "CASE-REPORT-ERROR-SYNTHETIC",
          status: "queued",
        },
      });
    },
  );
  await page.route("**/api/sessions/MDS-REPORT-ERROR-SYNTHETIC", (route) =>
    route.fulfill({
      json: syntheticSession({
        sessionId: "MDS-REPORT-ERROR-SYNTHETIC",
        caseId: "CASE-REPORT-ERROR-SYNTHETIC",
        createdAt,
        status: "completed",
        progress: {
          total_recordings: 1,
          finished_recordings: 1,
          completed_recordings: 1,
          failed_recordings: 0,
          percent: 100,
        },
      }),
    }),
  );

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-report-error-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-unreadable-report");

    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    const details = page.getByRole("region", { name: "Patient details" });
    await expect(details).toContainText(
      "The report could not be read locally.",
    );

    const startButton = page.getByRole("button", { name: "Start processing" });
    await expect(startButton).toBeEnabled();
    await startButton.click();
    await expect(
      page.getByRole("heading", { name: "Processing complete" }),
    ).toBeVisible();
    expect(reportPosts).toBe(1);
    expect(draftPosts).toBe(1);
    expect(finalizePosts).toBe(1);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("EEG progress separates completed recordings from failures", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted upload workflow.",
  );

  const createdAt = new Date().toISOString();
  let sessionFinished = false;
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-PARTIAL-PROGRESS-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-PARTIAL-PROGRESS-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-PARTIAL-PROGRESS-SYNTHETIC",
          case_id: "CASE-PARTIAL-PROGRESS-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-PARTIAL-PROGRESS-SYNTHETIC", (route) =>
    route.fulfill({
      json: syntheticSession({
        sessionId: "MDS-PARTIAL-PROGRESS-SYNTHETIC",
        caseId: "CASE-PARTIAL-PROGRESS-SYNTHETIC",
        createdAt,
        status: sessionFinished ? "completed_with_errors" : "processing",
        progress: sessionFinished
          ? {
              total_recordings: 3,
              finished_recordings: 3,
              completed_recordings: 2,
              failed_recordings: 1,
              percent: 100,
            }
          : {
              total_recordings: 3,
              finished_recordings: 2,
              completed_recordings: 1,
              failed_recordings: 1,
              percent: 67,
            },
      }),
    }),
  );
  await page.route(
    "**/api/cases/CASE-PARTIAL-PROGRESS-SYNTHETIC/patient-profile/extracted",
    (route) =>
      route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: [{ label: "Findings", value: "Synthetic finding." }],
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      }),
  );

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-partial-progress-test-"));
  try {
    writeFileSync(join(folder, "recording-one.e"), "synthetic-eeg-one");
    writeFileSync(join(folder, "recording-two.e"), "synthetic-eeg-two");
    writeFileSync(join(folder, "recording-three.e"), "synthetic-eeg-three");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");

    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();

    const progress = page.getByRole("region", {
      name: "Patient processing progress",
    });
    await expect(progress.getByRole("status")).toContainText(
      "EEG processing: 1 of 3 recordings complete; 1 failed",
    );
    sessionFinished = true;
    await expect(
      progress.getByRole("heading", {
        name: "Processing finished with issues",
      }),
    ).toBeVisible();
    const eegProgress = progress.getByRole("region", {
      name: "Recording analysis",
    });
    await expect(eegProgress).toContainText("2 of 3 EEG recordings complete");
    await expect(eegProgress).toContainText("1 need attention");
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("video intake waits for queue capacity and automatically submits later clips", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted upload workflow.",
  );

  const createdAt = new Date().toISOString();
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  let detectionPosts = 0;
  let acceptedJobs = 0;
  let firstJobTerminalObserved = false;
  let retriedAfterCapacityOpened = false;
  let capacityRejected = false;
  const jobs = new Map<string, Record<string, unknown>>();

  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-RETRY-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: expiresAt,
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-RETRY-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-RETRY-SYNTHETIC",
          case_id: "CASE-RETRY-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-RETRY-SYNTHETIC", (route) =>
    route.fulfill({
      json: syntheticSession({
        sessionId: "MDS-RETRY-SYNTHETIC",
        caseId: "CASE-RETRY-SYNTHETIC",
        createdAt,
        status: "completed",
        progress: {
          total_recordings: 1,
          finished_recordings: 1,
          completed_recordings: 1,
          failed_recordings: 0,
          percent: 100,
        },
        processingAttempts: [
          {
            recording_sequence_index: 1,
            stage: "inference",
            status: "running",
            started_at: new Date(Date.now() - 2_000).toISOString(),
            finished_at: null,
          },
        ],
      }),
    }),
  );
  await page.route(
    "**/api/cases/CASE-RETRY-SYNTHETIC/patient-profile/extracted",
    (route) =>
      route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: [{ label: "Findings", value: "Synthetic finding." }],
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      }),
  );
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() !== "POST")
      return route.fulfill({ json: { jobs: Array.from(jobs.values()) } });
    detectionPosts += 1;
    if (detectionPosts === 2 && !capacityRejected) {
      capacityRejected = true;
      return route.fulfill({
        status: 429,
        json: { detail: "Video processing is temporarily busy." },
      });
    }
    if (detectionPosts > 2 && firstJobTerminalObserved)
      retriedAfterCapacityOpened = true;
    acceptedJobs += 1;
    const jobId = `VID-RETRY-SYNTHETIC-${acceptedJobs}`;
    const job = {
      job_id: jobId,
      case_id: "CASE-RETRY-SYNTHETIC",
      label: `Video ${acceptedJobs}`,
      status: "ready",
      current_stage: "complete",
      duration_seconds: 10,
      fps: 30,
      created_at: createdAt,
      retention_expires_at: expiresAt,
      video_available: false,
      error: null,
    };
    jobs.set(jobId, job);
    return route.fulfill({ status: 202, json: { job } });
  });
  await page.route("**/api/video-detection/jobs/*", (route) => {
    const jobId = route.request().url().split("/").pop() ?? "";
    const job = jobs.get(jobId);
    if (jobId === "VID-RETRY-SYNTHETIC-1" && job?.status === "ready")
      firstJobTerminalObserved = true;
    return job
      ? route.fulfill({ json: { job } })
      : route.fulfill({ status: 404, json: { detail: "Job not found." } });
  });

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-video-retry-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "clip-one.avi"), "synthetic-video-one");
    writeFileSync(join(folder, "clip-two.avi"), "synthetic-video-two");
    writeFileSync(join(folder, "clip-three.avi"), "synthetic-video-three");

    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();

    await expect(
      page.getByRole("heading", { name: "Processing complete" }),
    ).toBeVisible();
    expect(detectionPosts).toBe(4);
    expect(acceptedJobs).toBe(3);
    expect(firstJobTerminalObserved).toBe(true);
    expect(retriedAfterCapacityOpened).toBe(true);
    expect([...jobs.values()].map((job) => job.label)).toEqual([
      "Video 1",
      "Video 2",
      "Video 3",
    ]);
    const videoProgress = page.getByRole("region", {
      name: "Video processing",
    });
    const eegProgress = page.getByRole("region", {
      name: "Recording analysis",
    });
    await eegProgress
      .getByText("Show EEG processing stages · 1 recorded")
      .click();
    await expect(eegProgress).toContainText("Recording 01 · Run H5 model");
    await expect(eegProgress).toContainText("running");
    await expect(
      videoProgress.getByText("Complete", { exact: true }),
    ).toHaveCount(3);
    await expect(
      videoProgress.getByText("Not submitted", { exact: true }),
    ).toHaveCount(0);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("shows issues when an EEG session fails before creating recordings", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted upload workflow.",
  );

  const createdAt = new Date().toISOString();
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({ json: { draft: { details: [], truncated: false } } }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-FAILED-EEG-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: expiresAt,
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-FAILED-EEG-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-FAILED-EEG-SYNTHETIC",
          case_id: "CASE-FAILED-EEG-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-FAILED-EEG-SYNTHETIC", (route) =>
    route.fulfill({
      json: syntheticSession({
        sessionId: "MDS-FAILED-EEG-SYNTHETIC",
        caseId: "CASE-FAILED-EEG-SYNTHETIC",
        createdAt,
        status: "failed",
        progress: {
          total_recordings: 1,
          finished_recordings: 0,
          completed_recordings: 0,
          failed_recordings: 0,
          percent: 0,
        },
      }),
    }),
  );

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-failed-eeg-status-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");

    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();

    await expect(
      page.getByRole("heading", { name: "Processing finished with issues" }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Recording analysis" }),
    ).toContainText("failed");
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("canceling an accepted video upload leaves it unconfirmed and links to the patient review", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted upload workflow.",
  );

  const createdAt = "2026-09-27T00:00:00Z";
  const expiresAt = "2026-09-28T00:00:00Z";
  const job = {
    job_id: "VID-CANCEL-SYNTHETIC-1",
    case_id: "CASE-CANCEL-SYNTHETIC",
    label: "Video 1",
    status: "queued",
    current_stage: "preflight",
    duration_seconds: 10,
    fps: 30,
    created_at: createdAt,
    retention_expires_at: expiresAt,
    video_available: false,
    error: null,
  };
  let detectionPosts = 0;
  let releaseAcceptedResponse = () => {};
  let markUploadAccepted = () => {};
  const heldResponse = new Promise<void>(
    (resolve) => (releaseAcceptedResponse = resolve),
  );
  const uploadAccepted = new Promise<void>(
    (resolve) => (markUploadAccepted = resolve),
  );

  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-CANCEL-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: expiresAt,
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-CANCEL-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-CANCEL-SYNTHETIC",
          case_id: "CASE-CANCEL-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-CANCEL-SYNTHETIC", (route) =>
    route.fulfill({
      json: syntheticSession({
        sessionId: "MDS-CANCEL-SYNTHETIC",
        caseId: "CASE-CANCEL-SYNTHETIC",
        createdAt,
        status: "completed",
        progress: {
          total_recordings: 1,
          finished_recordings: 1,
          completed_recordings: 1,
          failed_recordings: 0,
          percent: 100,
        },
      }),
    }),
  );
  await page.route(
    "**/api/cases/CASE-CANCEL-SYNTHETIC/patient-profile/extracted",
    (route) =>
      route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: [{ label: "Findings", value: "Synthetic finding." }],
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      }),
  );
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() !== "POST")
      return route.fulfill({ json: { jobs: [job] } });
    detectionPosts += 1;
    markUploadAccepted();
    try {
      await heldResponse;
      await route.fulfill({ status: 202, json: { job } });
    } catch {
      // The client cancels after the service has accepted this synthetic job.
    }
  });

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-cancel-safety-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "clip.avi"), "synthetic-video");

    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();
    await expect(
      page.getByRole("heading", { name: "Processing patient review" }),
    ).toBeVisible();
    await uploadAccepted;
    await page.getByRole("button", { name: "Cancel intake" }).click();
    releaseAcceptedResponse();

    const videoProgress = page.getByRole("region", {
      name: "Video processing",
    });
    await expect(videoProgress.getByText("Status unconfirmed")).toBeVisible();
    await expect(
      page.getByRole("link", {
        name: "Open patient review to check status",
      }),
    ).toHaveAttribute("href", "/cases/CASE-CANCEL-SYNTHETIC");
    await expect(
      page.getByRole("button", { name: "Recheck processing status" }),
    ).toHaveCount(0);
    expect(detectionPosts).toBe(1);
  } finally {
    releaseAcceptedResponse();
    rmSync(folder, { recursive: true, force: true });
  }
});
