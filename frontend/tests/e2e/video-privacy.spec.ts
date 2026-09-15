import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("legacy video privacy route redirects to unified VEEG video review", async ({
  page,
}) => {
  await page.goto("/video-privacy");
  await expect(page).toHaveURL(/\/video-detection$/);
  await expect(
    page.getByRole("heading", { name: "Video seizure detection" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Face redaction runs before pose extraction/i),
  ).toBeVisible();
});
