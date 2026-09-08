import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const API = "http://127.0.0.1:18000";
const CANARY = "CANARY_";

test("real encrypted upload completes without leaking canary metadata", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Email address").fill(`demo-${Date.now()}@example.test`);
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.goto("/upload");
  await page.locator("#eeg-file").setInputFiles(resolve("test-results/real-e2e.zip"));
  await expect(page.getByText("Required baseline", { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("body")).not.toContainText(CANARY);
  await page.getByRole("button", { name: "Submit for analysis" }).click();
  await expect(page).toHaveURL(/\/sessions\/SES-/);

  const sessionId = page.url().split("/sessions/")[1];
  await expect.poll(async () => {
    const response = await page.request.get(`${API}/api/sessions/${sessionId}/status`);
    return (await response.json()).status as string;
  }, { timeout: 120_000, intervals: [500, 1000, 2000] }).toMatch(/completed|completed_with_errors|failed/);

  const sessionResponse = await page.request.get(`${API}/api/sessions/${sessionId}`);
  expect(sessionResponse.ok()).toBeTruthy();
  const sessionText = await sessionResponse.text();
  expect(sessionText).not.toContain(CANARY);
  const session = JSON.parse(sessionText) as { recordings: Array<{ record_id: string; status: string }> };
  expect(session.recordings).toHaveLength(1);
  expect(session.recordings[0]?.status).toBe("inferred");

  const recordId = session.recordings[0]!.record_id;
  for (const path of [
    `/api/recordings/${recordId}`,
    `/api/recordings/${recordId}/prediction`,
    `/api/recordings/${recordId}/explanation`,
  ]) {
    const response = await page.request.get(`${API}${path}`);
    expect(response.ok()).toBeTruthy();
    expect(await response.text()).not.toContain(CANARY);
  }
  expect((await page.request.get(`${API}/api/recordings/${recordId}/signal`)).status()).toBe(404);
  expect((await page.request.delete(`${API}/api/sessions/${sessionId}`, { headers: { Origin: "http://127.0.0.1:3002" } })).status()).toBe(204);
});
