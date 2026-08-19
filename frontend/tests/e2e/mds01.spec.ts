import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("upload leads with one clear action and creates a queued analysis", async ({ page }) => {
  await page.goto("/upload");
  await expect(page.getByRole("heading", { name: "Submit an EEG recording for analysis." })).toBeVisible();
  await page.getByLabel("EEG recording").setInputFiles({ name: "recording_01.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await page.getByRole("radio", { name: /Cancellable signal projection/ }).check();
  await page.screenshot({ path: test.info().outputPath("upload.png"), fullPage: true });
  await page.getByRole("button", { name: "Submit for Analysis" }).click();
  await expect(page).toHaveURL(/sessions/);
  await expect(page.getByText("Analysis session", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Recordings in this session" }).getByText("Recording 01 of 1", { exact: true }).first()).toBeVisible();
 await expect(page.getByRole("region", { name: /MDS-/ }).getByRole("status", { name: "Status: Queued" })).toBeVisible();
  const processingStatus = page.getByRole("region", { name: /MDS-/ }).getByRole("status", { name: "Status: Processing" });
  await expect(processingStatus).toBeVisible({ timeout: 5000 });
  await expect(processingStatus.locator("svg")).toHaveClass(/animate-spin/);
});

test("dashboard shows an empty state and no private fields", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Analysis dashboard" })).toBeVisible();
  if ((page.viewportSize()?.width ?? 0) < 1024) {
    const menuButton = page.getByRole("button", { name: /navigation menu/ });
    await expect(menuButton).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "New analysis" })).toBeVisible();
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "false");
  }
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
  const sessionRegion = page.getByRole("region", { name: /MDS-/ });
  await expect(sessionRegion.getByRole("status", { name: "Status: Complete" })).toBeVisible({ timeout: 10000 });
  await page.getByRole("link", { name: /Open Recording 01 of 1 results/ }).click();
  await expect(page.getByRole("heading", { name: "Development activity flagged" })).toBeVisible();
  await expect(page.getByText("Development-stub score", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("img", { name: /18-channel de-identified EEG viewer/ })).toBeVisible();
  await expect(page.getByText("Dataset annotation unavailable")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Recordings in this session" })).toBeVisible();
  await expect(page.getByText("Non-clinical output")).toBeVisible();
  await expect(page.getByText("patient_reference")).not.toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: test.info().outputPath("result.png"), fullPage: true });
});

test("dashboard groups recordings under the session timestamp", async ({ page }) => {
 await page.goto("/upload");
 await page.getByLabel("EEG recording").setInputFiles({ name: "grouped_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
 await page.getByRole("button", { name: "Submit for Analysis" }).click();
 await page.getByRole("link", { name: "Back to dashboard" }).click();
 await expect(page.getByRole("heading", { name: "Analysis dashboard" })).toBeVisible();
 await expect(page.getByText(/1 session/)).toBeVisible();
 await expect(page.getByText("Submitted")).toBeVisible();
 const sessionRegion = page.getByRole("region", { name: /MDS-/ });
 await expect(sessionRegion.getByText("Recording 01 of 1", { exact: true }).first()).toBeHidden();
  await expect(sessionRegion.getByText("Dataset findings available after processing", { exact: true })).toBeVisible();
  await sessionRegion.getByRole("link", { name: /Open session/ }).click();
  await expect(page).toHaveURL(/\/sessions\//);
  await expect(page.getByText("Recordings in this session", { exact: true })).toBeVisible();
});

test("completed sessions can be deleted from the dashboard", async ({ page }) => {
  await page.goto("/upload");
  await page.getByLabel("EEG recording").setInputFiles({ name: "delete_case.zip", mimeType: "application/zip", buffer: Buffer.from("synthetic") });
  await page.getByRole("button", { name: "Submit for Analysis" }).click();
 const sessionRegion = page.getByRole("region", { name: /MDS-/ });
 await expect(sessionRegion.getByRole("status", { name: "Status: Complete" })).toBeVisible({ timeout: 10000 });
 await page.getByRole("link", { name: "Back to dashboard" }).click();
 const dashboardSession = page.getByRole("region", { name: /MDS-/ });
 page.once("dialog", (dialog) => void dialog.accept());
 await dashboardSession.getByRole("button", { name: "Delete session" }).click();
  await expect(page.getByText("No analyses submitted yet.")).toBeVisible();
});

test("unknown result has a recoverable error state", async ({ page }) => {
  await page.goto("/results/not-a-real-job");
  await expect(page.getByRole("heading", { name: "Result unavailable" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Return to dashboard/ })).toBeVisible();
});
