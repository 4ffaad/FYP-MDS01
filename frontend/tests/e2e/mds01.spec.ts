import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("upload leads with one clear action and creates a queued analysis", async ({ page }) => {
  await page.goto("/upload");
  await expect(page.getByRole("heading", { name: "Submit an EEG recording for analysis." })).toBeVisible();
  await page.getByLabel("EEG recording").setInputFiles({ name: "recording_01.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await page.getByRole("radio", { name: /Channel Anonymization/ }).check();
  await page.screenshot({ path: test.info().outputPath("upload.png"), fullPage: true });
  await page.getByRole("button", { name: "Submit for Analysis" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByText("Recording 01")).toBeVisible();
  await expect(page.locator('[role="status"]', { hasText: "Queued" })).toBeVisible();
});

test("dashboard shows an empty state and no private fields", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Analysis dashboard" })).toBeVisible();
  await expect(page.getByText("No analyses submitted yet.")).toBeVisible();
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await expect(page.getByText("original_path")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: test.info().outputPath("dashboard.png"), fullPage: true });
});

test("completed analysis opens a result with confidence and explanation notice", async ({ page }) => {
  await page.goto("/upload");
  await page.getByLabel("EEG recording").setInputFiles({ name: "review_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await page.getByRole("button", { name: "Submit for Analysis" }).click();
  await expect(page.locator('[role="status"]', { hasText: "Queued" })).toBeVisible();
  await expect(page.locator('[role="status"]', { hasText: "Complete" })).toBeVisible({ timeout: 10000 });
  await page.getByRole("link", { name: /Open Recording 01 results/ }).click();
  await expect(page.getByRole("heading", { name: /pattern indicated/ })).toBeVisible();
  await expect(page.getByText("Model confidence")).toBeVisible();
  await expect(page.getByRole("img", { name: /EEG waveform with attention weighting/ })).toBeVisible();
  await expect(page.getByText("Non-clinical output")).toBeVisible();
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: test.info().outputPath("result.png"), fullPage: true });
});

test("unknown result has a recoverable error state", async ({ page }) => {
  await page.goto("/results/not-a-real-job");
  await expect(page.getByRole("heading", { name: "Result unavailable" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Return to dashboard/ })).toBeVisible();
});
