import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("submits a video to a standalone privacy job and shows only protected output", async ({ page }) => {
  await page.goto("/video-privacy");
  await expect(page.getByRole("heading", { name: "Choose a privacy profile" })).toBeVisible();
  await page.getByRole("radio", { name: /Pose-only/ }).check();
  await page.locator("#video-file").setInputFiles({ name: "patient-confidential.mp4", mimeType: "video/mp4", buffer: Buffer.from("synthetic video") });
  await page.getByRole("button", { name: "Start privacy transform" }).click();
  await expect(page).toHaveURL(/\/video-privacy\/VID-/);
  await expect(page.getByRole("heading", { name: "Video upload 01" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Privacy processing" })).toBeVisible();
  await expect(page.getByText("Preflight", { exact: true })).toBeVisible();
  await expect(page.getByText("Ready for review", { exact: true })).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("heading", { name: "Protected preview frame" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Download protected video/ })).toBeVisible();
  await expect(page.getByText("patient-confidential.mp4", { exact: true })).toHaveCount(0);
  await expect(page.getByText(/EEG|H5|model/i)).toHaveCount(0);
  await page.screenshot({ path: test.info().outputPath("video-privacy.png"), fullPage: true });
});

test("profile choices are a real single-choice group", async ({ page }) => {
  await page.goto("/video-privacy");
  await expect(page.getByRole("radio")).toHaveCount(2);
  await expect(page.getByRole("radio", { name: /Face redaction/ })).toBeChecked();
  await page.getByRole("radio", { name: /Pose-only/ }).check();
  await expect(page.getByRole("radio", { name: /Face redaction/ })).not.toBeChecked();
  await expect(page.getByRole("radio", { name: /Pose-only/ })).toBeChecked();
});
