import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { highestScoringAttribution } from "../../src/lib/research-attribution";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const key = "mds01.e2e-cleaned";
    if (window.sessionStorage.getItem(key)) return;
    window.localStorage.clear();
    window.sessionStorage.setItem(key, "true");
  });
});

test("research evidence selects the highest-scoring window independent of order", () => {
  const lower = { windowIndex: 8, score: 0.62 };
  const higher = { windowIndex: 3, score: 0.91 };

  expect(highestScoringAttribution([lower, higher])).toBe(higher);
  expect(highestScoringAttribution([higher, lower])).toBe(higher);
  expect(highestScoringAttribution([])).toBeNull();
});

async function seedCompletedStubSession(page: Page, sessionId: string) {
  await page.goto("/dashboard");
  await page.evaluate((jobId) => {
    window.localStorage.setItem(
      "mds01.jobs.v1",
      JSON.stringify([
        {
          jobId,
          recordingLabel: "Recording 01",
          submittedAt: new Date(Date.now() - 30_000).toISOString(),
          status: "complete",
          privacyMethod: {
            id: "metadata-scrub",
            label: "Metadata scrub",
            description:
              "Required baseline. Removes identifying EDF metadata while preserving waveform values.",
            previewTitle: "Waveform preserved",
            previewDescription:
              "The waveform stays the same. Identifying EDF header fields are removed before analysis.",
            required: true,
          },
        },
      ]),
    );
  }, sessionId);
  await page.goto(`/sessions/${encodeURIComponent(sessionId)}`);
}

test("upload opens one patient-folder review", async ({ page }) => {
  await page.goto("/upload");
  await expect(
    page.getByRole("heading", { name: "Add a patient recording" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Choose patient folder" }),
  ).toBeVisible();
  await expect(page.locator('input[type="file"]')).toHaveAttribute(
    "webkitdirectory",
    "",
  );
  await expect(page.getByRole("radio")).toHaveCount(0);
});

test("intake copy describes the combined workflow without a warning wall", async ({
  page,
}) => {
  await page.goto("/upload");
  await expect(
    page.getByText(/report, multiple EEG recordings, and video clips/i),
  ).toBeVisible();
  await expect(
    page.getByText(/not a diagnosis|research-only warning/i),
  ).toHaveCount(1);
});

test("legacy patient-intake route redirects to the unified upload", async ({
  page,
}) => {
  await page.goto("/patient-intake");
  await expect(page).toHaveURL(/\/upload$/);
  await expect(
    page.getByRole("heading", { name: "Add a patient recording" }),
  ).toBeVisible();
});

test("workspace shows safe case totals and exposes EEG tools", async ({
  page,
}) => {
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );
  await page.goto("/dashboard");
  if ((page.viewportSize()?.width ?? 0) >= 1024) {
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: "Skip to main content" }),
    ).toBeFocused();
    await expect(
      page.getByRole("link", { name: "Skip to main content" }),
    ).toHaveCSS("opacity", "1");
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
    await expect(
      page.getByRole("link", { name: "Skip to main content" }),
    ).toHaveCSS("opacity", "0");
  }
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recent patients / sessions" }),
  ).toBeVisible();
  const workspaces = page.getByRole("region", { name: "Analysis workspaces" });
  await expect(workspaces.getByRole("link", { name: /VEEG/ })).toHaveAttribute(
    "href",
    "/cases",
  );
  await expect(
    workspaces.locator('a[href="/upload/eeg?view=reviews"]'),
  ).toHaveCount(1);
  await expect(workspaces.getByRole("link", { name: /VIDEO/ })).toHaveAttribute(
    "href",
    "/video-reviews",
  );
  await expect(page.getByRole("link", { name: "New review" })).toHaveAttribute(
    "href",
    "/upload",
  );
  if ((page.viewportSize()?.width ?? 0) >= 1024) {
    const navigation = page.getByRole("navigation", {
      name: "Primary navigation",
    });
    await expect(
      navigation.getByRole("link", { name: "New patient review" }),
    ).toHaveAttribute("href", "/upload");
    await expect(
      navigation.getByRole("link", { name: "EEG workspace" }),
    ).toHaveAttribute("href", "/upload/eeg");
  }
  if ((page.viewportSize()?.width ?? 0) < 1024) {
    const menuButton = page.getByRole("button", { name: /navigation menu/ });
    await expect(menuButton).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "true");
    await expect(
      page
        .getByRole("navigation", { name: "Primary navigation" })
        .getByRole("link", { name: "Patient cases", exact: true }),
    ).toHaveAttribute("aria-current", "page");
    await expect(
      page
        .getByRole("navigation", { name: "Primary navigation" })
        .getByRole("link", { name: "New patient review", exact: true }),
    ).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "false");
  }
  await expect(page.getByText(/No patient cases yet/)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await expect(page.getByText("original_path")).not.toBeVisible();
});

test("workspace cards open EEG, video, and VEEG workspaces", async ({
  page,
}) => {
  await page.goto("/dashboard");
  const workspaces = page.getByRole("region", { name: "Analysis workspaces" });
  await workspaces.getByRole("link", { name: /VEEG/ }).click();
  await expect(page).toHaveURL(/\/cases$/);
  await expect(
    page.getByRole("heading", { name: "Patient cases", exact: true }),
  ).toBeVisible();
});

test("completed analysis presents the score timeline and EEG review", async ({
  page,
}) => {
  await seedCompletedStubSession(page, "MDS-STUB-RESULT");
  const sessionRegion = page.getByRole("region", { name: /MDS-/ });
  await expect(page.getByLabel("Status: Complete").first()).toBeVisible({
    timeout: 15000,
  });
  await page
    .getByRole("link", { name: /Open Recording 01 of 1 results/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Recording 01" }),
  ).toBeVisible();
  const signalPreviewEnabled =
    process.env.NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW === "true";
  const waveform = page.getByRole("region", {
    name: "EEG Viewer",
  });
  const waveformControl = page.getByRole("slider", {
    name: /18-channel EEG waveform/,
  });
  await expect(waveform).toHaveCount(signalPreviewEnabled ? 1 : 0);
  await expect(waveformControl).toHaveCount(signalPreviewEnabled ? 1 : 0);
  if (signalPreviewEnabled) {
    await expect(waveform.getByText("18 channels")).toBeVisible();
    const timeWindow = waveform.getByRole("combobox", {
      name: "EEG time window",
    });
    await expect(timeWindow).toHaveValue("10");
    await timeWindow.selectOption("5");
    await expect(timeWindow).toHaveValue("5");
    await timeWindow.selectOption("20");
    await expect(timeWindow).toHaveValue("20");
    await timeWindow.selectOption("110");
  } else {
    await expect(
      page.getByText("EEG waveform preview is disabled.", { exact: true }),
    ).toBeVisible();
  }
  const predictionTimeline = page.getByRole("group", {
    name: "Prediction score timeline",
  });
  await expect(predictionTimeline).toBeVisible();
  const accessibleAlertPoints = predictionTimeline.getByRole("button");
  await expect(accessibleAlertPoints.first()).toBeVisible();
  await expect(accessibleAlertPoints.first()).toHaveAttribute(
    "aria-label",
    /Window \d+/,
  );
  await expect(
    page.getByText("Alert threshold · 0.50", { exact: true }),
  ).toBeVisible();
  const alertNavigator = page.getByRole("group", {
    name: "Flagged windows",
  });
  await expect(alertNavigator).toHaveAttribute("tabindex", "0");
  const alertPoints = page.locator('svg circle[data-alert-point="true"]');
  expect(await alertPoints.count()).toBeGreaterThan(0);
  const displayedScores = await alertPoints.evaluateAll((points) =>
    points.map((point) => Number(point.getAttribute("data-score"))),
  );
  expect(displayedScores.every((score) => score >= 0.5)).toBe(true);
  await expect(page.getByTestId("prediction-score-line")).toHaveAttribute(
    "data-point-count",
    "29",
  );
  await alertPoints.first().focus();
  await expect(alertPoints.first()).toBeFocused();
  await alertNavigator.focus();
  await page.keyboard.press("End");
  await expect(page.getByText(/Flag \d+\/\d+ · .*score/)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Privacy representation preview" }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Research reference", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("navigation", { name: "Recordings in this session" }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Development · not a diagnosis", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Peak window score", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Threshold", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Shared timeline" }),
  ).toBeVisible();
  await expect(
    page.getByRole("group", { name: "EEG and video source-clock timeline" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Select manual event at EEG 0:42/ }),
  ).toBeVisible();
  await expect(page.getByText("Peak 4-second score")).toHaveCount(0);
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({
    path: test.info().outputPath("result.png"),
    fullPage: true,
  });
});

test("single recording result skips redundant navigation on tablet", async ({
  page,
}) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await seedCompletedStubSession(page, "MDS-STUB-TABLET");
  await expect(page.getByLabel("Status: Complete").first()).toBeVisible({
    timeout: 15000,
  });
  await page
    .getByRole("link", { name: /Open Recording 01 of 1 results/ })
    .click();
  await expect(
    page.getByRole("navigation", { name: "Recordings in this session" }),
  ).toHaveCount(0);
  const timeline = await page
    .getByRole("heading", { name: "Shared timeline" })
    .boundingBox();
  expect(timeline).not.toBeNull();
});

test("EEG source markers seek the matching synchronized video clip", async ({
  page,
}) => {
  await seedCompletedStubSession(page, "MDS-STUB-SYNCED");
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({
      json: {
        jobs: [
          {
            job_id: "VID-SYNCED-STUB",
            case_id: "CASE-B-SYNCED",
            label: "Video detection 000001",
            status: "ready",
            current_stage: "privacy-review-ready",
            duration_seconds: 4,
            fps: 25,
            blur_strength_percent: 100,
            review_privacy_method: "tracked-face-blur-with-full-frame-fallback",
            created_at: new Date().toISOString(),
            retention_expires_at: new Date(Date.now() + 3600000).toISOString(),
            video_available: true,
            error: null,
            sync: {
              status: "linked",
              record_id: "MDS-STUB-SYNCED",
              session_id: "MDS-STUB-SYNCED",
              eeg_source_start_seconds: 40,
              video_duration_seconds: 4,
              eeg_coverage_seconds: 4,
              mapped_segments: [
                {
                  video_start_seconds: 0,
                  video_end_seconds: 2,
                  eeg_source_start_seconds: 40,
                },
                {
                  video_start_seconds: 2,
                  video_end_seconds: 4,
                  eeg_source_start_seconds: 50,
                },
              ],
            },
          },
        ],
      },
    }),
  );
  await page.route(
    "**/api/video-detection/jobs/VID-SYNCED-STUB/predictions",
    (route) =>
      route.fulfill({
        json: {
          model: {
            model_name: "VSViG-base",
            model_version: "synthetic-test-only",
            weights_hash: "synthetic",
            preprocessing_version: "test",
            threshold: 0.5,
            sample_fps: 6,
            window_frames: 30,
            stride_frames: 15,
            calibrated: false,
          },
          predictions: [
            {
              start_time: 0,
              end_time: 4,
              raw_score: 0.8,
              score: 0.8,
              score_type: "uncalibrated_model_score",
              seizure_detected: true,
              model_evidence: {
                method: "vsvig-graph-grad-cam",
                target_class: "flagged",
                note: "Synthetic overlay evidence.",
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
                gradcam_samples: Array.from(
                  { length: 30 },
                  (_, sample_index) => ({
                    timestamp: sample_index / 6,
                    patches: Array.from({ length: 15 }, (_, patch_index) => ({
                      patch_index,
                      relevance: patch_index === 5 ? 1 : 0.05,
                    })),
                  }),
                ),
              },
            },
          ],
          intervals: [{ start_time: 0, end_time: 4 }],
          visualization: {
            available: true,
            media_type: "video/mp4",
            audio_included: false,
            privacy_method:
              "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
            face_blur_coverage: 0.8,
            full_frame_fallback_frames: 3,
            quality_flags: [],
          },
          recording_probability_available: false,
        },
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
          "Access-Control-Allow-Credentials": "true",
        },
      }),
  );
  const reviewVideo = await readFile(
    resolve(process.cwd(), "tests/fixtures/synthetic-review.mp4"),
  );
  await page.route(
    "**/api/video-detection/jobs/VID-SYNCED-STUB/visualization",
    (route) => {
      const range = route
        .request()
        .headers()
        .range?.match(/^bytes=(\d+)-(\d*)$/);
      const headers = {
        "Access-Control-Allow-Origin": "http://127.0.0.1:3001",
        "Access-Control-Allow-Credentials": "true",
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
      };
      if (!range)
        return route.fulfill({ status: 200, body: reviewVideo, headers });
      const start = Number(range[1]);
      const end = Math.min(
        range[2] ? Number(range[2]) : reviewVideo.length - 1,
        reviewVideo.length - 1,
      );
      const body = reviewVideo.subarray(start, end + 1);
      return route.fulfill({
        status: 206,
        body,
        headers: {
          ...headers,
          "Content-Length": String(body.length),
          "Content-Range": `bytes ${start}-${end}/${reviewVideo.length}`,
        },
      });
    },
  );

  await page.goto("/results/MDS-STUB-SYNCED");

  const review = page.getByRole("region", { name: "Shared timeline" });
  await expect(review).toBeVisible();
  await page
    .getByRole("button", { name: /Select manual event at EEG 0:42/ })
    .click();
  await page.getByRole("button", { name: "Open synchronized video" }).click();
  const synchronizedReview = page.getByRole("region", {
    name: "Synchronized camera video",
  });
  await expect(synchronizedReview).toBeVisible();
  await expect(
    synchronizedReview.getByLabel("Select synchronized video"),
  ).toHaveValue("VID-SYNCED-STUB");
  const player = page.getByTestId("synchronized-video-player");
  await expect
    .poll(() => player.evaluate((video: HTMLVideoElement) => video.currentTime))
    .toBeCloseTo(2, 0);
  await expect(page.getByTestId("video-vsvig-gradcam")).toBeVisible();
  await expect(
    page.getByText("EEG 0:42 · Video 01 · 0:02", { exact: true }),
  ).toBeVisible();

  await player.evaluate((video: HTMLVideoElement) => {
    video.currentTime = 1;
    video.dispatchEvent(new Event("timeupdate", { bubbles: true }));
  });
  await expect(
    page.getByText("EEG 0:41 · Video 01 · 0:01", { exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("video-vsvig-gradcam")).toHaveCount(0);

  await page.getByRole("button", { name: "Close" }).click();
  await page.getByRole("button", { name: /Window 21, 0:40–0:44/ }).click();
  await page.getByRole("button", { name: "Open synchronized video" }).click();
  await expect
    .poll(() => player.evaluate((video: HTMLVideoElement) => video.currentTime))
    .toBeCloseTo(2, 0);
  await page.getByRole("button", { name: "Close" }).click();
  const sharedTimeline = page.getByRole("group", {
    name: "Shared EEG timeline. Click or drag any lane to seek; use arrow keys to move one second.",
  });
  await sharedTimeline.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("status", { name: "EEG 0:46 · No video" }),
  ).toBeVisible();

  const markerLane = sharedTimeline.locator("[data-timeline-track]").nth(1);
  const markerLaneBounds = await markerLane.boundingBox();
  expect(markerLaneBounds).not.toBeNull();
  await page.mouse.move(
    markerLaneBounds!.x + 5,
    markerLaneBounds!.y + markerLaneBounds!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    markerLaneBounds!.x + markerLaneBounds!.width * 0.75,
    markerLaneBounds!.y + markerLaneBounds!.height / 2,
  );
  await page.mouse.up();
  await expect
    .poll(() =>
      page.getByRole("status", { name: /EEG 0:/ }).getAttribute("aria-label"),
    )
    .not.toContain("0:46");
});

test("EEG review lists every same-case video synchronization outcome", async ({
  page,
}) => {
  const sessionId = "MDS-STUB-SYNC-INVENTORY";
  const caseId = `CASE-${sessionId.slice(-8)}`;
  await seedCompletedStubSession(page, sessionId);
  const createJob = (
    jobId: string,
    caseId: string,
    syncStatus: string,
    recordId: string | null = null,
  ) => ({
    job_id: jobId,
    case_id: caseId,
    label: `Video detection ${jobId.slice(-6)}`,
    status: "failed",
    current_stage: "privacy-review-ready",
    duration_seconds: 4,
    fps: 25,
    blur_strength_percent: 100,
    created_at: new Date().toISOString(),
    retention_expires_at: new Date(Date.now() + 3600000).toISOString(),
    video_available: true,
    error: "OpenPose could not detect all required landmarks.",
    sync: {
      status: syncStatus,
      record_id: recordId,
      session_id: "MDS-STUB-SYNC-INVENTORY",
      eeg_source_start_seconds: 40,
      video_duration_seconds: 4,
      eeg_coverage_seconds: 4,
      mapped_segments:
        syncStatus === "linked"
          ? [
              {
                video_start_seconds: 0,
                video_end_seconds: 4,
                eeg_source_start_seconds: 40,
              },
            ]
          : [],
    },
  });
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({
      json: {
        jobs: [
          createJob("VID-LINKED-CURRENT", caseId, "linked", sessionId),
          createJob(
            "VID-LINKED-OTHER",
            caseId,
            "linked",
            "MDS-OTHER-RECORDING",
          ),
          createJob("VID-UNMATCHED", caseId, "unmatched"),
          createJob("VID-AMBIGUOUS", caseId, "ambiguous"),
          createJob("VID-UNAVAILABLE", caseId, "unavailable"),
          {
            ...createJob("VID-PENDING", caseId, "pending"),
            status: "queued",
            video_available: false,
          },
          createJob("VID-OTHER-CASE", "CASE-OTHER", "unmatched"),
        ],
      },
    }),
  );

  await page.goto("/results/MDS-STUB-SYNC-INVENTORY");
  await expect(
    page.getByRole("group", { name: "EEG and video source-clock timeline" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Video synchronization status" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Select Video 01 coverage/ }),
  ).toBeVisible();
});

test("EEG sessions group recordings under the session timestamp", async ({
  page,
}) => {
  await seedCompletedStubSession(page, "MDS-STUB-GROUPED");
  await page.getByRole("link", { name: "Back to EEG sessions" }).click();
  await expect(
    page.getByRole("heading", { name: "EEG reviews" }),
  ).toBeVisible();
  await expect(
    page.getByText("1 EEG recordings", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("1 complete · 0 need review")).toBeVisible();
  await page.getByRole("link", { name: "Open session" }).click();
  await expect(page).toHaveURL(/\/sessions\//);
  await expect(
    page.getByText("Recordings in this session", { exact: true }),
  ).toBeVisible();
});

test("completed EEG sessions can be deleted from their review", async ({
  page,
}) => {
  await seedCompletedStubSession(page, "MDS-STUB-DELETE");
  await expect(page.getByLabel("Status: Complete").first()).toBeVisible({
    timeout: 15000,
  });
  await page.getByRole("button", { name: "Delete session" }).first().click();
  await expect(
    page.getByRole("alertdialog", { name: "Delete this session?" }),
  ).toBeVisible();
  await page.waitForTimeout(1000);
  await expect(
    page.getByRole("alertdialog", { name: "Delete this session?" }),
  ).toBeVisible();
  await page
    .getByRole("alertdialog", { name: "Delete this session?" })
    .getByRole("button", { name: "Delete session" })
    .click({ force: true });
  await expect(page).toHaveURL(/\/upload\/eeg\?view=reviews$/);
  await expect(page.getByText("No EEG sessions yet")).toBeVisible();
});

test("unknown result has a recoverable error state", async ({ page }) => {
  await page.goto("/results/not-a-real-job");
  await expect(
    page.getByRole("heading", { name: "Result unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Return to EEG sessions/ }),
  ).toBeVisible();
});

test("verified EEG-video metadata aligns source markers in the research report", async ({
  page,
}) => {
  const sessionId = "MDS-STUB-DEMO-REPORT";
  const caseId = `CASE-${sessionId.slice(-8)}`;
  await page.addInitScript(() => {
    window.print = () => {
      document.documentElement.dataset.printRequested = "true";
    };
  });
  const videoJob = {
    job_id: "VID-demo-report",
    case_id: caseId,
    label: "Demo video review",
    status: "ready",
    current_stage: "complete",
    duration_seconds: 120,
    fps: 25,
    created_at: new Date().toISOString(),
    retention_expires_at: new Date(Date.now() + 3600000).toISOString(),
    video_available: false,
    visualization_available: false,
    visualization_url: null,
    error: null,
    sync: {
      status: "linked",
      record_id: sessionId,
      session_id: sessionId,
      eeg_source_start_seconds: 0,
      video_duration_seconds: 120,
      eeg_coverage_seconds: 120,
      mapped_segments: [
        {
          video_start_seconds: 0,
          video_end_seconds: 120,
          eeg_source_start_seconds: 0,
        },
      ],
    },
  };
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() === "POST")
      return route.fulfill({ json: { job: videoJob } });
    return route.fulfill({ json: { jobs: [videoJob] } });
  });
  await page.route("**/api/video-detection/jobs/VID-demo-report", (route) =>
    route.fulfill({ json: { job: videoJob } }),
  );
  await page.route(
    "**/api/video-detection/jobs/VID-demo-report/predictions",
    (route) =>
      route.fulfill({
        json: {
          duration_seconds: 120,
          model: {
            model_name: "VSViG-base",
            model_version: "demo-contract",
            weights_hash: "",
            preprocessing_version: "demo",
            threshold: 0.5,
            sample_fps: 6,
            window_frames: 30,
            stride_frames: 3,
            calibrated: false,
          },
          predictions: [
            {
              start_time: 90,
              end_time: 95,
              raw_score: 0.73,
              score: 0.73,
              score_type: "uncalibrated_model_score",
              seizure_detected: true,
            },
          ],
          intervals: [{ start_time: 90, end_time: 95 }],
          summary: {
            peak_score: 0.73,
            potential_event_detected: true,
            event_count: 1,
            threshold: 0.5,
          },
          recording_probability_available: false,
        },
      }),
  );

  await seedCompletedStubSession(page, sessionId);
  await page.goto(
    `/analysis?sessionId=${sessionId}&videoJobId=VID-demo-report`,
  );

  await expect(
    page.getByRole("heading", { name: "EEG and video review" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(page.getByText("1 of 1 recordings complete")).toBeVisible({
    timeout: 15000,
  });
  await expect(
    page.getByText("Unique metadata match among uploaded clips"),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "EEG and video timeline" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /EEG flagged windows:/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /Video flagged windows:/ }),
  ).toBeVisible();
  await expect(
    page.getByText(/The camera clock is linked from Nicolet frame markers/),
  ).toBeVisible();
  await page.getByText("Imported EEG markers", { exact: true }).click();
  await page.getByText("View marker times", { exact: true }).click();
  await expect(page.getByText("Manual source marker")).toBeVisible();
  await expect(page.getByText("Video 0:42", { exact: true })).toBeVisible();
  await expect(page.getByText("VSViG-base", { exact: false })).toBeVisible();
  await expect(
    page.getByText("Uncalibrated · not a probability"),
  ).toBeVisible();
  await expect(
    page.getByText("Research output · not a diagnosis", { exact: false }),
  ).toBeVisible();

  await page.screenshot({
    path: test.info().outputPath("demo-analysis-report.png"),
    fullPage: true,
  });
  await page.emulateMedia({ media: "print" });
  await expect(
    page.getByRole("button", { name: "Print / Save as PDF" }),
  ).toBeHidden();
  await expect(
    page.getByText("Unique metadata match among uploaded clips"),
  ).toBeVisible();
  if (test.info().project.name === "desktop") {
    const pdf = await page.pdf({
      path: test.info().outputPath("demo-analysis-report.pdf"),
      format: "A4",
      printBackground: true,
    });
    expect(pdf.subarray(0, 5).toString("ascii")).toBe("%PDF-");
    expect(pdf.byteLength).toBeGreaterThan(1000);
  }
  await page.screenshot({
    path: test.info().outputPath("demo-analysis-report-print.png"),
    fullPage: true,
  });
  await page.emulateMedia({ media: "screen" });
  await page.getByRole("button", { name: "Print / Save as PDF" }).click();
  await expect(page.locator("html")).toHaveAttribute(
    "data-print-requested",
    "true",
  );
});
