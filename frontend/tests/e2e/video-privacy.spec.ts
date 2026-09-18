import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("video privacy route opens its protected transform workflow", async ({
  page,
}) => {
  await page.goto("/video-privacy");
  await expect(
    page.getByRole("heading", {
      name: "Protect a patient video before review",
    }),
  ).toBeVisible();
  await expect(page.getByText("Audio excluded:")).toBeVisible();
});
