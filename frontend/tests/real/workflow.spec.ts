import { randomBytes } from "node:crypto";
import { test, expect } from "@playwright/test";

const API = process.env.MDS01_SECURITY_API_BASE_URL;
const PATIENT_FOLDER = process.env.MDS01_SECURITY_PATIENT_FOLDER;
const SYNTHETIC_DETAIL = "SYNTHETIC_VEEG_STUDY";

if (!API) throw new Error("MDS01_SECURITY_API_BASE_URL is required");

test("synthetic VEEG upload is analyzed without exposing owner-only report details", async ({
  page,
  playwright,
}) => {
  if (!PATIENT_FOLDER) {
    throw new Error("MDS01_SECURITY_PATIENT_FOLDER is required");
  }
  await page.goto("/login");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page
    .getByLabel("Email address")
    .fill(`demo-${Date.now()}@example.test`);
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.goto("/upload");
  await page.locator('input[type="file"]').setInputFiles(PATIENT_FOLDER);
  await expect(
    page.getByRole("heading", { name: "Patient details", exact: true }),
  ).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(SYNTHETIC_DETAIL)).toBeVisible();
  const finalizedResponse = page.waitForResponse((response) => {
    const pathname = new URL(response.url()).pathname;
    return (
      response.request().method() === "POST" &&
      /\/api\/uploads\/drafts\/[^/]+\/finalize$/.test(pathname)
    );
  });
  await page.getByRole("button", { name: "Start processing" }).click();
  const finalized = await finalizedResponse;
  expect(finalized.ok()).toBeTruthy();
  const { session_id: sessionId, case_id: caseId } =
    (await finalized.json()) as {
      session_id: string;
      case_id: string;
    };
  expect(sessionId).toMatch(/^SES-/);
  expect(caseId).toMatch(/^CASE-/);
  await expect(page).toHaveURL(/\/upload$/);
  await expect(
    page.getByRole("region", { name: "Patient processing progress" }),
  ).toBeVisible();

  await expect
    .poll(
      async () => {
        const response = await page.request.get(
          `${API}/api/sessions/${sessionId}/status`,
        );
        return (await response.json()).status as string;
      },
      { timeout: 120_000, intervals: [500, 1000, 2000] },
    )
    .toMatch(/completed|completed_with_errors|failed/);

  const sessionResponse = await page.request.get(
    `${API}/api/sessions/${sessionId}`,
  );
  expect(sessionResponse.ok()).toBeTruthy();
  const sessionText = await sessionResponse.text();
  expect(sessionText).not.toContain(SYNTHETIC_DETAIL);
  const session = JSON.parse(sessionText) as {
    recordings: Array<{ record_id: string; status: string }>;
  };
  expect(session.recordings).toHaveLength(1);
  expect(session.recordings[0]?.status).toBe("inferred");

  const profileResponse = await page.request.get(
    `${API}/api/cases/${caseId}/patient-profile`,
  );
  expect(profileResponse.ok()).toBeTruthy();
  expect(await profileResponse.text()).toContain(SYNTHETIC_DETAIL);

  for (const path of ["/api/cases", `/api/cases/${caseId}`]) {
    const response = await page.request.get(`${API}${path}`);
    expect(response.ok()).toBeTruthy();
    expect(await response.text()).not.toContain(SYNTHETIC_DETAIL);
  }

  const recordId = session.recordings[0]!.record_id;
  for (const path of [
    `/api/recordings/${recordId}`,
    `/api/recordings/${recordId}/prediction`,
    `/api/recordings/${recordId}/explanation`,
  ]) {
    const response = await page.request.get(`${API}${path}`);
    expect(response.ok()).toBeTruthy();
    expect(await response.text()).not.toContain(SYNTHETIC_DETAIL);
  }
  expect(
    (
      await page.request.get(`${API}/api/recordings/${recordId}/signal`)
    ).status(),
  ).toBe(404);

  const stranger = await playwright.request.newContext();
  try {
    expect(
      (
        await stranger.post(`${API}/api/auth/register`, {
          data: {
            email: `other-${Date.now()}@example.test`,
            password: randomBytes(20).toString("hex"),
          },
          headers: { Origin: "http://127.0.0.1:3002" },
        })
      ).status(),
    ).toBe(201);
    expect(
      (
        await stranger.get(`${API}/api/cases/${caseId}/patient-profile`)
      ).status(),
    ).toBe(404);
    expect((await stranger.get(`${API}/api/cases/${caseId}`)).status()).toBe(
      404,
    );
    const strangerCases = await stranger.get(`${API}/api/cases`);
    expect(strangerCases.ok()).toBeTruthy();
    expect(await strangerCases.text()).not.toContain(caseId);
  } finally {
    await stranger.dispose();
  }

  expect(
    (
      await page.request.delete(`${API}/api/sessions/${sessionId}`, {
        headers: { Origin: "http://127.0.0.1:3002" },
      })
    ).status(),
  ).toBe(204);
});
