import { expect, test } from "@playwright/test";

const CASE_ID = "CASE-SYNTHETIC";
const REVIEWED_AT = "2026-09-27T00:00:00Z";

function requireBackendProjection() {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify owner-scoped case projections.",
  );
}

test("patient history uses the accessible orb while cases are loading", async ({
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

  await page.goto("/cases");
  try {
    await requestStarted;
    const loadingStatus = page
      .getByRole("status")
      .filter({ hasText: "Loading patient history…" });
    await expect(loadingStatus).toBeVisible();
    await expect(loadingStatus.locator("canvas")).toBeVisible();
    releaseResponse();
    await expect(
      page.getByRole("heading", { name: "No patient reviews yet" }),
    ).toBeVisible();
  } finally {
    releaseResponse();
  }
});

test("patient history shows a retry state instead of empty state when loading fails", async ({
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

  await page.goto("/cases");
  await expect.poll(() => attempts).toBeGreaterThan(0);

  await expect(
    page
      .locator('[role="alert"]')
      .filter({ hasText: "Synthetic temporary failure" }),
  ).toBeVisible();
  const failedAttemptCount = attempts;
  await expect(
    page.getByRole("heading", { name: "No patient reviews yet" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /Create first patient review/ }),
  ).toHaveCount(0);
  shouldFail = false;
  await page.getByRole("button", { name: "Retry loading patients" }).click();
  await expect(
    page.getByRole("heading", { name: "No patient reviews yet" }),
  ).toBeVisible();
  expect(attempts).toBeGreaterThan(failedAttemptCount);
});

test("case history shows the patient name without rendering the opaque case ID", async ({
  page,
}) => {
  requireBackendProjection();
  await page.route("**/api/cases", (route) =>
    route.fulfill({
      json: [
        {
          case_id: CASE_ID,
          patient_name: "Synthetic Case Patient",
          report_summary: "Synthetic report preview only.",
          modalities: ["eeg", "video"],
          analysis_count: 3,
          latest_created_at: REVIEWED_AT,
          status: "needs_review",
          flagged_interval_count: 0,
          explanation_ready: true,
        },
      ],
    }),
  );

  await page.goto("/cases");

  await expect(
    page.getByRole("heading", { name: "Synthetic Case Patient" }),
  ).toBeVisible();
  await expect(page.getByText(CASE_ID, { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /Synthetic Case Patient/ }),
  ).toHaveAttribute("href", `/cases/${CASE_ID}`);
  await expect(page.getByText("Synthetic report preview only.")).toBeVisible();
});

test("case detail groups report sections and keeps contact identifiers out of the summary", async ({
  page,
}) => {
  requireBackendProjection();
  await page.route(`**/api/cases/${CASE_ID}/patient-profile`, (route) =>
    route.fulfill({
      json: {
        profile: {
          name: "",
          hospital_id: "",
          age: "",
          findings: "",
          details: [
            { label: "Patient Name", value: "Synthetic Case Patient" },
            { label: "Test Type", value: "Routine EEG" },
            {
              label: "Technical summary",
              value: "Synthetic technical summary.",
            },
            { label: "Event description", value: "Synthetic observed event." },
            { label: "Conclusion", value: "Synthetic conclusion." },
            { label: "Address", value: "42 Synthetic Street" },
            { label: "Contact phone", value: "555-0100" },
            { label: "Medical Record Number", value: "SYNTHETIC-MRN-1" },
            { label: "Date & Time", value: "13/1/2026 6:46:30 AM" },
            { label: "Field label 20", value: "Synthetic safe extra detail" },
            {
              label: "Field label 21",
              value: "Unit 42, Jalan Synthetic; 012-3456789",
            },
          ],
          reviewed: true,
          reviewed_at: REVIEWED_AT,
        },
      },
    }),
  );
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({
      json: {
        case_id: CASE_ID,
        patient_name: "Synthetic Case Patient",
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
  const sourcePdf = Buffer.from(
    "%PDF-1.7\n% synthetic fixture\n%%EOF",
    "ascii",
  );
  let uploadedPdfContentType = "";
  await page.route(`**/api/cases/${CASE_ID}/report`, async (route) => {
    if (route.request().method() === "PUT") {
      uploadedPdfContentType = route.request().headers()["content-type"] ?? "";
      await route.fulfill({ json: { available: true } });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/pdf",
      body: sourcePdf,
    });
  });

  await page.goto(`/cases/${CASE_ID}`);

  await expect(
    page.getByRole("heading", { name: "Synthetic Case Patient" }),
  ).toBeVisible();
  await expect(page.getByText(CASE_ID, { exact: true })).toHaveCount(0);
  await expect(
    page.getByText(/No VSViG player is attached to this case yet/),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Technical summary" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Events" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Conclusion" })).toBeVisible();
  await expect(page.getByText("Synthetic technical summary.")).toBeVisible();
  await expect(page.getByText("Synthetic observed event.")).toBeVisible();
  await expect(page.getByText("Synthetic conclusion.").first()).toBeVisible();
  await expect(page.getByText("42 Synthetic Street")).toHaveCount(0);
  await expect(page.getByText("555-0100")).toHaveCount(0);
  await expect(page.getByText("SYNTHETIC-MRN-1")).toHaveCount(0);
  await expect(page.getByText("Synthetic safe extra detail")).not.toBeVisible();
  await expect(
    page.getByText("Unit 42, Jalan Synthetic; 012-3456789"),
  ).toHaveCount(0);
  await page.getByText(/Other report details/).click();
  await expect(page.getByText("Synthetic safe extra detail")).toBeVisible();
  await expect(page.getByText("13/1/2026 6:46:30 AM")).toBeVisible();

  await expect(
    page.getByRole("button", { name: /View original report PDF/ }),
  ).toBeVisible();

  await page.getByLabel("Attach source report PDF").setInputFiles({
    name: "synthetic.pdf",
    mimeType: "application/pdf",
    buffer: sourcePdf,
  });
  await expect(
    page.getByText("PDF report attached and stored encrypted for this case."),
  ).toBeVisible();
  expect(uploadedPdfContentType).toBe("application/pdf");

  await page.getByRole("button", { name: "View original report PDF" }).click();
  await expect(page.getByTitle("Original source report PDF")).toBeVisible();
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
  await page.getByRole("link", { name: "Back to Patient History" }).click();
  await expect(page).toHaveURL(/\/cases$/);
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

test("navigation highlights only the active screen and labels cases as Patient History", async ({
  page,
}) => {
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
  await expect(
    primaryNavigation.getByRole("link", { name: "New patient review" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    primaryNavigation.getByRole("link", { name: "Workspace" }),
  ).not.toHaveAttribute("aria-current", "page");

  await page.goto("/dashboard");
  primaryNavigation = await openPrimaryNavigation();
  await expect(
    primaryNavigation.getByRole("link", { name: "Workspace" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    primaryNavigation.getByRole("link", { name: "New patient review" }),
  ).not.toHaveAttribute("aria-current", "page");

  await page.goto("/cases");
  primaryNavigation = await openPrimaryNavigation();
  await expect(
    primaryNavigation.getByRole("link", { name: "Patient History" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    primaryNavigation.getByRole("link", { name: "Cases" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "All patient reviews" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Patients", exact: true }),
  ).toHaveCount(0);
});

test("workspace previews recent cases without rendering patient details", async ({
  page,
}) => {
  requireBackendProjection();
  await page.route("**/api/sessions**", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/cases", (route) =>
    route.fulfill({
      json: [
        {
          case_id: "CASE-RECENT-1",
          patient_name: "Synthetic Private Name",
          report_summary: "Synthetic private report summary.",
          modalities: ["eeg", "video"],
          analysis_count: 3,
          latest_created_at: "2026-09-27T00:00:00Z",
          status: "needs_review",
          flagged_interval_count: 2,
          explanation_ready: true,
        },
        {
          case_id: "CASE-RECENT-2",
          patient_name: "Another Synthetic Name",
          report_summary: "Another private report summary.",
          modalities: ["eeg"],
          analysis_count: 1,
          latest_created_at: "2026-09-26T00:00:00Z",
          status: "processing",
          flagged_interval_count: 0,
          explanation_ready: false,
        },
      ],
    }),
  );

  await page.goto("/dashboard");

  await expect(
    page.getByRole("heading", { name: "Recent patient history" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Review 01/ })).toHaveAttribute(
    "href",
    "/cases/CASE-RECENT-1",
  );
  await expect(page.getByRole("link", { name: /Review 02/ })).toHaveAttribute(
    "href",
    "/cases/CASE-RECENT-2",
  );
  await expect(page.getByText("Synthetic Private Name")).toHaveCount(0);
  await expect(page.getByText("Another Synthetic Name")).toHaveCount(0);
  await expect(page.getByText("Synthetic private report summary.")).toHaveCount(
    0,
  );
  await expect(page.getByText("Another private report summary.")).toHaveCount(
    0,
  );
  await expect(page.getByText("CASE-RECENT-1", { exact: true })).toHaveCount(0);
  await expect(
    page
      .getByRole("region", { name: "Recent patient history" })
      .getByRole("link", { name: "Patient History" }),
  ).toHaveAttribute("href", "/cases");
  await page.screenshot({
    path: test.info().outputPath("workspace-recent-history.png"),
    fullPage: true,
  });
});
