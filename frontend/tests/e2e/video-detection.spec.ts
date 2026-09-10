import { test, expect } from "@playwright/test";

const job = { job_id: "VID-synthetic", label: "Synthetic video detection", status: "ready", current_stage: "complete", duration_seconds: 10, fps: 30, created_at: new Date().toISOString(), retention_expires_at: new Date(Date.now() + 3600000).toISOString(), video_available: true, error: null };
const result = {
  model: { model_name: "VSViG-base", model_version: "synthetic-test-only", weights_hash: "synthetic", preprocessing_version: "test", threshold: 0.5, sample_fps: 15, window_frames: 30, stride_frames: 15, calibrated: false },
  predictions: [{ start_time: 0, end_time: 2, score: 0.2, raw_score: 0.2, score_type: "uncalibrated_model_score", seizure_detected: false }, { start_time: 1, end_time: 3, score: 0.8, raw_score: 0.8, score_type: "uncalibrated_model_score", seizure_detected: true }],
  intervals: [{ start_time: 1, end_time: 3 }], recording_probability_available: false,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/video-detection/**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:3001", "Access-Control-Allow-Credentials": "true", "Access-Control-Allow-Headers": "content-type,accept", "Access-Control-Allow-Methods": "GET,POST,OPTIONS" } });
    if (url.endsWith("/video")) return route.abort();
    return route.fulfill({ json: url.endsWith("/predictions") ? result : url.endsWith("/jobs") && route.request().method() === "GET" ? { jobs: [job] } : { job }, headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:3001", "Access-Control-Allow-Credentials": "true" } });
  });
});

test("uploads and reviews window supports without confidence percentages", async ({ page }) => {
  await page.goto("/video-detection");
  await page.getByLabel("Patient video", { exact: true }).setInputFiles({ name: "synthetic.mp4", mimeType: "video/mp4", buffer: Buffer.from("synthetic fixture") });
  await page.getByRole("button", { name: "Start detection", exact: true }).click();
  await expect(page).toHaveURL(/video-detection\/VID-synthetic/);
  await expect(page.getByRole("heading", { name: "Uncalibrated model score" })).toBeVisible();
  await expect(page.getByText(/Each point covers 2.00 seconds, stepping 1.00 seconds/)).toBeVisible();
  await expect(page.getByRole("img", { name: /Threshold 0.5/ })).toBeVisible();
  await expect(page.locator("main")).not.toContainText(/\d+%|confidence/i);
  // Exercise the seek handler without pretending a mocked response is media.
  await page.locator("video").evaluate((element) => {
    Object.defineProperty(element, "currentTime", { configurable: true, writable: true, value: 0 });
  });
  await page.getByRole("button", { name: /Event 1/ }).click();
  await expect.poll(() => page.locator("video").evaluate((element: HTMLVideoElement) => element.currentTime)).toBe(1);
  await page.getByText("All window scores", { exact: true }).click();
  await expect(page.getByRole("button", { name: "0:01.0–0:03.0", exact: true })).toBeVisible();
});

test("shows actionable asset error without navigating to fabricated results", async ({ page }) => {
  await page.route("**/api/video-detection/jobs", (route) => route.request().method() === "POST" ? route.fulfill({ status: 503, json: { detail: "Mount the official model assets before starting detection." }, headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:3001", "Access-Control-Allow-Credentials": "true" } }) : route.fallback());
  await page.goto("/video-detection");
  await page.getByLabel("Patient video", { exact: true }).setInputFiles({ name: "synthetic.mp4", mimeType: "video/mp4", buffer: Buffer.from("test") });
  await page.getByRole("button", { name: "Start detection", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Mount the official model assets");
  await expect(page).toHaveURL(/\/video-detection$/);
});

test("expired job removes playback and scores", async ({ page }) => {
  await page.route("**/api/video-detection/jobs/VID-synthetic", (route) => route.fulfill({ json: { job: { ...job, status: "expired", current_stage: "expired", video_available: false } } }));
  await page.goto("/video-detection/VID-synthetic");
  await expect(page.getByText("The retention period ended. Video and results have been removed.")).toBeVisible();
  await expect(page.locator("video")).toHaveCount(0);
});
