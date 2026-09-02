import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("upload leads with one clear action and creates a queued analysis", async ({ page }) => {
  await page.goto("/upload");
  await expect(page.getByRole("heading", { name: "Upload an EEG archive" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
  const archiveInput = page.locator("#eeg-file");
  await archiveInput.focus();
  const uploadTarget = page.locator('label[for="eeg-file"]');
  expect(await uploadTarget.evaluate((element) => getComputedStyle(element).boxShadow)).not.toBe("none");
  await archiveInput.setInputFiles({ name: "recording_01.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await expect(page.getByText("Required baseline", { exact: true })).toBeVisible({ timeout: 15000 });
  await page.getByRole("checkbox", { name: /Signal obfuscation/ }).check();
  await page.screenshot({ path: test.info().outputPath("upload.png"), fullPage: true });
  await page.getByRole("button", { name: "Submit for analysis" }).click();
  await expect(page).toHaveURL(/sessions/);
  await expect(page.getByText("Analysis session", { exact: true })).toBeVisible();
  await expect(page.getByText("1 recording still processing. Only completed results are shown.", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Status: Queued")).toBeVisible();
  const processingStatus = page.getByLabel("Status: Processing");
  await expect(processingStatus).toBeVisible({ timeout: 5000 });
  await expect(processingStatus.locator("svg")).toHaveClass(/animate-spin/);
});

test("privacy preview shows the fixed 18-channel contract and an accessible divider", async ({ page }) => {
  const signalRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/signal")) signalRequests.push(request.url());
  });
  await page.goto("/upload");
  await page.locator("#eeg-file").setInputFiles({ name: "preview_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await expect(page.getByRole("checkbox", { name: /Signal obfuscation/ })).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("img", { name: /Synthetic 18-channel EEG preview/ })).toBeVisible();
  await expect(page.getByText("FP1-F7", { exact: true })).toBeVisible();
  await expect(page.getByText("CZ-PZ", { exact: true })).toBeVisible();
  const previewScroller = page.getByRole("region", { name: /Waveform preserved/ }).locator(".overflow-x-auto");
  expect(await previewScroller.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
  const divider = page.getByRole("slider", { name: "Before and after preview divider" });
  await expect(divider).toHaveAttribute("aria-valuetext", /50% before.*50% after/);
  await divider.focus();
  await page.keyboard.press("Home");
  await expect(divider).toHaveAttribute("aria-valuetext", /100% before.*0% after/);
  await expect(page.locator('clipPath[data-layer-clip="before"] rect')).toHaveAttribute("width", "100");
  await expect(page.locator('clipPath[data-layer-clip="after"] rect')).toHaveAttribute("width", "0");
  await page.keyboard.press("End");
  await expect(divider).toHaveAttribute("aria-valuetext", /100% after/);
  await expect(page.locator('clipPath[data-layer-clip="before"] rect')).toHaveAttribute("width", "0");
  await expect(page.locator('clipPath[data-layer-clip="after"] rect')).toHaveAttribute("width", "100");
  await page.getByRole("checkbox", { name: /Signal obfuscation/ }).check();
  await expect(page.getByText("Signal detail reduced")).toBeVisible();
  expect(signalRequests).toHaveLength(0);
});

test("EEG analysis shows an empty state and no private fields", async ({ page }) => {
  await page.goto("/dashboard");
  if ((page.viewportSize()?.width ?? 0) >= 1024) {
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
  }
  await expect(page.getByRole("heading", { name: "EEG analysis" })).toBeVisible();
  await expect(page.locator('[data-slot="button"]', { hasText: "New EEG analysis" })).toHaveCSS("color", "rgb(255, 255, 255)");
  if ((page.viewportSize()?.width ?? 0) < 1024) {
    const menuButton = page.getByRole("button", { name: /navigation menu/ });
    await expect(menuButton).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "New EEG analysis" })).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "false");
  }
  await expect(page.getByText("No EEG analyses yet.")).toBeVisible();
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await expect(page.getByText("original_path")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: test.info().outputPath("dashboard.png"), fullPage: true });
});

test("completed analysis opens a result with a score timeline and explanation notice", async ({ page }) => {
  await page.goto("/upload");
  await page.locator("#eeg-file").setInputFiles({ name: "review_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await expect(page.getByRole("button", { name: "Submit for analysis" })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Submit for analysis" }).click();
  const sessionRegion = page.getByRole("region", { name: /MDS-/ });
  await expect(page.getByLabel("Status: Complete").first()).toBeVisible({ timeout: 15000 });
  await page.getByRole("link", { name: /Open Recording 01 of 1 results/ }).click();
  await expect(page.getByRole("heading", { name: "Development flag" })).toBeVisible();
  await expect(page.getByRole("region", { name: "EEG waveform review" })).toBeVisible();
  await expect(page.getByRole("img", { name: /Display-normalized 18-channel EEG/ })).toBeVisible();
  await expect(page.getByText("EEG viewing is disabled because the signal can remain biometrically sensitive.", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("img", { name: "Prediction score timeline" })).toBeVisible();
  await expect(page.getByText("Alert threshold · 0.50", { exact: true })).toBeVisible();
  const alertNavigator = page.getByRole("group", { name: /Browse exact flagged windows/ });
  await expect(alertNavigator).toHaveAttribute("tabindex", "0");
  const alertPoints = page.locator('svg circle[data-alert-point="true"]');
  expect(await alertPoints.count()).toBeGreaterThan(0);
  const displayedScores = await alertPoints.evaluateAll((points) => points.map((point) => Number(point.getAttribute("data-score"))));
  expect(displayedScores.every((score) => score >= 0.5)).toBe(true);
  await expect(page.getByTestId("prediction-score-line")).toHaveAttribute("data-point-count", "29");
  await alertPoints.first().focus();
  await expect(alertPoints.first()).toBeFocused();
  await alertNavigator.focus();
  await page.keyboard.press("End");
  await expect(page.getByText(/Flagged window \d+ of \d+ · .*score/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Privacy representation preview" })).toHaveCount(0);
  await expect(page.getByText("Research reference", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Recordings in this session" })).toBeVisible();
  await expect(page.getByText("Development output only")).toBeVisible();
  await expect(page.getByRole("heading", { name: "How to read this output" })).toBeVisible();
  await expect(page.getByText(/does not explain why the model produced a score/i)).toBeVisible();
  await expect(page.getByText(/flagged windows|No flagged windows/).first()).toBeVisible();
  await expect(page.getByText("Peak 4-second score")).toHaveCount(0);
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: test.info().outputPath("result.png"), fullPage: true });
});

test("recording navigation precedes result details on tablet", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await page.goto("/upload");
  await page.locator("#eeg-file").setInputFiles({ name: "tablet_review.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await expect(page.getByRole("button", { name: "Submit for analysis" })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Submit for analysis" }).click();
  await expect(page.getByLabel("Status: Complete").first()).toBeVisible({ timeout: 15000 });
  await page.getByRole("link", { name: /Open Recording 01 of 1 results/ }).click();
  const navigation = await page.getByRole("navigation", { name: "Recordings in this session" }).boundingBox();
  const timeline = await page.getByRole("heading", { name: "Prediction score timeline" }).boundingBox();
  expect(navigation).not.toBeNull();
  expect(timeline).not.toBeNull();
  expect(navigation!.y).toBeLessThan(timeline!.y);
});

test("EEG analysis groups recordings under the session timestamp", async ({ page }) => {
 await page.goto("/upload");
 await page.locator("#eeg-file").setInputFiles({ name: "grouped_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
 await expect(page.getByRole("button", { name: "Submit for analysis" })).toBeVisible({ timeout: 15000 });
 await page.getByRole("button", { name: "Submit for analysis" }).click();
 await page.getByRole("link", { name: "Back to EEG analysis" }).click();
 await expect(page.getByRole("heading", { name: "EEG analysis" })).toBeVisible();
 await expect(page.getByText(/1 EEG session/)).toBeVisible();
 await expect(page.getByText("Submitted")).toBeVisible();
 const sessionRegion = page.getByRole("region", { name: /MDS-/ });
 await expect(sessionRegion.getByText("Recording 01 of 1", { exact: true }).first()).toBeHidden();
  await expect(sessionRegion.getByText(/Results pending|recordings? with (model alerts|development flags)|No (model alerts|development flags) detected/)).toBeVisible();
  await sessionRegion.getByRole("link", { name: /Open session/ }).click();
  await expect(page).toHaveURL(/\/sessions\//);
  await expect(page.getByText("Recordings in this session", { exact: true })).toBeVisible();
});

test("completed sessions can be deleted from EEG analysis", async ({ page }) => {
  await page.goto("/upload");
  await page.locator("#eeg-file").setInputFiles({ name: "delete_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await expect(page.getByRole("button", { name: "Submit for analysis" })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Submit for analysis" }).click();
 const sessionRegion = page.getByRole("region", { name: /MDS-/ });
 await expect(page.getByLabel("Status: Complete").first()).toBeVisible({ timeout: 15000 });
 await page.getByRole("link", { name: "Back to EEG analysis" }).click();
 await expect(page).toHaveURL(/\/dashboard$/);
 const dashboardSession = page.getByRole("region", { name: /MDS-/ });
 await dashboardSession.getByRole("button", { name: "Delete session" }).click();
 await expect(page.getByRole("alertdialog", { name: "Delete this session?" })).toBeVisible();
 await page.waitForTimeout(1000);
 await expect(page.getByRole("alertdialog", { name: "Delete this session?" })).toBeVisible();
 await page.getByRole("alertdialog", { name: "Delete this session?" }).getByRole("button", { name: "Delete session" }).click({ force: true });
  await expect(page.getByText("No EEG analyses yet.")).toBeVisible();
});

test("unknown result has a recoverable error state", async ({ page }) => {
  await page.goto("/results/not-a-real-job");
  await expect(page.getByRole("heading", { name: "Result unavailable" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Return to EEG analysis/ })).toBeVisible();
});
