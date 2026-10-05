import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("legacy video privacy routes use the unified video workspace", async ({
  page,
}) => {
  await page.goto("/video-privacy");
  await expect(page.getByRole("heading", { name: "Video" })).toBeVisible();
  await expect(page).toHaveURL(/\/video-detection$/);
  await expect(
    page
      .getByRole("navigation", { name: "Video workspace" })
      .getByRole("link", { name: "New video analysis" }),
  ).toBeVisible();

  await page.goto("/video-privacy/legacy-job");
  await expect(page).toHaveURL(/\/video-detection\?view=reviews$/);
  await expect(
    page.getByRole("heading", { name: "Video reviews" }),
  ).toBeVisible();
});
