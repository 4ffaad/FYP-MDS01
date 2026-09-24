import { test, expect } from "@playwright/test";

const sessionId = "SESSION-report-readiness";
const recordId = "REC-report-readiness";
const videoJobId = "JOB-report-readiness";

const recording = {
  record_id: recordId,
  sequence_index: 1,
  status: "inferred",
  source_filename: "Recording 01",
  source_format: "edf",
  duration_seconds: 120,
  sampling_rate: 256,
  channel_count: 18,
  session_id: sessionId,
  session_created_at: "2026-09-24T00:00:00Z",
  privacy_method: "metadata-scrub",
  privacy_methods: ["metadata-scrub"],
};

const emptyPrediction = {
  model: null,
  summary: {
    window_count: 0,
    flagged_window_count: 0,
    flagged_window_fraction: 0,
    peak_window_score: 0,
    highest_window: null,
    alert_intervals: [],
    aggregation_unit: "window",
    recording_probability_available: false,
  },
  predictions: [],
};

const inferredPrediction = {
  model: {
    name: "development-stub",
    version: "stub-0.1.0",
    threshold: 0.5,
    score_type: "development_score",
    calibrated: false,
    calibration_method: null,
  },
  summary: {
    window_count: 1,
    flagged_window_count: 1,
    flagged_window_fraction: 1,
    peak_window_score: 0.7,
    highest_window: { start_seconds: 0, end_seconds: 4, score: 0.7 },
    alert_intervals: [{ start_seconds: 0, end_seconds: 4 }],
    aggregation_unit: "window",
    recording_probability_available: false,
  },
  predictions: [
    {
      start_seconds: 0,
      end_seconds: 4,
      score: 0.7,
      probability: 0.7,
      raw_score: 0.7,
      score_type: "development_score",
      seizure_detected: true,
    },
  ],
};

test("combined report waits for inferred status before requesting prediction data @report-api", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with npm run test:e2e:report to exercise the API-mode readiness boundary.",
  );

  let sessionReads = 0;
  let currentStatus = "processed";
  let allowInference = false;
  let predictionRequests = 0;
  let requestedPredictionBeforeInference = false;

  await page.route(`**/api/sessions/${sessionId}`, async (route) => {
    sessionReads += 1;
    const inferred = allowInference;
    currentStatus = inferred ? "inferred" : "processed";
    return route.fulfill({
      json: {
        session_id: sessionId,
        case_id: null,
        privacy_method: "metadata-scrub",
        privacy_methods: ["metadata-scrub"],
        status: inferred ? "completed" : "inference",
        current_stage: inferred ? null : "inference",
        created_at: "2026-09-24T00:00:00Z",
        completed_at: inferred ? "2026-09-24T00:00:04Z" : null,
        progress: {
          total_recordings: 1,
          finished_recordings: inferred ? 1 : 0,
          completed_recordings: inferred ? 1 : 0,
          failed_recordings: 0,
          percent: inferred ? 100 : 50,
        },
        summary: { model_alert_recordings: 0 },
        recordings: [
          {
            ...recording,
            status: currentStatus,
          },
        ],
      },
    });
  });
  await page.route(`**/api/recordings/${recordId}`, (route) =>
    route.fulfill({ json: recording }),
  );
  await page.route(`**/api/recordings/${recordId}/prediction`, (route) => {
    predictionRequests += 1;
    if (currentStatus !== "inferred") requestedPredictionBeforeInference = true;
    return route.fulfill({
      json: currentStatus === "inferred" ? inferredPrediction : emptyPrediction,
    });
  });
  await page.route(`**/api/recordings/${recordId}/explanation`, (route) =>
    route.fulfill({ json: { explanations: [] } }),
  );
  await page.route(`**/api/recordings/${recordId}/annotations`, (route) =>
    route.fulfill({ status: 404, json: { detail: "Not found" } }),
  );

  await page.goto(`/analysis?sessionId=${sessionId}`);
  await expect(
    page.getByRole("heading", { name: "EEG and video review" }),
  ).toBeVisible();
  await expect(
    page.getByText("Waiting for a completed EEG recording.", { exact: true }),
  ).toBeVisible();
  expect(predictionRequests).toBe(0);

  allowInference = true;
  await expect(page.getByText("1 / 1", { exact: true })).toBeVisible({
    timeout: 8000,
  });
  expect(sessionReads).toBeGreaterThanOrEqual(2);
  expect(requestedPredictionBeforeInference).toBe(false);
  expect(predictionRequests).toBe(1);
});

test("combined report explains terminal EEG failure and links to the session @report-api", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with npm run test:e2e:report to exercise the API-mode readiness boundary.",
  );

  let sessionReads = 0;
  await page.route(`**/api/sessions/${sessionId}`, async (route) => {
    sessionReads += 1;
    return route.fulfill({
      json: {
        session_id: sessionId,
        case_id: null,
        privacy_method: "metadata-scrub",
        privacy_methods: ["metadata-scrub"],
        status: "completed_with_errors",
        current_stage: null,
        created_at: "2026-09-24T00:00:00Z",
        completed_at: "2026-09-24T00:00:04Z",
        progress: {
          total_recordings: 1,
          finished_recordings: 1,
          completed_recordings: 0,
          failed_recordings: 1,
          percent: 100,
        },
        summary: { model_alert_recordings: 0 },
        recordings: [{ ...recording, status: "failed" }],
      },
    });
  });

  await page.goto(`/analysis?sessionId=${sessionId}`);

  await expect(
    page.getByRole("status").filter({
      hasText: "EEG processing ended without an inferred recording.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open session details" }),
  ).toHaveAttribute("href", `/sessions/${sessionId}`);
  expect(sessionReads).toBeGreaterThanOrEqual(1);
});

test("combined report reports when privacy quality flags are empty @report-api", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with npm run test:e2e:report to exercise the API-mode readiness boundary.",
  );

  const job = {
    job_id: videoJobId,
    case_id: null,
    label: "Research sample",
    status: "ready",
    current_stage: "complete",
    duration_seconds: 4,
    fps: 6,
    created_at: "2026-09-24T00:00:00Z",
    retention_expires_at: "2026-09-25T00:00:00Z",
    video_available: false,
    visualization_available: false,
    visualization_url: null,
    error: null,
  };
  await page.route("**/api/video-detection/jobs/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith(`/jobs/${videoJobId}/predictions`))
      return route.fulfill({
        json: {
          model: {
            model_name: "fixture-model",
            model_version: "fixture-1",
            weights_hash: "fixture-hash",
            preprocessing_version: "fixture-preprocessing",
            threshold: 0.5,
            sample_fps: 6,
            window_frames: 48,
            stride_frames: 12,
            calibrated: false,
          },
          predictions: [],
          intervals: [],
          recording_probability_available: false,
          privacy: {
            method: "face-detection-and-full-frame-blur",
            model_input: "full-frame-blurred video",
            face_detection_coverage: 1,
            quality_flags: [],
            review_required: false,
          },
        },
      });
    if (url.pathname.endsWith(`/jobs/${videoJobId}`))
      return route.fulfill({ json: { job } });
    return route.continue();
  });

  await page.goto(`/analysis?videoJobId=${videoJobId}`);

  await expect(
    page.getByText("No privacy quality flags reported", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Review quality flags", { exact: true }),
  ).toHaveCount(0);
});
