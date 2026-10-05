import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { resolve } from "node:path";
import { test, expect } from "@playwright/test";

const API = process.env.MDS01_SECURITY_API_BASE_URL;
const SECURITY_PROJECT = process.env.MDS01_SECURITY_COMPOSE_PROJECT;

if (!API) throw new Error("MDS01_SECURITY_API_BASE_URL is required");
if (!/^mds01-security-[a-f0-9]{32}$/.test(SECURITY_PROJECT ?? "")) {
  throw new Error("A unique security Compose project is required");
}

test("real cookies isolate encrypted video review playback", async ({
  page,
  playwright,
}) => {
  const email = `video-${randomBytes(6).toString("hex")}@example.test`;
  const password = randomBytes(20).toString("hex");
  await page.goto("/login");
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
      SECURITY_PROJECT!,
      "--env-file",
      "/dev/null",
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

  const ownerJobResponse = await page.request.get(
    `${API}/api/video-detection/jobs/${id}`,
  );
  expect(ownerJobResponse.ok()).toBeTruthy();
  expect((await ownerJobResponse.json()).job.video_available).toBe(true);
  const predictions = await page.request.get(
    `${API}/api/video-detection/jobs/${id}/predictions`,
  );
  expect(predictions.ok()).toBeTruthy();
  expect((await predictions.json()).predictions).toHaveLength(2);
  const playback = await page.request.get(
    `${API}/api/video-detection/jobs/${id}/visualization`,
    { headers: { Range: "bytes=0-8" } },
  );
  expect(playback.status()).toBe(206);
  expect(playback.headers()["content-range"]).toMatch(/^bytes 0-8\//);
  expect(await playback.body()).toHaveLength(9);

  await page.goto(`/video-detection/${id}`);
  await expect(
    page.getByRole("heading", { name: "VSViG score and protected video" }),
  ).toBeVisible();
  await expect(page.locator("video")).toBeVisible();

  const laterRange = await page.request.get(
    `${API}/api/video-detection/jobs/${id}/visualization`,
    { headers: { Range: "bytes=9-17" } },
  );
  expect(laterRange.status()).toBe(206);
  expect(laterRange.headers()["content-range"]).toMatch(/^bytes 9-17\//);
  expect(await laterRange.body()).toHaveLength(9);

  const stranger = await playwright.request.newContext();
  try {
    expect(
      (await stranger.get(`${API}/api/video-detection/jobs/${id}`)).status(),
    ).toBe(401);
    expect(
      (
        await stranger.get(`${API}/api/video-detection/jobs/${id}/predictions`)
      ).status(),
    ).toBe(401);
    expect(
      (
        await stranger.get(
          `${API}/api/video-detection/jobs/${id}/visualization`,
        )
      ).status(),
    ).toBe(401);
    const registration = await stranger.post(`${API}/api/auth/register`, {
      data: {
        email: `other-${email}`,
        password: randomBytes(20).toString("hex"),
      },
      headers: { Origin: "http://127.0.0.1:3002" },
    });
    expect(registration.status()).toBe(201);
    expect(
      (await stranger.get(`${API}/api/video-detection/jobs/${id}`)).status(),
    ).toBe(404);
    expect(
      (
        await stranger.get(`${API}/api/video-detection/jobs/${id}/predictions`)
      ).status(),
    ).toBe(404);
    expect(
      (
        await stranger.get(
          `${API}/api/video-detection/jobs/${id}/visualization`,
        )
      ).status(),
    ).toBe(404);
  } finally {
    await stranger.dispose();
  }

  const upload = await page.request.post(`${API}/api/video-detection/jobs`, {
    data: Buffer.from("synthetic test video bytes"),
    headers: {
      Origin: "http://127.0.0.1:3002",
      "Content-Type": "application/octet-stream",
      "X-Video-Format": "mp4",
    },
  });
  expect(upload.status()).toBe(503);
  expect(await upload.text()).toContain("Mount the official model assets");
});
