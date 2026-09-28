import { expect, test, type Page } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const key = "mds01.e2e-cleaned";
    if (window.sessionStorage.getItem(key)) return;
    window.localStorage.clear();
    window.sessionStorage.setItem(key, "true");
  });
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
    page.getByRole("link", { name: "MDS01 patient review" }),
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
  ).toHaveCount(0);
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

test("VEEG analysis shows an empty state and no private fields", async ({
  page,
}) => {
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
  await expect(
    page.getByRole("heading", { name: "VEEG analysis" }),
  ).toBeVisible();
  if ((page.viewportSize()?.width ?? 0) >= 1024) {
    await expect(
      page
        .getByRole("navigation", { name: "Primary navigation" })
        .getByRole("link", { name: "New patient review", exact: true }),
    ).toHaveAttribute("href", "/upload");
  }
  if ((page.viewportSize()?.width ?? 0) < 1024) {
    const menuButton = page.getByRole("button", { name: /navigation menu/ });
    await expect(menuButton).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "true");
    await expect(
      page
        .getByRole("navigation", { name: "Primary navigation" })
        .getByRole("link", { name: "Workspace", exact: true }),
    ).toHaveAttribute("aria-current", "page");
    await expect(
      page
        .getByRole("navigation", { name: "Primary navigation" })
        .getByRole("link", { name: "New patient review", exact: true }),
    ).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "false");
  }
  await expect(page.getByText("No VEEG analyses yet.")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await expect(page.getByText("original_path")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({
    path: test.info().outputPath("dashboard.png"),
    fullPage: true,
  });
});

test("completed analysis opens a result with a score timeline and explanation notice", async ({
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
    page.getByRole("heading", { name: "Development flag" }),
  ).toBeVisible();
  const signalPreviewEnabled =
    process.env.NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW === "true";
  await expect(
    page.getByRole("region", { name: "VEEG waveform review" }),
  ).toHaveCount(signalPreviewEnabled ? 1 : 0);
  await expect(
    page.getByRole("img", { name: /Display-normalized 18-channel VEEG/ }),
  ).toHaveCount(signalPreviewEnabled ? 1 : 0);
  const signalNotice = page.getByText(
    "VEEG viewing is disabled because the signal can remain biometrically sensitive.",
    { exact: true },
  );
  if (signalPreviewEnabled) {
    await expect(signalNotice).toHaveCount(0);
  } else {
    await expect(signalNotice).toBeVisible();
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
    name: /Browse exact flagged windows/,
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
  await expect(
    page.getByText(/Flagged window \d+ of \d+ · .*score/),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Privacy representation preview" }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Research reference", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("navigation", { name: "Recordings in this session" }),
  ).toBeVisible();
  await expect(page.getByText("Development output only")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Source EEG event markers" }),
  ).toBeVisible();
  await expect(page.getByText("Synthetic demo marker")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "How to read this output" }),
  ).toBeVisible();
  await expect(
    page.getByText(/does not explain why the model produced a score/i),
  ).toBeVisible();
  await expect(
    page.getByText(/flagged windows|No flagged windows/).first(),
  ).toBeVisible();
  await expect(page.getByText("Peak 4-second score")).toHaveCount(0);
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({
    path: test.info().outputPath("result.png"),
    fullPage: true,
  });
});

test("recording navigation precedes result details on tablet", async ({
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
  const navigation = await page
    .getByRole("navigation", { name: "Recordings in this session" })
    .boundingBox();
  const timeline = await page
    .getByRole("heading", { name: "Prediction score timeline" })
    .boundingBox();
  expect(navigation).not.toBeNull();
  expect(timeline).not.toBeNull();
  expect(navigation!.y).toBeLessThan(timeline!.y);
});

test("VEEG analysis groups recordings under the session timestamp", async ({
  page,
}) => {
  await seedCompletedStubSession(page, "MDS-STUB-GROUPED");
  await page.getByRole("link", { name: "Back to VEEG analysis" }).click();
  await expect(
    page.getByRole("heading", { name: "VEEG analysis" }),
  ).toBeVisible();
  await expect(page.getByText(/1 VEEG session/)).toBeVisible();
  await expect(page.getByText("Submitted")).toBeVisible();
  const sessionRegion = page.getByRole("region", { name: /MDS-/ });
  await expect(
    sessionRegion.getByText("Recording 01 of 1", { exact: true }).first(),
  ).toBeHidden();
  await expect(
    sessionRegion.getByText(
      /Results pending|recordings? with (model alerts|development flags)|No (model alerts|development flags) detected/,
    ),
  ).toBeVisible();
  await sessionRegion.getByRole("link", { name: /Open session/ }).click();
  await expect(page).toHaveURL(/\/sessions\//);
  await expect(
    page.getByText("Recordings in this session", { exact: true }),
  ).toBeVisible();
});

test("completed sessions can be deleted from VEEG analysis", async ({
  page,
}) => {
  await seedCompletedStubSession(page, "MDS-STUB-DELETE");
  const sessionRegion = page.getByRole("region", { name: /MDS-/ });
  await expect(page.getByLabel("Status: Complete").first()).toBeVisible({
    timeout: 15000,
  });
  await page.getByRole("link", { name: "Back to VEEG analysis" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const dashboardSession = page.getByRole("region", { name: /MDS-/ });
  await dashboardSession
    .getByRole("button", { name: "Delete session" })
    .click();
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
  await expect(page.getByText("No VEEG analyses yet.")).toBeVisible();
});

test("unknown result has a recoverable error state", async ({ page }) => {
  await page.goto("/results/not-a-real-job");
  await expect(
    page.getByRole("heading", { name: "Result unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Return to VEEG analysis/ }),
  ).toBeVisible();
});

test("demo report shows assumed EEG-video timing and prints a research-only summary", async ({
  page,
}) => {
  await page.addInitScript(() => {
    window.print = () => {
      document.documentElement.dataset.printRequested = "true";
    };
  });
  const videoJob = {
    job_id: "VID-demo-report",
    case_id: null,
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

  await seedCompletedStubSession(page, "MDS-STUB-DEMO-REPORT");
  await page.goto(
    "/analysis?sessionId=MDS-STUB-DEMO-REPORT&videoJobId=VID-demo-report",
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
  await expect(page.getByText("Assumed pairing — not verified")).toBeVisible();
  await expect(
    page.getByText("These analyses are shown together for demonstration only", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.getByText("Synthetic demo marker")).toBeVisible();
  await expect(page.getByText("Video 0:42", { exact: true })).toBeVisible();
  await expect(page.getByText("VSViG-base", { exact: false })).toBeVisible();
  await expect(
    page.getByText("Uncalibrated · not a probability"),
  ).toBeVisible();
  await expect(
    page.getByText("Research and demonstration output only", { exact: false }),
  ).toBeVisible();

  const offset = page.getByLabel("Video starts after EEG (seconds)");
  await offset.fill("12");
  await expect(page.getByText("Video 0:30", { exact: true })).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("demo-analysis-report.png"),
    fullPage: true,
  });
  await page.emulateMedia({ media: "print" });
  await expect(
    page.getByRole("button", { name: "Print / Save as PDF" }),
  ).toBeHidden();
  await expect(page.getByText(/Assumed clock offset: \+12s/)).toBeVisible();
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
