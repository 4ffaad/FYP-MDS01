import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const reviewVideo = readFileSync(
  resolve(__dirname, "../fixtures/synthetic-review.mp4"),
);

const job = {
  job_id: "VID-synthetic",
  label: "Synthetic video detection",
  status: "ready",
  current_stage: "complete",
  duration_seconds: 10,
  fps: 30,
  blur_strength_percent: 100,
  review_privacy_method: "tracked-face-blur-with-full-frame-fallback" as const,
  created_at: new Date().toISOString(),
  retention_expires_at: new Date(Date.now() + 3600000).toISOString(),
  video_available: true,
  error: null,
};
const result = {
  model: {
    model_name: "VSViG-base",
    model_version: "synthetic-test-only",
    weights_hash: "synthetic",
    preprocessing_version: "test",
    threshold: 0.5,
    sample_fps: 15,
    window_frames: 30,
    stride_frames: 15,
    calibrated: false,
  },
  predictions: [
    {
      start_time: 0,
      end_time: 2,
      score: 0.2,
      raw_score: 0.2,
      score_type: "uncalibrated_model_score",
      seizure_detected: false,
    },
    {
      start_time: 1,
      end_time: 3,
      score: 0.8,
      raw_score: 0.8,
      score_type: "uncalibrated_model_score",
      seizure_detected: true,
      model_evidence: {
        method: "vsvig-graph-grad-cam",
        target_class: "flagged",
        note: "Synthetic Grad-CAM test evidence.",
        pose_samples: [
          {
            timestamp: 2,
            points: Array.from({ length: 15 }, (_, patch_index) => ({
              patch_index,
              x: 0.32 + (patch_index % 5) * 0.08,
              y: 0.2 + Math.floor(patch_index / 5) * 0.2,
              confidence: 0.9,
            })),
          },
        ],
        gradcam_samples: Array.from({ length: 30 }, (_, sample_index) => ({
          timestamp: 1 + sample_index / 15,
          patches: Array.from({ length: 15 }, (_, patch_index) => ({
            patch_index,
            relevance: patch_index === 5 ? 1 : 0.05,
          })),
        })),
      },
    },
  ],
  intervals: [{ start_time: 1, end_time: 3 }],
  timeline: [
    {
      timestamp: 1,
      start_time: 0,
      end_time: 2,
      score: 0.2,
      seizure_detected: false,
    },
    {
      timestamp: 2,
      start_time: 1,
      end_time: 3,
      score: 0.8,
      seizure_detected: true,
    },
  ],
  events: [{ start_time: 1, end_time: 3, peak_score: 0.8, peak_timestamp: 2 }],
  summary: {
    peak_score: 0.8,
    potential_event_detected: true,
    event_count: 1,
    threshold: 0.5,
  },
  privacy: {
    method: "tracked-face-blur-with-full-frame-fallback",
    model_input: "15 individually blurred RGB patches per sampled frame",
    blur_strength_percent: 50,
    model_input_adaptation: "none",
    source_resolution: [1920, 1080],
    model_resolution: [1920, 1080],
    source_timestamp_offset_seconds: 0.118,
    face_blur_coverage: 0.8,
    quality_flags: ["intermittent_detection"],
    review_required: true,
  },
  visualization: {
    available: true,
    media_type: "video/mp4",
    audio_included: false,
    privacy_method:
      "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
    face_blur_coverage: 0.8,
    full_frame_fallback_frames: 20,
    quality_flags: ["full_frame_fallback_used"],
  },
  recording_probability_available: false,
};

let mediaAssetRequests: string[] = [];
let uploadBlurStrength = 100;

test.beforeEach(async ({ page }) => {
  mediaAssetRequests = [];
  uploadBlurStrength = 100;
  await page.route("**/api/video-detection/**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "OPTIONS")
      return route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Headers":
            "content-type,accept,x-case-id,x-video-format,x-model-blur-percent,idempotency-key",
          "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
      });
    if (url.endsWith("/visualization")) {
      mediaAssetRequests.push(new URL(url).pathname);
      return route.fulfill({
        status: 200,
        body: reviewVideo,
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
          "Access-Control-Allow-Credentials": "true",
          "Accept-Ranges": "bytes",
          "Cache-Control": "private, no-store",
          "Content-Type": "video/mp4",
        },
      });
    }
    if (url.endsWith("/jobs") && route.request().method() === "POST") {
      uploadBlurStrength = Number(
        route.request().headers()["x-model-blur-percent"] ?? "100",
      );
    }
    return route.fulfill({
      json: url.endsWith("/predictions")
        ? uploadBlurStrength === 0
          ? {
              ...result,
              privacy: {
                ...result.privacy,
                method: "unblurred-owner-source",
                model_input: "15 unblurred RGB patches per sampled frame",
                blur_strength_percent: 0,
                face_blur_coverage: null,
                quality_flags: [],
              },
              visualization: {
                ...result.visualization,
                privacy_method: "unblurred-owner-source-and-skeleton-overlay",
                face_blur_coverage: null,
                full_frame_fallback_frames: 0,
                quality_flags: [],
              },
            }
          : result
        : url.endsWith("/jobs") && route.request().method() === "GET"
          ? { jobs: [job] }
          : {
              job: {
                ...job,
                blur_strength_percent: uploadBlurStrength,
                review_privacy_method:
                  uploadBlurStrength === 0
                    ? "unblurred-owner-source"
                    : job.review_privacy_method,
                retention_policy: "until-deletion",
                retention_expires_at: null,
              },
            },
      headers: {
        "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
        "Access-Control-Allow-Credentials": "true",
      },
    });
  });
});

test("uploads and reviews window supports without confidence percentages", async ({
  page,
}) => {
  await page.goto("/video-detection");
  await expect(
    page.getByText(
      "Upload a clip once. MDS01 scores movement and creates an owner-only review copy automatically.",
    ),
  ).toBeVisible();
  await expect(page.getByRole("slider", { name: /blur/i })).toHaveCount(0);
  await page.getByLabel("Video", { exact: true }).setInputFiles({
    name: "synthetic.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("synthetic fixture"),
  });
  const uploadRequest = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/video-detection/jobs") &&
      request.method() === "POST",
  );
  await page.getByRole("button", { name: "Upload video", exact: true }).click();
  expect((await uploadRequest).headers()["x-model-blur-percent"]).toBe("0");
  await expect(page).toHaveURL(/\/video-detection$/);
  await page
    .getByRole("link", { name: "open its review when you’re ready" })
    .click();
  await expect(page).toHaveURL(/video-detection\/VID-synthetic/);
  await expect(
    page
      .getByTestId("video-review-frame")
      .getByText("Owner reference · unblurred"),
  ).toBeVisible();
  await expect(page.locator("video")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "VSViG score over time" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Threshold crossed" }),
  ).toBeVisible();
  await expect(
    page.getByRole("group", { name: "Video display blur" }),
  ).toHaveCount(0);
  const videoFrame = page.getByTestId("video-review-frame");
  const supportsFullscreen = await videoFrame.evaluate(
    (frame) => typeof frame.requestFullscreen === "function",
  );
  await videoFrame.getByRole("button", { name: "Full screen" }).click();
  if (supportsFullscreen) {
    await expect
      .poll(() =>
        videoFrame.evaluate((frame) => document.fullscreenElement === frame),
      )
      .toBe(true);
  } else {
    await expect(videoFrame).toHaveClass(/fixed/);
  }
  await expect(
    page
      .getByTestId("video-review-frame")
      .getByText("Owner reference · unblurred"),
  ).toBeVisible();
  await videoFrame.getByRole("button", { name: "Exit full screen" }).click();
  if (supportsFullscreen) {
    await expect
      .poll(() => page.evaluate(() => document.fullscreenElement))
      .toBeNull();
  } else {
    await expect(videoFrame).not.toHaveClass(/fixed/);
  }
  const timeline = page.getByRole("region", {
    name: "VSViG score over time",
  });
  await expect(timeline).toBeVisible();
  await expect(timeline.getByRole("button")).toHaveCount(2);
  await expect(
    page.getByText(/configured research threshold 0.50/),
  ).toBeVisible();
  await expect(
    page.getByText("VSViG score and protected video", { exact: true }),
  ).toBeVisible();
  const peakScoreScale = page.getByRole("img", {
    name: "Peak score 0.800 on a fixed 0 to 1 display scale; threshold 0.500",
  });
  await expect(peakScoreScale).toBeVisible();
  await expect(peakScoreScale.locator("span").nth(0)).toHaveAttribute(
    "style",
    "left: 50%;",
  );
  await expect(peakScoreScale.locator("span").nth(1)).toHaveAttribute(
    "style",
    "left: 80%;",
  );
  await expect(
    page.getByText(
      "Encrypted originals and results are retained until case deletion.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText("Selected video time", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Video review completion" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(page.locator("main")).not.toContainText(/confidence/i);
  // Only the authenticated owner reference is fetched for playback.
  expect(mediaAssetRequests).toEqual([
    "/api/video-detection/jobs/VID-synthetic/visualization",
  ]);
  await expect(page.getByRole("button", { name: "Event 1" })).toBeVisible();
  await page.getByRole("button", { name: "Event 1" }).click();
  await expect(page.getByTestId("video-vsvig-gradcam")).toBeVisible();
  await expect
    .poll(() =>
      page
        .locator("video")
        .evaluate((element) => (element as HTMLVideoElement).currentTime),
    )
    .toBe(2);
  await page.getByText("All window scores", { exact: true }).click();
  await expect(
    page.getByRole("table").getByText("0:01.0–0:03.0", { exact: true }),
  ).toBeVisible();
  await page.getByText("Model and processing details", { exact: true }).click();
  await expect(
    page.getByText("0% of default strength", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Source timestamp offset", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText("+0.118 s", { exact: true })).toHaveCount(0);
});

test("separates scores for multiple people and lets the reviewer choose a track", async ({
  page,
}) => {
  const firstTrack = {
    subject_id: "track-1",
    label: "Track 1",
    status: "unscored",
    unavailable_reason: "incomplete_pose",
    unscored_windows: [
      {
        start_time: 0,
        end_time: 5,
        reason: "incomplete_pose",
      },
    ],
    predictions: [],
    timeline: [],
    intervals: [],
    events: [],
  };
  const secondTrack = {
    subject_id: "track-2",
    label: "Track 2",
    status: "scored",
    unavailable_reason: null,
    unscored_windows: [],
    predictions: result.predictions,
    timeline: result.timeline,
    intervals: result.intervals,
    events: result.events,
    summary: result.summary,
  };
  await page.route(
    "**/api/video-detection/jobs/VID-synthetic/predictions",
    (route) =>
      route.fulfill({
        json: {
          ...result,
          predictions: [],
          timeline: [],
          intervals: [],
          events: [],
          summary: undefined,
          subjects: [firstTrack, secondTrack],
        },
      }),
  );

  await page.goto("/video-detection/VID-synthetic");
  await expect(
    page.getByText(
      "Track labels follow detection order and do not identify the patient.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "No scored window selected" }),
  ).toBeVisible();
  await page.getByRole("radio", { name: /Track 2/ }).check();
  await expect(
    page.getByRole("heading", { name: "Threshold crossed" }),
  ).toBeVisible();
  await page.getByText("All window scores", { exact: true }).click();
  await expect(
    page.getByRole("table").getByText("0:01.0–0:03.0", { exact: true }),
  ).toBeVisible();
});

test("zero face-blur coverage reports full-frame fallback in the retained review", async ({
  page,
}) => {
  await page.route(
    "**/api/video-detection/jobs/VID-synthetic/predictions",
    (route) =>
      route.fulfill({
        json: {
          ...result,
          privacy: {
            ...result.privacy,
            face_blur_coverage: 0,
            quality_flags: ["no_detection"],
            review_required: true,
          },
          visualization: {
            ...result.visualization,
            face_blur_coverage: 0,
            full_frame_fallback_frames: 20,
            quality_flags: ["full_frame_fallback_used"],
          },
        },
      }),
  );

  await page.goto("/video-detection/VID-synthetic");

  await expect(
    page.getByText("Face blur · 0% of frames · full-frame fallback 20 frames", {
      exact: true,
    }),
  ).toBeVisible();
});

test("video review history keeps rejected clips and shows the failure reason", async ({
  page,
}) => {
  const failedJob = {
    ...job,
    job_id: "VID-failed",
    label: "Synthetic rejected video",
    status: "failed" as const,
    current_stage: "pose_readiness",
    duration_seconds: 5.08,
    video_available: false,
    error:
      "The opening five-second pose check found no track with all 15 required landmarks selected by VSViG.",
  };
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({ json: { jobs: [failedJob] } }),
  );
  await page.route("**/api/video-detection/jobs/VID-failed", (route) =>
    route.fulfill({ json: { job: failedJob } }),
  );

  await page.goto("/video-reviews");

  const failedReview = page.getByRole("link", {
    name: /Synthetic rejected video/,
  });
  await expect(failedReview).toContainText("No person track had all 15");
  await failedReview.click();
  await expect(page).toHaveURL(/\/video-detection\/VID-failed$/);
  await expect(page.locator('p[role="alert"]')).toContainText(
    "other OpenPose joints are not required",
  );
  await expect(
    page.getByRole("heading", { name: "VSViG score over time" }),
  ).toHaveCount(0);
});

test("video reviews lists past uploads and opens the protected result", async ({
  page,
}) => {
  await page.goto("/video-reviews");
  await expect(page).toHaveURL(/\/video-detection\?view=reviews$/);
  await expect(
    page.getByRole("heading", { name: "Video reviews" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Synthetic video detection/ }),
  ).toHaveAttribute("href", "/video-detection/VID-synthetic");
  await expect(
    page
      .getByRole("navigation", { name: "Video workspace" })
      .getByRole("link", { name: "Video reviews" }),
  ).toHaveAttribute("aria-current", "page");
  await page
    .getByRole("navigation", { name: "Video workspace" })
    .getByRole("link", { name: "New video analysis" })
    .click();
  await expect(page).toHaveURL(/\/video-detection$/);
  await expect(page.getByRole("heading", { name: "Video" })).toBeVisible();
  await page
    .getByRole("navigation", { name: "Video workspace" })
    .getByRole("link", { name: "Video reviews" })
    .click();
  await expect(page).toHaveURL(/\/video-detection\?view=reviews$/);
  await expect(
    page.getByRole("heading", { name: "Video reviews" }),
  ).toBeVisible();
});

test("retries a transient ready-result failure without a reload", async ({
  page,
}) => {
  let attempts = 0;
  await page.route(
    "**/api/video-detection/jobs/VID-synthetic/predictions",
    async (route) => {
      attempts += 1;
      if (attempts === 1) {
        return route.fulfill({ status: 503, body: "temporary failure" });
      }
      return route.fulfill({
        json: result,
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
          "Access-Control-Allow-Credentials": "true",
        },
      });
    },
  );

  await page.goto("/video-detection/VID-synthetic");
  await expect
    .poll(() => attempts, { timeout: 10_000 })
    .toBeGreaterThanOrEqual(2);
  await expect(
    page.getByRole("heading", { name: "VSViG score over time" }),
  ).toBeVisible();
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
});

test("backs off after consecutive retryable ready-result failures", async ({
  page,
}) => {
  const requestTimes: number[] = [];
  await page.route(
    "**/api/video-detection/jobs/VID-synthetic/predictions",
    async (route) => {
      requestTimes.push(Date.now());
      if (requestTimes.length <= 2) {
        return route.fulfill({ status: 503, body: "temporary failure" });
      }
      return route.fulfill({
        json: result,
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
          "Access-Control-Allow-Credentials": "true",
        },
      });
    },
  );

  await page.goto("/video-detection/VID-synthetic");
  await expect
    .poll(() => requestTimes.length, { timeout: 10_000 })
    .toBeGreaterThanOrEqual(3);
  await expect(
    page.getByRole("heading", { name: "VSViG score over time" }),
  ).toBeVisible();

  const firstDelay = requestTimes[1] - requestTimes[0];
  const secondDelay = requestTimes[2] - requestTimes[1];
  expect(secondDelay).toBeGreaterThan(firstDelay + 600);
});

test("lets the user retry a non-retryable initial job-load failure", async ({
  page,
}) => {
  let attempts = 0;
  let retryAllowed = false;
  await page.route(
    "**/api/video-detection/jobs/VID-synthetic",
    async (route) => {
      attempts += 1;
      if (!retryAllowed) {
        return route.fulfill({
          status: 404,
          json: { detail: "This video job could not be found." },
        });
      }
      return route.fulfill({ json: { job } });
    },
  );

  await page.goto("/video-detection/VID-synthetic");
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "This video job could not be found.",
  );
  const failedAttempts = attempts;
  retryAllowed = true;
  await page.getByRole("button", { name: "Retry job" }).click();
  await expect(
    page.getByRole("heading", { name: "VSViG score over time" }),
  ).toBeVisible();
  expect(attempts).toBeGreaterThan(failedAttempts);
});

test("shows the reported processing stage and checkpoint percentage", async ({
  page,
}) => {
  await page.route("**/api/video-detection/jobs/VID-processing", (route) => {
    const processingJob = {
      ...job,
      status: "processing",
      current_stage: "normalization",
      video_available: false,
    };
    return route.fulfill({ json: { job: processingJob } });
  });

  await page.goto("/video-detection/VID-processing");
  await expect(
    page.getByRole("heading", { name: "Building your video review" }),
  ).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Video review completion" }),
  ).toHaveAttribute("aria-valuenow", "24");
  await expect(
    page
      .getByRole("list", { name: "Video review processing steps" })
      .getByText("Prepare input", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("24%", { exact: true })).toBeVisible();
});

test("shows where a failed pose run stopped", async ({ page }) => {
  await page.route("**/api/video-detection/jobs/VID-pose-failed", (route) => {
    const failedJob = {
      ...job,
      job_id: "VID-pose-failed",
      status: "failed",
      current_stage: "failed",
      video_available: false,
      error:
        "At least one sampled frame lacked a confident body landmark required by VSViG.",
    };
    return route.fulfill({ json: { job: failedJob } });
  });

  await page.goto("/video-detection/VID-pose-failed");
  await expect(
    page.getByRole("heading", { name: "Video processing stopped" }),
  ).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Video review completion" }),
  ).toHaveAttribute("aria-valuenow", "72");
  const steps = page.getByRole("list", {
    name: "Video review processing steps",
  });
  await expect(steps.getByText("Pose + VSViG", { exact: true })).toBeVisible();
  await expect(steps.getByText("Stopped here", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("alert").filter({ hasText: "Some sampled windows lacked" }),
  ).toContainText("remain unscored");
});

test("shows the upload handoff while the backend acknowledges the video", async ({
  page,
}) => {
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, 1200));
    return route.fulfill({ json: { job } });
  });

  await page.goto("/video-detection");
  await page.getByLabel("Video", { exact: true }).setInputFiles({
    name: "pending.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("pending upload fixture"),
  });
  await page.getByRole("button", { name: "Upload video", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: /Sending video securely|Checking pose readiness|Waiting for the private API/,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Video upload progress" }),
  ).toHaveAttribute("aria-valuenow", "0");
  await expect(
    page.getByRole("list", { name: "Video upload steps" }),
  ).toBeVisible();
  await expect(page.getByText("Review queue", { exact: true })).toBeVisible();
});

test("shows the safe landmark reason when pose readiness rejects an upload", async ({
  page,
}) => {
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 422,
      json: {
        detail:
          "Pose readiness failed. Missing landmark samples: right ankle: 1.",
      },
      headers: {
        "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
        "Access-Control-Allow-Credentials": "true",
      },
    });
  });

  await page.goto("/video-detection");
  await page.getByLabel("Video", { exact: true }).setInputFiles({
    name: "incomplete-pose.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("synthetic video fixture"),
  });
  await page.getByRole("button", { name: "Upload video", exact: true }).click();

  await expect(
    page.getByRole("alert").filter({ hasText: "Pose readiness failed." }),
  ).toContainText("right ankle: 1");
});

test("shows actionable asset error without navigating to fabricated results", async ({
  page,
}) => {
  await page.route("**/api/video-detection/jobs", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 503,
          json: {
            detail:
              "Mount the official model assets by running the pinned VSViG installer; see docs/video-detection.md.",
          },
          headers: {
            "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
            "Access-Control-Allow-Credentials": "true",
          },
        })
      : route.fallback(),
  );
  await page.goto("/video-detection");
  await page.getByLabel("Video", { exact: true }).setInputFiles({
    name: "synthetic.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("test"),
  });
  await page.getByRole("button", { name: "Upload video", exact: true }).click();
  await expect(
    page.getByText(
      "Video analysis is unavailable. Install and verify the pinned VSViG model assets, then retry.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/video-detection$/);
});

test("expired job removes playback and scores", async ({ page }) => {
  await page.route("**/api/video-detection/jobs/VID-synthetic", (route) =>
    route.fulfill({
      json: {
        job: {
          ...job,
          status: "expired",
          current_stage: "expired",
          video_available: false,
        },
      },
    }),
  );
  await page.goto("/video-detection/VID-synthetic");
  await expect(
    page.getByText(
      "The retention period ended. Encrypted predictions and review video have been removed.",
    ),
  ).toBeVisible();
  await expect(page.locator("video")).toHaveCount(0);
});
