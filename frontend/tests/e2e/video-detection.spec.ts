import { test, expect } from "@playwright/test";

const job = {
  job_id: "VID-synthetic",
  label: "Synthetic video detection",
  status: "ready",
  current_stage: "complete",
  duration_seconds: 10,
  fps: 30,
  created_at: new Date().toISOString(),
  retention_expires_at: new Date(Date.now() + 3600000).toISOString(),
  video_available: false,
  visualization_available: false,
  visualization_url: null,
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
    method: "face-detection-and-full-frame-blur",
    model_input: "full-frame-blurred video",
    model_input_adaptation: "none",
    source_resolution: [1920, 1080],
    model_resolution: [1920, 1080],
    source_timestamp_offset_seconds: 0.118,
    face_detection_coverage: 0.8,
    quality_flags: ["intermittent_detection"],
    review_required: true,
  },
  recording_probability_available: false,
};

let mediaAssetRequests: string[] = [];

test.beforeEach(async ({ page }) => {
  mediaAssetRequests = [];
  await page.route("**/api/video-detection/**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "OPTIONS")
      return route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Headers":
            "content-type,accept,x-case-id,x-video-format,idempotency-key",
          "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
      });
    if (url.endsWith("/video") || url.endsWith("/visualization")) {
      mediaAssetRequests.push(new URL(url).pathname);
      return route.fulfill({ status: 404, body: "No retained video artifact" });
    }
    return route.fulfill({
      json: url.endsWith("/predictions")
        ? result
        : url.endsWith("/jobs") && route.request().method() === "GET"
          ? { jobs: [job] }
          : { job },
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
      "Detection exposes no preview or playback; its privacy-safe validation visualization is transient and deleted. A separate video-privacy workflow may retain its own protected preview.",
      { exact: false },
    ),
  ).toBeVisible();
  await page.getByLabel("Video", { exact: true }).setInputFiles({
    name: "synthetic.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("synthetic fixture"),
  });
  await page
    .getByRole("button", { name: "Start detection", exact: true })
    .click();
  await expect(page).toHaveURL(/video-detection\/VID-synthetic/);
  await expect(
    page.getByText(
      "Detection retains encrypted predictions and safe provenance only; no video preview or playback is available.",
      { exact: false },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "VSViG score over time" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Potential seizure activity detected" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Privacy quality needs review" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "The detector reported exactly one face in only some frames.",
      {
        exact: true,
      },
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "OpenCV Haar reported exactly one face in 80% of frames. Full-frame blur was applied to every frame, independent of detection. This coverage signal does not guarantee anonymity.",
      { exact: true },
    ),
  ).toBeVisible();
  const timeline = page.getByRole("region", {
    name: "VSViG score over time",
  });
  await expect(timeline).toBeVisible();
  await expect(timeline.getByRole("button")).toHaveCount(2);
  await expect(
    page.getByText(/configured research threshold 0.50/),
  ).toBeVisible();
  await expect(
    page.getByText("Model evidence and event timeline", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Encrypted prediction retention ends", { exact: false }),
  ).toBeVisible();
  await expect(page.locator("video")).toHaveCount(0);
  await expect(
    page.getByRole("progressbar", { name: "Video review completion" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(page.locator("main")).not.toContainText(/confidence/i);
  // Video and derived video artifacts are never served to the browser.
  await expect(
    page.getByText(/No video artifact is retained or served\./),
  ).toBeVisible();
  expect(mediaAssetRequests).toEqual([]);
  await expect(page.getByRole("button", { name: "Event 1" })).toBeVisible();
  await page.getByText("All window scores", { exact: true }).click();
  await expect(
    page.getByRole("table").getByText("0:01.0–0:03.0", { exact: true }),
  ).toBeVisible();
  await page.getByText("Model and processing details", { exact: true }).click();
  await expect(
    page.getByText("Source timestamp offset", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText("+0.118 s", { exact: true })).toHaveCount(0);
});

test("zero face coverage is described as no frame with exactly one detection", async ({
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
            face_detection_coverage: 0,
            quality_flags: ["no_detection"],
            review_required: true,
          },
        },
      }),
  );

  await page.goto("/video-detection/VID-synthetic");

  await expect(
    page.getByText(
      "The detector did not report exactly one face in any frame.",
      {
        exact: true,
      },
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "OpenCV Haar reported exactly one face in 0% of frames. Full-frame blur was applied to every frame, independent of detection. This coverage signal does not guarantee anonymity.",
      { exact: true },
    ),
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
      current_stage: "privacy-transform",
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
  ).toHaveAttribute("aria-valuenow", "44");
  await expect(
    page
      .getByRole("list", { name: "Video review processing steps" })
      .getByText("Face redaction", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("44%", { exact: true })).toBeVisible();
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
  await page
    .getByRole("button", { name: "Start detection", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: /Sending video securely|Waiting for the private API/,
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
  await page
    .getByRole("button", { name: "Start detection", exact: true })
    .click();
  await expect(
    page.getByText(
      "Mount the official model assets by running the pinned VSViG installer; see docs/video-detection.md.",
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
          visualization_available: false,
          visualization_url: null,
        },
      },
    }),
  );
  await page.goto("/video-detection/VID-synthetic");
  await expect(
    page.getByText(
      "The retention period ended. Encrypted prediction data, source video, and the temporary model input have been removed.",
    ),
  ).toBeVisible();
  await expect(page.locator("video")).toHaveCount(0);
});
