import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { randomBytes } from "node:crypto";
import { test, expect } from "@playwright/test";

const API = process.env.MDS01_SECURITY_API_BASE_URL;

if (!API) throw new Error("MDS01_SECURITY_API_BASE_URL is required");

test("real cookies isolate synthetic review visualization and enforce range playback", async ({
  page,
  playwright,
}) => {
  const email = `video-${randomBytes(6).toString("hex")}@example.test`;
  const password = randomBytes(20).toString("hex");
  await page.goto("/login");
  // Register using the real API; the browser context receives its HttpOnly cookie.
  const response = await page.request.post(`${API}/api/auth/register`, {
    data: { email, password },
    headers: { Origin: "http://127.0.0.1:3002" },
  });
  expect(response.status()).toBe(201);
  const id = execFileSync(
    "docker",
    [
      "compose",
      "-p",
      process.env.MDS01_SECURITY_COMPOSE_PROJECT ?? "mds01-security",
      "-f",
      "docker-compose.security.yml",
      "exec",
      "-T",
      "backend",
      "python",
      "-m",
      "backend.tests.seed_video_detection",
      email,
    ],
    { cwd: resolve(__dirname, "../../.."), encoding: "utf8" },
  ).trim();
  await page.goto(`/video-detection/${id}`);
  await expect(
    page.getByRole("heading", { name: "Potential seizure activity detected" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page
        .locator("video")
        .evaluate((element: HTMLVideoElement) => element.readyState),
    )
    .toBeGreaterThanOrEqual(1);
  await page.getByRole("button", { name: /Event 1/ }).click();
  await expect
    .poll(() =>
      page
        .locator("video")
        .evaluate((element: HTMLVideoElement) => element.currentTime),
    )
    .toBeGreaterThanOrEqual(1);
  const video = await page.request.get(
    `${API}/api/video-detection/jobs/${id}/visualization`,
    { headers: { Range: "bytes=0-31" } },
  );
  expect(video.status()).toBe(206);
  expect(video.headers()["cache-control"]).toContain("no-store");
  const stranger = await playwright.request.newContext();
  try {
    expect(
      (
        await stranger.get(
          `${API}/api/video-detection/jobs/${id}/visualization`,
        )
      ).status(),
    ).toBe(401);
    expect(
      (
        await stranger.post(`${API}/api/auth/register`, {
          data: {
            email: `other-${email}`,
            password: randomBytes(20).toString("hex"),
          },
          headers: { Origin: "http://127.0.0.1:3002" },
        })
      ).status(),
    ).toBe(201);
    for (const suffix of ["", "/video", "/predictions", "/visualization"])
      expect(
        (
          await stranger.get(`${API}/api/video-detection/jobs/${id}${suffix}`)
        ).status(),
      ).toBe(404);
    const upload = await page.request.post(`${API}/api/video-detection/jobs`, {
      multipart: {
        video: {
          name: "synthetic.mp4",
          mimeType: "video/mp4",
          buffer: Buffer.from("synthetic test"),
        },
      },
      headers: { Origin: "http://127.0.0.1:3002" },
    });
    expect(upload.status()).toBe(503);
    expect(await upload.text()).toContain("Mount the official model assets");
  } finally {
    await stranger.dispose();
  }
});
