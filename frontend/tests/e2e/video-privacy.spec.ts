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
  await expect(page.getByText(/AVI, MP4, MOV, or WebM/)).toBeVisible();
  await expect(page.getByText("Audio-free output:")).toBeVisible();
  await expect(
    page.getByText(
      /Every frame receives full-frame blur, whether or not a face is detected/,
    ),
  ).toBeVisible();
  await expect(
    page.getByText(/Face-detection coverage is a quality signal for review/),
  ).toBeVisible();
});
