import { expect, test } from "@playwright/test";

const CASE_ID = "CASE-SYNTHETIC";
const REVIEWED_AT = "2026-09-27T00:00:00Z";

function requireBackendProjection() {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify owner-scoped case projections.",
  );
}

test("workspace shows a loading state while patients load", async ({
  page,
}) => {
  requireBackendProjection();
  let releaseResponse = () => {};
  let markRequestStarted = () => {};
  const heldResponse = new Promise<void>((resolve) => {
    releaseResponse = resolve;
  });
  const requestStarted = new Promise<void>((resolve) => {
    markRequestStarted = resolve;
  });
  await page.route("**/api/cases", async (route) => {
    markRequestStarted();
    await heldResponse;
    await route.fulfill({ json: [] });
  });
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto("/dashboard");
  try {
    await requestStarted;
    const recent = page.getByRole("region", {
      name: "Recent patients / sessions",
    });
    const loadingStatus = recent
      .getByRole("status")
      .filter({ hasText: "Loading records…" });
    await expect(loadingStatus).toBeVisible();
    releaseResponse();
    await expect(recent.getByText(/No patient cases yet/)).toBeVisible();
  } finally {
    releaseResponse();
  }
});

test("workspace offers a retry instead of showing an empty patient list on failure", async ({
  page,
}) => {
  requireBackendProjection();
  let attempts = 0;
  let shouldFail = true;
  await page.route("**/api/cases**", (route) => {
    attempts += 1;
    return shouldFail
      ? route.fulfill({
          status: 503,
          json: { detail: "Synthetic temporary failure" },
        })
      : route.fulfill({ json: [] });
  });
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto("/dashboard");
  await expect.poll(() => attempts).toBeGreaterThan(0);

  await expect(
    page
      .locator('[role="alert"]')
      .filter({ hasText: "Dashboard records could not be loaded" }),
  ).toBeVisible();
  const failedAttemptCount = attempts;
  await expect(page.getByText(/No patient cases yet/)).toHaveCount(0);
  shouldFail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(/No patient cases yet/)).toBeVisible();
  expect(attempts).toBeGreaterThan(failedAttemptCount);
});

test("patient case workspace opens from its route", async ({ page }) => {
  requireBackendProjection();
  await page.route("**/api/cases", (route) => route.fulfill({ json: [] }));
  await page.goto("/cases");

  await expect(page).toHaveURL(/\/cases$/);
  await expect(
    page.getByRole("heading", { name: "Patient cases", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Patient History" })).toHaveCount(
    0,
  );
});

test("case detail shows extracted report sections without an approval step", async ({
  page,
}) => {
  requireBackendProjection();
  const extractedProfileFields = [
    { label: "Patient Name", value: "Synthetic Case Patient" },
    { label: "Test Type", value: "Routine EEG" },
    { label: "Technical summary", value: "Synthetic technical summary." },
    { label: "Interictal record", value: "Synthetic interictal finding." },
    { label: "Ictal record", value: "Synthetic ictal finding." },
    { label: "Event description", value: "Synthetic observed event." },
    { label: "Conclusion", value: "Synthetic conclusion." },
    { label: "Specialist names", value: "Synthetic specialist." },
    { label: "Address", value: "42 Synthetic Street" },
    { label: "Contact phone", value: "555-0100" },
    { label: "Medical Record Number", value: "SYNTHETIC-MRN-1" },
    { label: "Date & Time", value: "13/1/2026 6:46:30 AM" },
    { label: "Other report field", value: "Synthetic extra detail" },
  ];
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, (route) =>
    route.fulfill({
      json: {
        profile: {
          name: "Synthetic Case Patient",
          hospital_id: "",
          age: "",
          findings: "",
          details: extractedProfileFields,
          reviewed: false,
          verification_status: "auto_extracted",
          reviewed_at: null,
        },
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        patient_name: "Synthetic Case Patient",
        patient_name_verification_status: "auto_extracted",
        analyses: [
          {
            id: "SES-SYNTHETIC",
            modality: "eeg",
            status: "needs_review",
            created_at: REVIEWED_AT,
            review_ready: true,
          },
        ],
      },
    }),
  );
  await page.route(`**/api/video-privacy/jobs?case_id=${CASE_ID}`, (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto(`/cases/${CASE_ID}`);

  await expect(
    page.getByRole("heading", { name: "Synthetic Case Patient" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Patient and recording details" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Interictal EEG" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Ictal EEG", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Attacks" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "EEG findings" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Conclusion" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Report sign-off" }),
  ).toBeVisible();
  await expect(
    page.getByText("Synthetic extra detail", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("SYNTHETIC-MRN-1", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Mark details reviewed" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Attach source report|Replace report/ }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Not available in the structured report details."),
  ).toHaveCount(0);
});

test("combined printable report omits private patient-profile values", async ({
  page,
}) => {
  requireBackendProjection();
  const sessionId = "SES-PRINT-SYNTHETIC";
  const caseId = "CASE-PRINT-SYNTHETIC";
  await page.route(`**/api/sessions/${sessionId}`, (route) =>
    route.fulfill({
      json: {
        session_id: sessionId,
        case_id: caseId,
        privacy_method: "metadata-scrub",
        privacy_methods: ["metadata-scrub"],
        status: "completed",
        current_stage: null,
        created_at: REVIEWED_AT,
        completed_at: REVIEWED_AT,
        progress: {
          total_recordings: 0,
          finished_recordings: 0,
          completed_recordings: 0,
          failed_recordings: 0,
          percent: 100,
        },
        summary: { model_alert_recordings: 0 },
        recordings: [],
      },
    }),
  );
  await page.route(`**/api/cases/${caseId}/patient-profile`, (route) =>
    route.fulfill({
      json: {
        profile: {
          name: "Synthetic Private Patient",
          hospital_id: "H-42-SYNTHETIC",
          age: "",
          findings: "Synthetic safe report finding.",
          details: [
            { label: "Patient Name", value: "Synthetic Private Patient" },
            { label: "Address", value: "42 Synthetic Street" },
            { label: "Hospital ID", value: "H-42-SYNTHETIC" },
            { label: "Contact phone", value: "555-0100" },
            { label: "Diagnosis", value: "Synthetic opted-in diagnosis" },
          ],
          reviewed: true,
          reviewed_at: REVIEWED_AT,
        },
      },
    }),
  );
  await page.route(`**/api/video-privacy/jobs?case_id=${caseId}`, (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto(`/analysis?sessionId=${sessionId}`);
  await expect(
    page.getByRole("heading", { name: "Patient details", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Synthetic opted-in diagnosis")).toBeVisible();
  await expect(page.getByText("Synthetic Private Patient")).toHaveCount(0);
  await expect(page.getByText("42 Synthetic Street")).toHaveCount(0);
  await expect(page.getByText("H-42-SYNTHETIC")).toHaveCount(0);
  await expect(page.getByText("555-0100")).toHaveCount(0);
});

test("source report object URLs are revoked when the PDF is replaced or deleted", async ({
  page,
}) => {
  requireBackendProjection();
  await page.addInitScript(() => {
    const observed = window as Window & { __revokedPdfUrls?: string[] };
    observed.__revokedPdfUrls = [];
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.revokeObjectURL = (url) => {
      observed.__revokedPdfUrls?.push(url);
      revoke(url);
    };
  });
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        analyses: [
          {
            id: "SES-SYNTHETIC",
            modality: "eeg",
            status: "processing",
            created_at: REVIEWED_AT,
            review_ready: false,
          },
        ],
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, async (route) => {
    if (route.request().method() === "DELETE")
      return route.fulfill({ status: 204 });
    return route.fulfill({
      json: {
        profile: {
          name: "Synthetic Case Patient",
          hospital_id: "",
          age: "",
          findings: "",
          details: [{ label: "Patient Name", value: "Synthetic Case Patient" }],
          reviewed: true,
          reviewed_at: REVIEWED_AT,
        },
      },
    });
  });
  await page.route(`**/api/video-privacy/jobs?case_id=${CASE_ID}`, (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );
  await page.route(`**/api/cases/${CASE_ID}/report`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/pdf",
      body: "%PDF-1.7\\n% synthetic fixture\\n%%EOF",
    }),
  );

  await page.goto(`/cases/${CASE_ID}`);
  await page.getByRole("button", { name: "View original report PDF" }).click();
  await expect(page.getByTitle("Original source report PDF")).toBeVisible();
  await page.getByLabel("Attach source report PDF").setInputFiles({
    name: "replacement.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\\n% replacement\\n%%EOF", "ascii"),
  });
  await expect(
    page.getByText("PDF report attached and stored encrypted for this case."),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as Window & { __revokedPdfUrls?: string[] }).__revokedPdfUrls
            ?.length ?? 0,
      ),
    )
    .toBe(1);

  await page.getByRole("button", { name: "View original report PDF" }).click();
  await expect(page.getByTitle("Original source report PDF")).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept());
  await page
    .getByRole("button", { name: "Delete patient record and PDF" })
    .click();
  await expect(
    page.getByText("Patient report details are not available."),
  ).toBeVisible();
  await expect(page.getByTitle("Original source report PDF")).toHaveCount(0);
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as Window & { __revokedPdfUrls?: string[] }).__revokedPdfUrls
            ?.length ?? 0,
      ),
    )
    .toBe(2);
});

test("a source PDF response arriving after navigation does not create an object URL", async ({
  page,
}) => {
  requireBackendProjection();
  await page.addInitScript(() => {
    const observed = window as Window & { __createdPdfUrls?: string[] };
    observed.__createdPdfUrls = [];
    const create = URL.createObjectURL.bind(URL);
    URL.createObjectURL = (blob) => {
      const url = create(blob);
      observed.__createdPdfUrls?.push(url);
      return url;
    };
  });
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        analyses: [
          {
            id: "SES-SYNTHETIC",
            modality: "eeg",
            status: "processing",
            created_at: REVIEWED_AT,
            review_ready: false,
          },
        ],
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, (route) =>
    route.fulfill({
      json: {
        profile: {
          name: "Synthetic Case Patient",
          hospital_id: "",
          age: "",
          findings: "",
          details: [{ label: "Patient Name", value: "Synthetic Case Patient" }],
          reviewed: true,
          reviewed_at: REVIEWED_AT,
        },
      },
    }),
  );
  await page.route(`**/api/video-privacy/jobs?case_id=${CASE_ID}`, (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );
  let releasePdf = () => {};
  let markPdfStarted = () => {};
  let markPdfHandlerFinished = () => {};
  const heldPdf = new Promise<void>((resolve) => (releasePdf = resolve));
  const pdfStarted = new Promise<void>((resolve) => (markPdfStarted = resolve));
  const pdfHandlerFinished = new Promise<void>(
    (resolve) => (markPdfHandlerFinished = resolve),
  );
  await page.route(`**/api/cases/${CASE_ID}/report`, async (route) => {
    markPdfStarted();
    try {
      await heldPdf;
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "%PDF-1.7\\n% synthetic fixture\\n%%EOF",
      });
    } catch {
      // Navigation may cancel the in-flight request.
    } finally {
      markPdfHandlerFinished();
    }
  });

  await page.goto(`/cases/${CASE_ID}`);
  await page.getByRole("button", { name: "View original report PDF" }).click();
  await pdfStarted;
  await page.route("**/api/cases", (route) => route.fulfill({ json: [] }));
  await page.getByRole("link", { name: "Back to Workspace" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  releasePdf();
  await pdfHandlerFinished;

  expect(
    await page.evaluate(
      () =>
        (window as Window & { __createdPdfUrls?: string[] }).__createdPdfUrls
          ?.length ?? 0,
    ),
  ).toBe(0);
});

test("failed patient-profile deletion keeps the profile visible and announces an error", async ({
  page,
}) => {
  requireBackendProjection();
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        analyses: [
          {
            id: "SES-SYNTHETIC",
            modality: "eeg",
            status: "processing",
            created_at: REVIEWED_AT,
            review_ready: false,
          },
        ],
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, (route) => {
    if (route.request().method() === "DELETE")
      return route.fulfill({
        status: 500,
        json: { detail: "Synthetic failure." },
      });
    return route.fulfill({
      json: {
        profile: {
          name: "Synthetic Case Patient",
          hospital_id: "",
          age: "",
          findings: "",
          details: [{ label: "Patient Name", value: "Synthetic Case Patient" }],
          reviewed: true,
          reviewed_at: REVIEWED_AT,
        },
      },
    });
  });
  await page.route(`**/api/video-privacy/jobs?case_id=${CASE_ID}`, (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto(`/cases/${CASE_ID}`);
  await expect(
    page.getByRole("heading", { name: "Synthetic Case Patient" }),
  ).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept());
  await page
    .getByRole("button", { name: "Delete patient record and PDF" })
    .click();

  await expect(
    page.getByRole("alert").filter({
      hasText: "The reviewed patient profile could not be deleted.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Synthetic Case Patient" }),
  ).toBeVisible();
});

test("case history warns when video clips were rejected before VSViG", async ({
  page,
}) => {
  requireBackendProjection();
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        analyses: [
          {
            id: "SES-SYNTHETIC",
            modality: "eeg",
            status: "processing",
            created_at: REVIEWED_AT,
            review_ready: false,
          },
        ],
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, (route) =>
    route.fulfill({ json: { profile: null } }),
  );
  await page.route(`**/api/video-privacy/jobs?case_id=${CASE_ID}`, (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto(
    `/cases/${CASE_ID}?video_rejected_count=2&video_unconfirmed_count=0`,
  );

  await expect(
    page.getByRole("alert").filter({
      hasText: "2 video clips were not accepted by VSViG",
    }),
  ).toBeVisible();
  await expect(
    page.getByText("No model result is available for those clips."),
  ).toBeVisible();
  await expect(
    page.getByText("VSViG video analysis", { exact: true }),
  ).toHaveCount(0);
});

test("ready EEG and video reviews keep separate links until a sync match is available", async ({
  page,
}) => {
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        analyses: [
          {
            id: "SES-SYNTHETIC",
            modality: "eeg",
            status: "complete",
            created_at: REVIEWED_AT,
            review_ready: true,
          },
          {
            id: "VID-SYNTHETIC",
            modality: "video",
            status: "complete",
            created_at: REVIEWED_AT,
            review_ready: true,
          },
        ],
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, (route) =>
    route.fulfill({ json: { profile: null } }),
  );

  await page.goto(`/cases/${CASE_ID}`);

  await expect(
    page.getByRole("link", { name: "Open EEG/video sync review" }),
  ).toHaveAttribute("href", "/analysis?videoJobId=VID-SYNTHETIC");
});

test("navigation exposes workspace, EEG, and video tools", async ({ page }) => {
  async function openPrimaryNavigation() {
    if (test.info().project.name === "mobile") {
      await page.getByRole("button", { name: "Open navigation menu" }).click();
    }
    return page.locator('nav[aria-label="Primary navigation"]:visible').first();
  }

  await page.goto("/upload");
  let primaryNavigation = await openPrimaryNavigation();
  await expect(primaryNavigation.locator('[aria-current="page"]')).toHaveCount(
    1,
  );
  await expect(primaryNavigation.getByRole("link")).toHaveCount(4);
  await expect(
    primaryNavigation.getByRole("link", { name: "New patient review" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    primaryNavigation.getByRole("link", { name: "Patient cases" }),
  ).not.toHaveAttribute("aria-current", "page");

  await page.goto("/dashboard");
  primaryNavigation = await openPrimaryNavigation();
  await expect(
    primaryNavigation.getByRole("link", { name: "Patient cases" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    primaryNavigation.getByRole("link", { name: "New patient review" }),
  ).not.toHaveAttribute("aria-current", "page");
  await expect(primaryNavigation.getByRole("link")).toHaveCount(4);
  await expect(
    primaryNavigation.getByRole("link", { name: "EEG workspace" }),
  ).toBeVisible();
  await expect(
    primaryNavigation.getByRole("link", { name: "Video workspace" }),
  ).toBeVisible();
  await expect(
    primaryNavigation.getByRole("link", { name: "EEG upload" }),
  ).toHaveCount(0);
  await expect(
    primaryNavigation.getByRole("link", { name: "Video privacy" }),
  ).toHaveCount(0);
  await expect(
    primaryNavigation.getByRole("link", { name: "Patient History" }),
  ).toHaveCount(0);

  await page.goto("/upload/eeg");
  primaryNavigation = await openPrimaryNavigation();
  await expect(
    primaryNavigation.getByRole("link", { name: "EEG workspace" }),
  ).toHaveAttribute("aria-current", "page");
  const eegWorkspace = page.getByRole("navigation", { name: "EEG workspace" });
  await expect(
    eegWorkspace.getByRole("link", { name: "New EEG analysis" }),
  ).toHaveAttribute("aria-current", "page");
  await eegWorkspace.getByRole("link", { name: "EEG reviews" }).click();
  await expect(page).toHaveURL(/\/upload\/eeg\?view=reviews$/);
  await expect(
    page.getByRole("heading", { name: "EEG reviews" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "EEG workspace" })
      .getByRole("link", { name: "EEG reviews" }),
  ).toHaveAttribute("aria-current", "page");
  await page
    .getByRole("navigation", { name: "EEG workspace" })
    .getByRole("link", { name: "New EEG analysis" })
    .click();
  await expect(page).toHaveURL(/\/upload\/eeg$/);
});

test("dashboard shows privacy-safe patient rows and workspace links", async ({
  page,
}) => {
  requireBackendProjection();
  let sessionRequests = 0;
  await page.route("**/api/sessions**", (route) => {
    sessionRequests += 1;
    return route.fulfill({ json: [] });
  });
  await page.route("**/api/cases", (route) =>
    route.fulfill({
      json: [
        {
          case_id: "CASE-RECENT-1",
          patient_name: null,
          patient_name_verification_status: null,
          report_summary: null,
          modalities: ["eeg", "video"],
          analysis_count: 3,
          privacy_preview_count: 1,
          latest_created_at: "2026-09-27T00:00:00Z",
          status: "needs_review",
          flagged_interval_count: 2,
          explanation_ready: true,
        },
        {
          case_id: "CASE-RECENT-2",
          patient_name: "Another Synthetic Name",
          patient_name_verification_status: "reviewed",
          report_summary: "Another private report summary.",
          modalities: ["eeg"],
          analysis_count: 1,
          privacy_preview_count: 0,
          latest_created_at: "2026-09-26T00:00:00Z",
          status: "processing",
          flagged_interval_count: 0,
          explanation_ready: false,
        },
      ],
    }),
  );
  await page.route("**/api/video-detection/jobs", (route) =>
    route.fulfill({ json: { jobs: [] } }),
  );

  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  const workspaces = page.getByRole("region", {
    name: "Analysis workspaces",
  });
  await expect(workspaces.getByRole("link")).toHaveCount(3);
  await expect(workspaces.getByRole("link", { name: /VEEG/ })).toHaveAttribute(
    "href",
    "/cases",
  );
  const recent = page.getByRole("region", {
    name: "Recent patients / sessions",
  });
  await expect(recent.getByRole("row")).toHaveCount(3);
  await expect(recent.getByText("PT-RECENT-1")).toBeVisible();
  await expect(recent.getByText("PT-RECENT-2")).toBeVisible();
  await expect(recent.getByText("Another Synthetic Name")).toHaveCount(0);
  await expect(recent.getByText(/private report summary/i)).toHaveCount(0);
  await expect(recent.getByText("EEG · Video")).toBeVisible();
  await expect(recent.getByText("Issues")).toBeVisible();
  const totals = page.locator(
    'dl[aria-label="Patient processing totals"] > div',
  );
  await expect(totals.nth(0)).toContainText("2");
  expect(sessionRequests).toBe(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.locator(".animate-enter-up").evaluate(async (element) => {
    await Promise.all(
      element.getAnimations().map((animation) => animation.finished),
    );
  });
  await page.screenshot({
    path: test.info().outputPath("workspace-patients.png"),
    fullPage: true,
  });
});

test("deleting a patient case requires confirmation and removes its queue row", async ({
  page,
}) => {
  requireBackendProjection();
  let deletionCount = 0;
  await page.route("**/api/cases", (route) =>
    route.fulfill({
      json: [
        {
          case_id: "CASE-DELETE01",
          patient_name: "Synthetic Delete Patient",
          patient_name_verification_status: "reviewed",
          modalities: ["eeg", "video"],
          analysis_count: 2,
          privacy_preview_count: 1,
          latest_created_at: "2026-09-27T00:00:00Z",
          status: "complete",
          flagged_interval_count: 0,
          explanation_ready: true,
        },
      ],
    }),
  );
  await page.route("**/api/cases/CASE-DELETE01", async (route) => {
    if (route.request().method() === "DELETE") {
      deletionCount += 1;
      return route.fulfill({ status: 204, body: "" });
    }
    return route.fulfill({ status: 200, json: {} });
  });

  await page.goto("/cases");
  const patients = page.getByRole("region", { name: "All patient cases" });
  const deleteButton = page.getByRole("button", {
    name: "Delete case for Synthetic Delete Patient",
  });
  await deleteButton.click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toContainText("all linked EEG sessions and results");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect.poll(() => deletionCount).toBe(0);

  await deleteButton.click();
  await dialog.getByRole("button", { name: "Delete case" }).click();
  await expect.poll(() => deletionCount).toBe(1);
  await expect(patients.getByText("No patient cases yet")).toBeVisible();
});

test("a rejected active-case deletion keeps the case visible and explains why", async ({
  page,
}) => {
  requireBackendProjection();
  await page.route("**/api/cases", (route) =>
    route.fulfill({
      json: [
        {
          case_id: "CASE-BUSY001",
          patient_name: "Synthetic Busy Patient",
          patient_name_verification_status: "reviewed",
          modalities: ["eeg"],
          analysis_count: 1,
          privacy_preview_count: 0,
          latest_created_at: "2026-09-27T00:00:00Z",
          status: "processing",
          flagged_interval_count: 0,
          explanation_ready: false,
        },
      ],
    }),
  );
  await page.route("**/api/cases/CASE-BUSY001", (route) =>
    route.fulfill({
      status: 409,
      json: {
        detail:
          "This case has processing work. Wait until it finishes before deleting the case.",
      },
    }),
  );

  await page.goto("/cases");
  await page
    .getByRole("button", { name: "Delete case for Synthetic Busy Patient" })
    .click();
  const dialog = page.getByRole("alertdialog");
  await dialog.getByRole("button", { name: "Delete case" }).click();
  await expect(dialog.getByRole("alert")).toContainText("processing work");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(
    page.getByRole("link", { name: /Synthetic Busy Patient/ }),
  ).toBeVisible();
});
