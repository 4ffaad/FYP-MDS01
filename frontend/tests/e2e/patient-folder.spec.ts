import { expect, test } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { unzipSync } from "fflate";
import { buildEegArchive, classifyPatientFolder } from "@/lib/patient-folder";
import { recordingFromBackend } from "@/lib/api";
import { profileLoadForCase } from "@/lib/case-profile-state";
import { prepareVideoUploadFile } from "@/lib/safe-upload";
import { videoJobFailureMessage } from "@/lib/video-detection";
import { extractPatientReportDraft } from "@/lib/report-extraction";

function folderFile(path: string, content = "synthetic"): File {
  const name = path.split("/").pop() ?? path;
  const file = new File([content], name);
  Object.defineProperty(file, "webkitRelativePath", { value: path });
  return file;
}

test("recording display names use sequence numbers, never backend filenames", () => {
  const recording = recordingFromBackend({
    record_id: "REC-SYNTHETIC",
    sequence_index: 7,
    status: "inferred",
    source_filename: "Synthetic-Patient-MRN-42.edf",
    duration_seconds: 12,
    sampling_rate: 256,
    channel_count: 18,
  });

  expect(recording.displayName).toBe("Recording 07");
  expect(recording.displayName).not.toContain("Synthetic-Patient-MRN-42");
});

test("explains why the video pose gate prevented VSViG from running", () => {
  expect(
    videoJobFailureMessage(
      "failed",
      "Too many patient landmarks were missing or obscured for this model.",
    ),
  ).toContain("the 15 body landmarks VSViG needs");
  expect(
    videoJobFailureMessage(
      "failed",
      "A single patient could not be identified throughout this clip.",
    ),
  ).toContain("track exactly one person");
});

test("classifies one explicitly selected folder without filename-based cross-modal pairing", () => {
  const result = classifyPatientFolder([
    folderFile("one-case/session.e"),
    folderFile("one-case/final-report.doc"),
    folderFile("one-case/clip-01.avi"),
    folderFile("one-case/notes.txt"),
  ]);

  expect(result.errors).toEqual([]);
  expect(result.eeg?.format).toBe("nicolet-e");
  expect(result.report?.name).toBe("final-report.doc");
  expect(result.videos).toHaveLength(1);
  expect(result.ignoredCount).toBe(1);
});

test("EEG-only classification permits a missing report and ignores videos", () => {
  const result = classifyPatientFolder(
    [
      folderFile("one-case/session.e"),
      folderFile("one-case/clip-01.avi"),
      folderFile("one-case/notes.txt"),
    ],
    { requireReport: false, includeVideos: false },
  );

  expect(result.errors).toEqual([]);
  expect(result.eegCandidates).toHaveLength(1);
  expect(result.report).toBeNull();
  expect(result.videos).toEqual([]);
  expect(result.ignoredCount).toBe(1);
});

test("rejects EEG and video files from a sibling patient folder", () => {
  const result = classifyPatientFolder([
    folderFile("patient-set/patient-a/report.doc"),
    folderFile("patient-set/patient-a/nested/recording.e"),
    folderFile("patient-set/patient-b/nested/recording.e"),
    folderFile("patient-set/patient-b/video/clip.avi"),
  ]);

  expect(result.errors).toContain(
    "Supported files were found in more than one patient folder. Select one patient folder at a time.",
  );
});

test("rejects sibling patient files when the selected folder has deeper nesting", () => {
  const result = classifyPatientFolder([
    folderFile("study/site/cohort/patient-a/report.doc"),
    folderFile("study/site/cohort/patient-a/eeg/recording.e"),
    folderFile("study/site/cohort/patient-b/eeg/recording.e"),
    folderFile("study/site/cohort/patient-b/video/clip.avi"),
  ]);

  expect(result.errors).toContain(
    "Supported files were found in more than one patient folder. Select one patient folder at a time.",
  );
});

test("classifies supported recordings nested below one patient folder", () => {
  const result = classifyPatientFolder([
    folderFile("patient-set/patient-a/report.doc"),
    folderFile("patient-set/patient-a/eeg/recording.e"),
    folderFile("patient-set/patient-a/eeg/second.edf"),
    folderFile("patient-set/patient-a/video/clip.avi"),
  ]);

  expect(result.errors).toEqual([]);
  expect(result.eegCandidates).toHaveLength(2);
  expect(result.videos).toHaveLength(1);
});

test("case profile state is hidden when its case does not match the route", () => {
  const caseA = {
    caseId: "CASE-A",
    profile: {
      name: "Synthetic Patient A",
      hospitalId: "",
      age: "",
      findings: "",
      details: [{ label: "Patient name", value: "Synthetic Patient A" }],
      reviewed: true as const,
      verificationStatus: "reviewed" as const,
      reviewedAt: "2026-09-26T00:00:00Z",
    },
    error: null,
  };
  const caseBError = {
    caseId: "CASE-B",
    profile: null,
    error: "The reviewed patient profile is unavailable.",
  };

  expect(profileLoadForCase("CASE-B", caseA)).toBeNull();
  expect(profileLoadForCase("CASE-B", caseBError)).toEqual(caseBError);
});

test("pairs Nicolet data and head only by exact directory and base name", () => {
  const result = classifyPatientFolder([
    folderFile("case/recording.data"),
    folderFile("case/recording.head"),
    folderFile("case/report.docx"),
  ]);

  expect(result.errors).toEqual([]);
  expect(result.eeg?.format).toBe("nicolet-data");
  expect(result.eeg?.files.map((entry) => entry.archiveName)).toEqual([
    "recording.data",
    "recording.head",
  ]);
});

test("video uploads replace source filenames with neutral names", async () => {
  const source = new File([new Uint8Array([1, 2, 3])], "Patient-H42_exam.AVI", {
    type: "video/x-msvideo",
    lastModified: 123,
  });

  const upload = prepareVideoUploadFile(source);

  expect(upload.name).toBe("video-source.avi");
  expect(upload.lastModified).toBe(0);
  expect(upload.type).toBe(source.type);
  expect(Array.from(new Uint8Array(await upload.arrayBuffer()))).toEqual([
    1, 2, 3,
  ]);
});

test("rejects ambiguous sources and does not pair sidecars across folders", () => {
  const result = classifyPatientFolder([
    folderFile("case-a/a.data"),
    folderFile("case-b/a.head"),
    folderFile("case/e.e"),
    folderFile("case/f.edf"),
    folderFile("case/a.doc"),
    folderFile("case/b.docx"),
  ]);

  expect(result.eeg).toBeNull();
  expect(result.report).toBeNull();
  expect(result.eegCandidates).toHaveLength(2);
  expect(result.errors).toContain(
    "Select exactly one supported report (.doc or .docx) in the patient folder.",
  );
  expect(result.errors).toContain(
    "Each Nicolet .data file needs exactly one same-directory, same-base-name .head sidecar.",
  );
  expect(result.errors).not.toContain(
    "Add one or more supported EEG recordings: .e, .edf/.edf+, or matched .data/.head pairs.",
  );
});

test("prompts for an EEG recording without implying only one is allowed", () => {
  const result = classifyPatientFolder([folderFile("case/report.doc")]);

  expect(result.errors).toContain(
    "Add one or more supported EEG recordings: .e, .edf/.edf+, or matched .data/.head pairs.",
  );
});

test("returns multiple EEG candidates for an explicit local choice", () => {
  const result = classifyPatientFolder([
    folderFile("case/first.e"),
    folderFile("case/second.e"),
    folderFile("case/report.doc"),
  ]);

  expect(result.eeg).toBeNull();
  expect(result.eegCandidates).toHaveLength(2);
  expect(result.errors).toEqual([]);
});

test("archives every selected EEG recording with distinct neutral names", async () => {
  const selection = classifyPatientFolder([
    folderFile("case/first.e", "first synthetic recording"),
    folderFile("case/second.e", "second synthetic recording"),
    folderFile("case/report.doc", "private report"),
  ]);
  const archive = await buildEegArchive(selection.eegCandidates);
  const entries = unzipSync(new Uint8Array(await archive.arrayBuffer()));

  expect(Object.keys(entries)).toEqual(["recording-01.e", "recording-02.e"]);
  expect(new TextDecoder().decode(entries["recording-01.e"])).toBe(
    "first synthetic recording",
  );
  expect(new TextDecoder().decode(entries["recording-02.e"])).toBe(
    "second synthetic recording",
  );
  expect(Object.keys(entries).join(" ")).not.toContain("case");
});

test("archives only EEG bytes under neutral names and fixed metadata", async () => {
  const source = folderFile(
    "patient-identifier/recording.e",
    "secret-synthetic-signal",
  );
  const selection = classifyPatientFolder([
    source,
    folderFile("patient-identifier/report.doc", "private-report-text"),
  ]);
  const archive = await buildEegArchive(selection.eeg!);
  const entries = unzipSync(new Uint8Array(await archive.arrayBuffer()));

  expect(Object.keys(entries)).toEqual(["recording.e"]);
  expect(new TextDecoder().decode(entries["recording.e"])).toBe(
    "secret-synthetic-signal",
  );
  expect(
    new TextDecoder().decode(new Uint8Array(await archive.arrayBuffer())),
  ).not.toContain("patient-identifier");
  expect(
    new TextDecoder().decode(new Uint8Array(await archive.arrayBuffer())),
  ).not.toContain("private-report-text");
});

test("extracts editable report fields without absorbing later identity into findings", () => {
  expect(
    extractPatientReportDraft(
      "Patient Name: Synthetic Person\nHospital ID: H-42\nAge: 47 years\nSex: Female\nFindings:\nSynthetic observed finding.\nPatient Name: Synthetic Person\nMRN: MRN-42\nImpression:\nSynthetic reviewed impression.\nMedication: review before saving",
    ),
  ).toEqual({
    details: [
      { label: "Patient Name", value: "Synthetic Person" },
      { label: "Hospital ID", value: "H-42" },
      { label: "Age", value: "47 years" },
      { label: "Sex", value: "Female" },
      { label: "Findings", value: "Synthetic observed finding." },
      { label: "Patient Name", value: "Synthetic Person" },
      { label: "MRN", value: "MRN-42" },
      { label: "Impression", value: "Synthetic reviewed impression." },
      { label: "Medication", value: "review before saving" },
    ],
    truncated: false,
  });
  expect(extractPatientReportDraft("Diagnosis: synthetic-only")).toEqual({
    details: [{ label: "Diagnosis", value: "synthetic-only" }],
    truncated: false,
  });
  expect(
    extractPatientReportDraft(
      "Patient Name\nSynthetic Person\nHospital ID\nH-42\nMedication:\nignore this",
    ),
  ).toMatchObject({
    details: [
      { label: "Patient Name", value: "Synthetic Person" },
      { label: "Hospital ID", value: "H-42" },
      { label: "Medication", value: "ignore this" },
    ],
  });
  expect(
    extractPatientReportDraft(
      "Patient Name: Synthetic Person Hospital ID: H-42 Diagnosis: synthetic-only",
    ),
  ).toMatchObject({
    details: [
      { label: "Patient Name", value: "Synthetic Person" },
      { label: "Hospital ID", value: "H-42" },
      { label: "Diagnosis", value: "synthetic-only" },
    ],
  });
  expect(
    extractPatientReportDraft(`Findings:\n${"x".repeat(30000)}`).truncated,
  ).toBe(true);
});

test("extracts technical, event, conclusion, and specialist report headings", () => {
  expect(
    extractPatientReportDraft(
      "TECHNICAL SUMMARY\nSynthetic technical description.\nEVENTS\nSynthetic recorded event.\nCONCLUSIONS\nSynthetic conclusion.\nSPECIALIST NAMES\nSynthetic specialist.",
    ).details,
  ).toEqual([
    {
      label: "TECHNICAL SUMMARY",
      value: "Synthetic technical description.",
    },
    { label: "EVENTS", value: "Synthetic recorded event." },
    { label: "CONCLUSIONS", value: "Synthetic conclusion." },
    { label: "SPECIALIST NAMES", value: "Synthetic specialist." },
  ]);
});

test("keeps the EEG report sections and date labels separate during extraction", () => {
  const result = extractPatientReportDraft(
    [
      "EEG NO",
      "VT 2/2026",
      "UNIT Neurology, Clinical Laboratory",
      "Synthetic Hospital",
      "03-1234567",
      "PATIENT DETIALS",
      "PATIENT NAME",
      "Synthetic Person",
      "IC NO",
      "000000-00-0000",
      "MRN NO",
      "SYN-42",
      "SEX",
      "Female",
      "RACE",
      "Synthetic",
      "HAND DOMINANCE",
      "R",
      "DATE & TIME:",
      "13/1/2026 6:46:30 AM",
      "TEST INFORMATION",
      "TYPES OF TEST",
      "ROUTINE EEG",
      "INTERICTAL RECORD",
      "Synthetic interictal details.",
      "ICTAL RECORD",
      "Synthetic ictal details.",
      "ATTACKS",
      "Two attacks captured.",
      "CONCLUSIONS",
      "Synthetic conclusion.",
      "SPECIALIST NAMES",
      "Synthetic neurologist",
      "DATE",
      "14.1.2026",
    ].join("\n"),
  );

  expect(result.details).toEqual([
    { label: "EEG NO", value: "VT 2/2026" },
    {
      label: "Institution",
      value:
        "UNIT Neurology, Clinical Laboratory\nSynthetic Hospital\n03-1234567",
    },
    { label: "PATIENT NAME", value: "Synthetic Person" },
    { label: "IC NO", value: "000000-00-0000" },
    { label: "MRN NO", value: "SYN-42" },
    { label: "SEX", value: "Female" },
    { label: "RACE", value: "Synthetic" },
    { label: "HAND DOMINANCE", value: "R" },
    { label: "DATE & TIME", value: "13/1/2026 6:46:30 AM" },
    { label: "TYPES OF TEST", value: "ROUTINE EEG" },
    { label: "INTERICTAL RECORD", value: "Synthetic interictal details." },
    { label: "ICTAL RECORD", value: "Synthetic ictal details." },
    { label: "ATTACKS", value: "Two attacks captured." },
    { label: "CONCLUSIONS", value: "Synthetic conclusion." },
    { label: "SPECIALIST NAMES", value: "Synthetic neurologist" },
    { label: "DATE", value: "14.1.2026" },
  ]);
  expect(result.truncated).toBe(false);
});

test("/upload opens the one-patient multi-recording intake", async ({
  page,
}) => {
  await page.goto("/upload");

  await expect(
    page.getByRole("heading", { name: "Add a patient recording" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /choose patient folder/i }),
  ).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
});

test("/upload/eeg accepts one EEG file without requiring a folder or report", async ({
  page,
}) => {
  await page.goto("/upload/eeg");
  await expect(
    page.getByRole("heading", { name: "Add EEG recordings" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Choose one EEG file" }),
  ).toBeVisible();
  await page.getByLabel("Choose one EEG recording").setInputFiles({
    name: "recording.e",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("synthetic-eeg"),
  });

  await expect(page.getByRole("region", { name: "Video input" })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("region", { name: "Privacy settings" }),
  ).toContainText("1 EEG recording included automatically");
  await expect(page.getByText("Imported report", { exact: true })).toHaveCount(
    0,
  );
});

test("local legacy Word extraction returns a bounded review draft only", async ({
  page,
}) => {
  test.skip(
    process.platform !== "darwin",
    "textutil is the local macOS parser",
  );
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated report fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-report-test-"));
  try {
    const rtf = join(folder, "report.rtf");
    const doc = join(folder, "report.doc");
    writeFileSync(
      rtf,
      "{\\rtf1\\ansi Patient Name: Synthetic Person\\line Hospital ID: H-42\\line Age: 47 years\\line Findings:\\line Synthetic finding.\\line Impression:\\line Synthetic impression.\\line Medication: synthetic-only}",
    );
    const conversion = spawnSync(
      "/usr/bin/textutil",
      ["-convert", "doc", "-output", doc, rtf],
      { timeout: 15_000 },
    );
    expect(conversion.status).toBe(0);
    const extracted = spawnSync(
      "/usr/bin/textutil",
      ["-convert", "txt", "-stdout", "-stdin", "-strip"],
      {
        input: readFileSync(doc),
        encoding: "utf8",
        env: {
          PATH: "/usr/bin:/bin",
          LANG: "en_US.UTF-8",
          NODE_ENV: "development",
        },
      },
    );
    expect(extracted.status).toBe(0);
    expect(extractPatientReportDraft(extracted.stdout)).toMatchObject({
      details: expect.arrayContaining([
        { label: "Patient Name", value: "Synthetic Person" },
        { label: "Hospital ID", value: "H-42" },
        { label: "Age", value: "47 years" },
        { label: "Findings", value: "Synthetic finding." },
        { label: "Medication", value: "synthetic-only" },
      ]),
      truncated: false,
    });

    await page.goto("/upload");
    const origin = new URL(page.url()).origin;
    const response = await page.request.post(`${origin}/api/patient-report`, {
      headers: { Origin: origin },
      multipart: {
        report: {
          name: "patient-report.doc",
          mimeType: "application/msword",
          buffer: readFileSync(doc),
        },
      },
    });
    const responseText = await response.text();
    expect(response.status(), responseText).toBe(200);
    expect(response.headers()["cache-control"]).toBe("no-store");
    const payload = JSON.parse(responseText) as unknown;
    expect(payload).toEqual({
      draft: {
        details: [
          { label: "Patient Name", value: "Synthetic Person" },
          { label: "Hospital ID", value: "H-42" },
          { label: "Age", value: "47 years" },
          { label: "Findings", value: "Synthetic finding." },
          { label: "Impression", value: "Synthetic impression." },
          { label: "Medication", value: "synthetic-only" },
        ],
        truncated: false,
      },
      stored: false,
    });
    expect(JSON.stringify(payload)).toContain("synthetic-only");
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("a delayed report response cannot replace details from a newer folder", async ({
  page,
}) => {
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const firstFolder = mkdtempSync(join(scratch, "mds01-report-race-a-"));
  const secondFolder = mkdtempSync(join(scratch, "mds01-report-race-b-"));
  let requestCount = 0;
  let releaseFirst = () => {};
  let markFirstStarted = () => {};
  let markFirstFinished = () => {};
  const firstGate = new Promise<void>((resolve) => (releaseFirst = resolve));
  const firstStarted = new Promise<void>(
    (resolve) => (markFirstStarted = resolve),
  );
  const firstFinished = new Promise<void>(
    (resolve) => (markFirstFinished = resolve),
  );
  const reportResponse = (name: string) => ({
    status: 200,
    contentType: "application/json" as const,
    headers: { "Cache-Control": "no-store" },
    json: {
      draft: { details: [{ label: "Patient Name", value: name }] },
      stored: false,
    },
  });
  await page.route("**/api/patient-report", async (route) => {
    const requestIndex = requestCount++;
    if (requestIndex === 0) {
      markFirstStarted();
      await firstGate;
      try {
        await route.fulfill(reportResponse("Synthetic Patient A"));
      } catch {
        // The browser may cancel this superseded local extraction request.
      } finally {
        markFirstFinished();
      }
      return;
    }
    await route.fulfill(reportResponse("Synthetic Patient B"));
  });

  await page.goto("/upload");
  try {
    writeFileSync(join(firstFolder, "recording.e"), "synthetic-eeg-a");
    writeFileSync(join(firstFolder, "report.doc"), "synthetic-report-a");
    writeFileSync(join(secondFolder, "recording.e"), "synthetic-eeg-b");
    writeFileSync(join(secondFolder, "report.doc"), "synthetic-report-b");

    const folderInput = page.locator('input[type="file"][webkitdirectory]');
    await folderInput.setInputFiles(firstFolder);
    await firstStarted;
    await folderInput.setInputFiles(secondFolder);
    const patientDetails = page.getByRole("region", {
      name: "Patient details",
    });
    await expect(
      patientDetails.getByText("Synthetic Patient B", { exact: true }),
    ).toBeVisible();
    releaseFirst();
    await firstFinished;
    await expect(
      page.getByText("Synthetic Patient A", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText("Synthetic Patient B", { exact: true }),
    ).toHaveCount(1);
  } finally {
    releaseFirst();
    rmSync(firstFolder, { recursive: true, force: true });
    rmSync(secondFolder, { recursive: true, force: true });
  }
});

test("folder review displays all extracted details without a confirmation step", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "true",
    "This test covers the disconnected API-stub view.",
  );
  await page.route("**/api/patient-report", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Cache-Control": "no-store" },
      body: JSON.stringify({
        draft: {
          details: [
            { label: "Patient Name", value: "Synthetic Person" },
            { label: "Hospital ID", value: "H-42" },
            { label: "Age", value: "47 years" },
            { label: "Findings", value: "Synthetic finding." },
            { label: "Medication", value: "synthetic medication" },
          ],
          truncated: false,
        },
      }),
    });
  });
  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-folder-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "second-recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "clip.avi"), "synthetic-video");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);

    const details = page.getByRole("region", { name: "Patient details" });
    const extractedDetails = details.locator("details");
    await expect(extractedDetails).toHaveJSProperty("open", false);
    await expect(
      details.getByText("Synthetic Person", { exact: true }),
    ).toBeHidden();
    await extractedDetails.locator("summary").click();
    for (const value of [
      "Synthetic Person",
      "H-42",
      "47 years",
      "Synthetic finding.",
      "synthetic medication",
    ]) {
      await expect(details).toContainText(value);
    }
    await expect(details.getByRole("checkbox")).toHaveCount(0);
    await expect(details.locator("input, textarea, button")).toHaveCount(0);
    await expect(
      page.getByRole("region", { name: "Video input" }),
    ).toContainText("1 video clip included automatically");
    await expect(
      page.getByRole("button", { name: "Start processing" }),
    ).toBeDisabled();
    await expect(
      page.getByText("Connect the local API to create a patient review."),
    ).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(350);
    const viewport = await page.evaluate(() => ({
      width: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      headerBottom: document
        .querySelector(".app-header")
        ?.getBoundingClientRect().bottom,
      mainTop: document.querySelector("#main-content")?.getBoundingClientRect()
        .top,
    }));
    expect(viewport.documentWidth).toBeLessThanOrEqual(viewport.width);
    expect(viewport.headerBottom).toBeLessThanOrEqual(viewport.mainTop ?? 0);
    await page.screenshot({
      path: test.info().outputPath("patient-folder-review.png"),
      fullPage: true,
    });
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("empty report extraction has no field-selection controls", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "true",
    "This test covers local report extraction in the disconnected API-stub view.",
  );
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      json: { draft: { details: [], truncated: false } },
    }),
  );
  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-empty-report-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);

    const details = page.getByRole("region", { name: "Patient details" });
    await expect(details).toContainText("No patient details were extracted");
    await expect(details.getByRole("checkbox")).toHaveCount(0);
    await expect(details.getByRole("button")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Start processing" }),
    ).toBeDisabled();
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("video clips are summarized and included automatically for VSViG", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "true",
    "This test covers the disconnected API-stub view.",
  );
  await page.route("**/api/patient-report", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Cache-Control": "no-store" },
      body: JSON.stringify({
        draft: {
          details: [
            { label: "Patient Name", value: "Synthetic Person" },
            { label: "Hospital ID", value: "Synthetic-H42" },
          ],
          truncated: false,
        },
        stored: false,
      }),
    });
  });
  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-preflight-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "second-recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "first.avi"), "synthetic-video-one");
    writeFileSync(join(folder, "second.avi"), "synthetic-video-two");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);

    const videoInput = page.getByRole("region", {
      name: "Video input",
    });
    await expect(videoInput).toContainText(
      "2 video clips included automatically",
    );
    await expect(videoInput).toContainText(
      "VSViG receives the coordinates plus 15 RGB patches blurred individually after extraction",
    );
    await expect(page.getByText("EEG input", { exact: true })).toHaveCount(0);
    await expect(
      page.getByRole("region", { name: /\d+ EEG recordings?/ }),
    ).toHaveCount(0);
    await expect(page.getByLabel(/Include EEG recording/)).toHaveCount(0);
    await expect(videoInput.getByRole("checkbox")).toHaveCount(0);
    await expect(videoInput.getByRole("button")).toHaveCount(0);
    const privacySettings = page.getByRole("region", {
      name: "Privacy settings",
    });
    await expect(privacySettings.getByRole("checkbox")).toHaveCount(1);
    await expect(
      privacySettings.getByRole("checkbox", { name: "Signal obfuscation" }),
    ).toBeVisible();
    await expect(
      privacySettings.getByRole("heading", {
        name: "Privacy representation preview",
      }),
    ).toBeVisible();
    await expect(privacySettings).toContainText("Before · staged");
    await expect(privacySettings).toContainText("After · metadata scrubbed");
    await expect(privacySettings).toContainText(
      "Illustrative preview — synthetic data, not your uploaded VEEG.",
    );
    await expect(
      page.getByRole("checkbox", { name: /VSViG analysis for clip/ }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Start processing" }),
    ).toBeVisible();
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("one patient folder includes every report detail and proceeds directly to processing", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify intercepted uploads.",
  );
  const createdAt = "2026-09-27T00:00:00Z";
  const archiveContentTypes: string[] = [];
  let finalizedPayload = "";
  let savedDetails: Array<{ label: string; value: string }> = [];
  let profileVerificationStatus: string | null = null;
  const videoDetectionRequests: string[] = [];
  let releaseUploadResponse = () => {};
  let markUploadStarted = () => {};
  const uploadResponseGate = new Promise<void>((resolve) => {
    releaseUploadResponse = resolve;
  });
  const uploadStarted = new Promise<void>((resolve) => {
    markUploadStarted = resolve;
  });

  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/api/video-detection/jobs"))
      videoDetectionRequests.push(`${request.method()} ${pathname}`);
  });
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [
            { label: "Patient Name", value: "Synthetic Person" },
            { label: "Hospital ID", value: "Synthetic-H42" },
            { label: "Age", value: "47 years" },
            { label: "Findings", value: "Synthetic reviewed finding." },
          ],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", async (route) => {
    const request = route.request();
    archiveContentTypes.push(request.headers()["content-type"] ?? "");
    markUploadStarted();
    await uploadResponseGate;
    return route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: "2026-09-28T00:00:00Z",
      },
    });
  });
  await page.route("**/api/uploads/drafts/UPL-SYNTHETIC/finalize", (route) => {
    finalizedPayload = route.request().postDataBuffer()?.toString("utf8") ?? "";
    return route.fulfill({
      status: 202,
      json: {
        session_id: "MDS-SYNTHETIC",
        case_id: "CASE-SYNTHETIC",
        status: "queued",
      },
    });
  });
  await page.route("**/api/sessions/MDS-SYNTHETIC", (route) =>
    route.fulfill({
      json: {
        session_id: "MDS-SYNTHETIC",
        case_id: "CASE-SYNTHETIC",
        privacy_method: "metadata-scrub",
        privacy_methods: ["metadata-scrub", "signal-obfuscation"],
        status: "completed",
        current_stage: "complete",
        created_at: createdAt,
        completed_at: createdAt,
        error_message: null,
        progress: {
          total_recordings: 2,
          finished_recordings: 2,
          completed_recordings: 2,
          failed_recordings: 0,
          percent: 100,
        },
        summary: { model_alert_recordings: 0 },
        recordings: [],
      },
    }),
  );
  await page.route(
    "**/api/cases/CASE-SYNTHETIC/patient-profile**",
    async (route) => {
      if (route.request().method() === "PUT") {
        const payload = route.request().postDataJSON() as {
          details: Array<{ label: string; value: string }>;
        };
        savedDetails = payload.details;
        profileVerificationStatus = "auto_extracted";
      }
      return route.fulfill({
        json: {
          profile: {
            name: "Synthetic Person",
            hospital_id: "Synthetic-H42",
            age: "47 years",
            findings: "",
            details: savedDetails,
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      });
    },
  );
  await page.route("**/api/cases/CASE-SYNTHETIC", (route) =>
    route.fulfill({
      json: {
        case_id: "CASE-SYNTHETIC",
        analyses: [
          {
            id: "MDS-SYNTHETIC",
            modality: "eeg",
            status: "processing",
            created_at: createdAt,
            review_ready: false,
          },
        ],
      },
    }),
  );
  await page.route(
    "**/api/video-privacy/jobs?case_id=CASE-SYNTHETIC",
    (route) => route.fulfill({ json: { jobs: [] } }),
  );

  await page.addInitScript(() => {
    const send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (body) {
      if (body instanceof Blob && body.size > 0) {
        this.upload.dispatchEvent(
          new ProgressEvent("progress", {
            lengthComputable: true,
            loaded: 18,
            total: 100,
          }),
        );
      }
      return send.call(this, body);
    };
  });
  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-patient-submit-test-"));
  try {
    writeFileSync(join(folder, "patient-a.e"), "synthetic-eeg-one");
    writeFileSync(join(folder, "patient-b.e"), "synthetic-eeg-two");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);

    const mediaPrivacy = page.getByRole("region", { name: "Privacy settings" });
    await mediaPrivacy
      .getByRole("checkbox", { name: "Signal obfuscation" })
      .check();
    const reportDetails = page.getByRole("region", { name: "Patient details" });
    const extractedDetails = reportDetails.locator("details");
    await expect(extractedDetails).toHaveJSProperty("open", false);
    await extractedDetails.locator("summary").click();
    for (const value of [
      "Synthetic Person",
      "Synthetic-H42",
      "47 years",
      "Synthetic reviewed finding.",
    ]) {
      await expect(reportDetails).toContainText(value);
    }
    await expect(
      page.getByRole("checkbox", { name: /Include detail/ }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Continue to patient details" }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Start processing" }).click();

    await uploadStarted;
    const uploadProgress = page.getByRole("region", {
      name: "Recording analysis",
    });
    await expect(uploadProgress).toContainText(
      "2 EEG recordings · 18% of archive uploaded",
    );
    await expect(
      uploadProgress.getByRole("progressbar", {
        name: "EEG processing progress",
      }),
    ).toHaveJSProperty("value", 18);
    releaseUploadResponse();

    await expect(
      page.getByRole("heading", { name: "Processing complete" }),
    ).toBeVisible();
    await expect(
      page.getByText("2 of 2 EEG recordings complete"),
    ).toBeVisible();
    await page.getByRole("link", { name: "Open patient review" }).click();

    await expect(page).toHaveURL(/\/cases\/CASE-SYNTHETIC$/);
    await expect(
      page.getByRole("heading", { name: "Report overview" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Patient review" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Synthetic Person" }),
    ).toBeVisible();
    await expect(page.getByText("47 years", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Synthetic reviewed finding.", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Synthetic-H42", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Auto-extracted · not reviewed", { exact: true }),
    ).toHaveCount(0);

    expect(profileVerificationStatus).toBe("auto_extracted");
    expect(savedDetails.map((detail) => detail.label)).toEqual([
      "Patient Name",
      "Hospital ID",
      "Age",
      "Findings",
    ]);
    expect(archiveContentTypes).toEqual(["application/octet-stream"]);
    expect(finalizedPayload).toContain(
      '["metadata-scrub","signal-obfuscation"]',
    );
    expect(videoDetectionRequests).toEqual([]);
  } finally {
    releaseUploadResponse();
    rmSync(folder, { recursive: true, force: true });
  }
});

test("canceling finalization prevents a late patient-case redirect", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify cancellation of API work.",
  );
  let releaseFinalize = () => {};
  let markFinalizeStarted = () => {};
  let markFinalizeSettled = () => {};
  const finalizeGate = new Promise<void>((resolve) => {
    releaseFinalize = resolve;
  });
  const finalizeStarted = new Promise<void>((resolve) => {
    markFinalizeStarted = resolve;
  });
  const finalizeSettled = new Promise<void>((resolve) => {
    markFinalizeSettled = resolve;
  });
  const reviewedAt = "2026-09-27T00:00:00Z";

  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [
            { label: "Findings", value: "Synthetic cancellation test" },
          ],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-CANCEL",
        status: "staged",
        created_at: reviewedAt,
        expires_at: "2026-09-28T00:00:00Z",
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-CANCEL/finalize",
    async (route) => {
      markFinalizeStarted();
      await finalizeGate;
      try {
        await route.fulfill({
          status: 202,
          json: {
            session_id: "MDS-CANCEL",
            case_id: "CASE-CANCEL",
            status: "queued",
          },
        });
      } catch {
        // Cancellation may abort the held request before the synthetic reply.
      } finally {
        markFinalizeSettled();
      }
    },
  );
  await page.route(
    "**/api/cases/CASE-CANCEL/patient-profile**",
    async (route) => {
      const body = route.request().postDataJSON() as {
        details: Array<{ label: string; value: string }>;
      };
      await route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: body.details,
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      });
    },
  );

  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-cancel-review-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();
    await finalizeStarted;

    await page.getByRole("button", { name: "Cancel intake" }).click();
    await expect(
      page.locator('[role="alert"]').filter({
        hasText: "Work already accepted by the service may continue",
      }),
    ).toBeVisible();
    releaseFinalize();
    await finalizeSettled;
    await expect(page).toHaveURL((url) => url.pathname.endsWith("/upload"));
  } finally {
    releaseFinalize();
    rmSync(folder, { recursive: true, force: true });
  }
});

test("media intake splits EEG privacy from video input and shows details inline", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "true",
    "This test covers the disconnected API-stub intake view.",
  );
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Cache-Control": "no-store" },
      json: {
        draft: {
          details: [
            { label: "Patient Name", value: "Synthetic Person" },
            { label: "Findings", value: "Synthetic finding." },
          ],
          truncated: false,
        },
      },
    }),
  );
  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-media-step-test-"));
  try {
    writeFileSync(join(folder, "recording-one.e"), "synthetic-eeg");
    writeFileSync(join(folder, "recording-two.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "clip-one.avi"), "synthetic-video");
    writeFileSync(join(folder, "clip-two.avi"), "synthetic-video");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);

    const video = page.getByRole("region", { name: "Video input" });
    const privacy = page.getByRole("region", { name: "Privacy settings" });
    const details = page.getByRole("region", { name: "Patient details" });
    await expect(privacy).toContainText(
      "2 EEG recordings included automatically and analyzed independently",
    );
    await expect(video).toContainText("2 video clips included automatically");
    await expect(video).toContainText(
      "VSViG receives the coordinates plus 15 RGB patches blurred individually after extraction",
    );
    const blurStrength = video.getByRole("slider", {
      name: "VSViG model-input blur strength",
    });
    await expect(blurStrength).toHaveValue("100");
    await blurStrength.focus();
    await blurStrength.press("Home");
    await expect(blurStrength).toHaveValue("50");
    await expect(page.getByText("EEG input", { exact: true })).toHaveCount(0);
    await expect(
      page.getByRole("region", { name: /\d+ EEG recordings?/ }),
    ).toHaveCount(0);
    await expect(
      privacy.getByRole("checkbox", { name: "Signal obfuscation" }),
    ).toBeVisible();
    await expect(
      privacy.getByRole("heading", { name: "Privacy representation preview" }),
    ).toBeVisible();
    await expect(privacy).toContainText("Before · staged");
    await expect(privacy).toContainText("After · metadata scrubbed");
    await expect(privacy).toContainText(
      "Illustrative preview — synthetic data, not your uploaded VEEG.",
    );
    await expect(
      details.getByText("Synthetic Person", { exact: true }),
    ).toBeHidden();
    await details.getByText("View extracted details").click();
    await expect(
      details.getByText("Synthetic Person", { exact: true }),
    ).toBeVisible();
    await expect(
      details.getByText("Synthetic finding.", { exact: true }),
    ).toBeVisible();
    await expect(details.getByRole("checkbox")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Start processing" }),
    ).toBeDisabled();

    if ((await page.evaluate(() => window.innerWidth)) >= 1024) {
      const privacyBox = await privacy.boundingBox();
      const videoBox = await video.boundingBox();
      expect(privacyBox).not.toBeNull();
      expect(videoBox).not.toBeNull();
      expect(privacyBox!.x + privacyBox!.width).toBeLessThan(videoBox!.x);
    }
    await page.screenshot({
      path: test.info().outputPath("patient-folder-media-step.png"),
      fullPage: true,
    });
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("one case queues all videos independently from EEG before polling", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted inference workflow.",
  );
  const createdAt = "2026-09-27T00:00:00Z";
  const detectionJobs: Array<Record<string, unknown> & { job_id: string }> = [];
  const detectionEvents: string[] = [];
  const detectionFormats: string[] = [];
  const detectionCaseIds: string[] = [];
  const detectionBlurStrengths: string[] = [];
  let savedDetails: Array<{ label: string; value: string }> = [];
  let legacyPrivacyRequests = 0;
  let eegTerminalSeen = false;
  let videoSubmittedBeforeEeg = false;

  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/api/video-detection/jobs")) {
      detectionEvents.push(`${request.method()} ${pathname}`);
    }
    if (request.method() === "POST" && pathname === "/api/video-privacy/jobs") {
      legacyPrivacyRequests += 1;
    }
  });
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-VIDEO-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: "2026-09-28T00:00:00Z",
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-VIDEO-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-VIDEO-SYNTHETIC",
          case_id: "CASE-VIDEO-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-VIDEO-SYNTHETIC", (route) => {
    const sessionComplete = detectionJobs.length > 0;
    if (sessionComplete) eegTerminalSeen = true;
    return route.fulfill({
      json: {
        session_id: "MDS-VIDEO-SYNTHETIC",
        case_id: "CASE-VIDEO-SYNTHETIC",
        privacy_method: "metadata-scrub",
        privacy_methods: ["metadata-scrub"],
        status: sessionComplete ? "completed" : "processing",
        current_stage: sessionComplete ? "complete" : "inference",
        created_at: createdAt,
        completed_at: sessionComplete ? createdAt : null,
        error_message: null,
        progress: {
          total_recordings: 2,
          finished_recordings: sessionComplete ? 2 : 0,
          completed_recordings: sessionComplete ? 2 : 0,
          failed_recordings: 0,
          percent: sessionComplete ? 100 : 0,
        },
        summary: { model_alert_recordings: 0 },
        recordings: [],
      },
    });
  });
  await page.route(
    "**/api/cases/CASE-VIDEO-SYNTHETIC/patient-profile**",
    async (route) => {
      if (route.request().method() === "PUT") {
        const body = route.request().postDataJSON() as {
          details: Array<{ label: string; value: string }>;
        };
        savedDetails = body.details;
      }
      return route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: savedDetails,
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      });
    },
  );
  await page.route("**/api/video-detection/jobs", async (route) => {
    if (route.request().method() !== "POST")
      return route.fulfill({ json: { jobs: detectionJobs } });
    if (!eegTerminalSeen) videoSubmittedBeforeEeg = true;
    const request = route.request();
    const headers = request.headers();
    detectionFormats.push(headers["x-video-format"] ?? "");
    detectionCaseIds.push(headers["x-case-id"] ?? "");
    detectionBlurStrengths.push(headers["x-model-blur-percent"] ?? "");
    const index = detectionJobs.length + 1;
    const job = {
      job_id: `VID-DETECTION-SYNTHETIC-${index}`,
      case_id: "CASE-VIDEO-SYNTHETIC",
      label: `Video ${index}`,
      status: "queued",
      current_stage: "queued",
      duration_seconds: 5,
      fps: 25,
      blur_strength_percent: Number(headers["x-model-blur-percent"] ?? "100"),
      created_at: createdAt,
      retention_expires_at: "2026-09-28T00:00:00Z",
      video_available: false,
      error: null,
    };
    detectionJobs.push(job);
    return route.fulfill({ status: 202, json: { job } });
  });
  await page.route(
    "**/api/video-detection/jobs/VID-DETECTION-SYNTHETIC-*",
    (route) => {
      const jobId = new URL(route.request().url()).pathname.split("/").at(-1);
      const job = detectionJobs.find((candidate) => candidate.job_id === jobId);
      if (!job)
        return route.fulfill({ status: 404, json: { detail: "Not found." } });
      if (jobId?.endsWith("-1")) {
        job.status = "failed";
        job.current_stage = "failed";
        job.error =
          "Too many patient landmarks were missing or obscured for this model. Try a clearer clip.";
      } else {
        job.status = "ready";
        job.current_stage = "complete";
      }
      return route.fulfill({ json: { job } });
    },
  );
  await page.route(
    "**/api/video-privacy/jobs?case_id=CASE-VIDEO-SYNTHETIC",
    (route) => route.fulfill({ json: { jobs: [] } }),
  );
  await page.route("**/api/video-privacy/jobs", (route) =>
    route.fulfill({ status: 404, json: { detail: "Not found." } }),
  );
  await page.route("**/api/cases/CASE-VIDEO-SYNTHETIC", (route) =>
    route.fulfill({
      json: {
        case_id: "CASE-VIDEO-SYNTHETIC",
        analyses: [
          {
            id: "MDS-VIDEO-SYNTHETIC",
            modality: "eeg",
            status: "processing",
            created_at: createdAt,
            review_ready: false,
          },
          ...detectionJobs.map((job) => ({
            id: job.job_id,
            modality: "video",
            status: job.status === "failed" ? "needs_review" : "complete",
            created_at: createdAt,
            review_ready: job.status === "ready",
          })),
        ],
      },
    }),
  );

  await page.goto("/upload");
  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-video-jobs-test-"));
  try {
    writeFileSync(join(folder, "recording-one.e"), "synthetic-eeg-one");
    writeFileSync(join(folder, "recording-two.e"), "synthetic-eeg-two");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    for (let index = 1; index <= 9; index += 1) {
      writeFileSync(
        join(folder, `clip-${index}.avi`),
        `synthetic-video-${index}`,
      );
    }
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);

    await expect(
      page.getByRole("region", { name: "Video input" }),
    ).toContainText("9 video clips included automatically");
    const blurStrength = page.getByRole("slider", {
      name: "VSViG model-input blur strength",
    });
    await expect(blurStrength).toHaveValue("100");
    await blurStrength.focus();
    await blurStrength.press("Home");
    await blurStrength.press("ArrowRight");
    await blurStrength.press("ArrowRight");
    await blurStrength.press("ArrowRight");
    await expect(blurStrength).toHaveValue("65");
    await page.getByRole("button", { name: "Start processing" }).click();
    await expect(
      page.getByRole("progressbar", {
        name: "Overall EEG and video processing progress",
      }),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", { name: "Processing finished with issues" }),
    ).toBeVisible();
    await expect(
      page.getByText("2 of 2 EEG recordings complete"),
    ).toBeVisible();
    const videoProgressRegion = page.getByRole("region", {
      name: "Video processing",
    });
    await expect(
      videoProgressRegion.getByText("Complete", { exact: true }),
    ).toHaveCount(8);
    await expect(videoProgressRegion.getByRole("progressbar")).toHaveCount(0);
    await expect(videoProgressRegion.getByText(/Phase estimate/)).toHaveCount(
      0,
    );
    const videoList = videoProgressRegion.locator("details");
    await expect(videoList.getByText("Video 1", { exact: true })).toBeHidden();
    await expect(videoList.locator("summary")).toContainText(
      "Show 9 video clips",
    );
    await expect(videoList.locator("summary")).toContainText(
      "8 complete · 0 in progress · 1 needs attention",
    );
    await videoList.locator("summary").click();
    await expect(videoList.getByText("Video 1", { exact: true })).toBeVisible();
    await expect(videoList.getByText("Video 9", { exact: true })).toBeVisible();
    await expect(videoList).toContainText(
      "Pose extraction could not find all 15 body landmarks required by VSViG",
    );
    await page.getByRole("link", { name: "Open patient review" }).click();
    await expect(page).toHaveURL(/\/cases\/CASE-VIDEO-SYNTHETIC$/);
    await expect(
      page.getByRole("heading", { name: "Report overview" }),
    ).toBeVisible();
    await expect(
      page.getByText("VSViG video analysis", { exact: true }),
    ).toHaveCount(9);
    expect(savedDetails).toEqual([
      { label: "Findings", value: "Synthetic finding." },
    ]);
    expect(detectionFormats).toEqual(Array(9).fill("avi"));
    expect(detectionBlurStrengths).toEqual(Array(9).fill("65"));
    expect(detectionCaseIds).toEqual(Array(9).fill("CASE-VIDEO-SYNTHETIC"));
    expect(detectionJobs).toHaveLength(9);
    expect(videoSubmittedBeforeEeg).toBe(true);
    expect(legacyPrivacyRequests).toBe(0);
    expect(detectionEvents.slice(0, 9)).toEqual(
      Array(9).fill("POST /api/video-detection/jobs"),
    );
    const firstStatusRead = detectionEvents.findIndex((event) =>
      event.startsWith(
        "GET /api/video-detection/jobs/VID-DETECTION-SYNTHETIC-",
      ),
    );
    expect(firstStatusRead).toBeGreaterThanOrEqual(9);
    expect(
      detectionEvents.filter((event) =>
        event.startsWith(
          "GET /api/video-detection/jobs/VID-DETECTION-SYNTHETIC-",
        ),
      ),
    ).toHaveLength(9);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("shows a safe message for a structured upload validation error", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to exercise streamed upload errors.",
  );
  let contentType = "";
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) => {
    contentType = route.request().headers()["content-type"] ?? "";
    return route.fulfill({
      status: 422,
      json: {
        detail: [
          {
            type: "missing",
            loc: ["body", "archive"],
            msg: "Field required",
            input: null,
          },
        ],
      },
    });
  });

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(join(scratch, "mds01-upload-422-test-"));
  try {
    writeFileSync(join(folder, "recording.e"), "synthetic-eeg");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();

    const alert = page.getByRole("main").getByRole("alert");
    await expect(alert).toContainText("rejected (422)");
    await expect(alert).not.toContainText("[object Object]");
    await expect(alert).not.toContainText("archive");
    expect(contentType).toContain("application/octet-stream");
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("video privacy-gate failures stay visible before model scoring", async ({
  page,
}) => {
  test.skip(
    process.env.NEXT_PUBLIC_USE_API_STUB !== "false",
    "Run with NEXT_PUBLIC_USE_API_STUB=false to verify the intercepted detection workflow.",
  );
  const createdAt = "2026-09-27T00:00:00Z";
  const detectionJobs: Array<Record<string, unknown> & { job_id: string }> = [];
  let detectionPosts = 0;
  let predictionRequests = 0;

  await page.on("request", (request) => {
    if (new URL(request.url()).pathname.endsWith("/predictions"))
      predictionRequests += 1;
  });
  await page.route("**/api/patient-report", (route) =>
    route.fulfill({
      json: {
        draft: {
          details: [{ label: "Findings", value: "Synthetic finding." }],
          truncated: false,
        },
      },
    }),
  );
  await page.route("**/api/uploads/drafts", (route) =>
    route.fulfill({
      status: 201,
      json: {
        draft_id: "UPL-PRIVACY-FAIL-SYNTHETIC",
        status: "staged",
        created_at: createdAt,
        expires_at: "2026-09-28T00:00:00Z",
      },
    }),
  );
  await page.route(
    "**/api/uploads/drafts/UPL-PRIVACY-FAIL-SYNTHETIC/finalize",
    (route) =>
      route.fulfill({
        status: 202,
        json: {
          session_id: "MDS-PRIVACY-FAIL-SYNTHETIC",
          case_id: "CASE-PRIVACY-FAIL-SYNTHETIC",
          status: "queued",
        },
      }),
  );
  await page.route("**/api/sessions/MDS-PRIVACY-FAIL-SYNTHETIC", (route) =>
    route.fulfill({
      json: {
        session_id: "MDS-PRIVACY-FAIL-SYNTHETIC",
        case_id: "CASE-PRIVACY-FAIL-SYNTHETIC",
        privacy_method: "metadata-scrub",
        privacy_methods: ["metadata-scrub"],
        status: "completed",
        current_stage: "complete",
        created_at: createdAt,
        completed_at: createdAt,
        error_message: null,
        progress: {
          total_recordings: 2,
          finished_recordings: 2,
          completed_recordings: 2,
          failed_recordings: 0,
          percent: 100,
        },
        summary: { model_alert_recordings: 0 },
        recordings: [],
      },
    }),
  );
  await page.route(
    "**/api/cases/CASE-PRIVACY-FAIL-SYNTHETIC/patient-profile**",
    (route) =>
      route.fulfill({
        json: {
          profile: {
            name: "",
            hospital_id: "",
            age: "",
            findings: "",
            details: [{ label: "Findings", value: "Synthetic finding." }],
            reviewed: false,
            verification_status: "auto_extracted",
            reviewed_at: null,
          },
        },
      }),
  );
  await page.route("**/api/video-detection/jobs", (route) => {
    if (route.request().method() !== "POST")
      return route.fulfill({ json: { jobs: detectionJobs } });
    detectionPosts += 1;
    const index = detectionJobs.length + 1;
    const job = {
      job_id: `VID-PRIVACY-FAIL-SYNTHETIC-${index}`,
      case_id: "CASE-PRIVACY-FAIL-SYNTHETIC",
      label: `Video ${index}`,
      status: "queued",
      current_stage: "preflight",
      duration_seconds: 10,
      fps: 30,
      created_at: createdAt,
      retention_expires_at: "2026-09-28T00:00:00Z",
      video_available: false,
      error: null,
    };
    detectionJobs.push(job);
    return route.fulfill({ status: 202, json: { job } });
  });
  await page.route(
    "**/api/video-detection/jobs/VID-PRIVACY-FAIL-SYNTHETIC-*",
    (route) => {
      const jobId = new URL(route.request().url()).pathname.split("/").at(-1);
      const job = detectionJobs.find((candidate) => candidate.job_id === jobId);
      if (!job)
        return route.fulfill({ status: 404, json: { detail: "Not found." } });
      job.status = "failed";
      job.current_stage = "failed";
      job.error =
        "The video could not be face-redacted safely. No detection result was published.";
      return route.fulfill({ json: { job } });
    },
  );

  const scratch = process.env.TMPDIR;
  if (!scratch)
    throw new Error("TMPDIR is required for isolated browser fixtures.");
  const folder = mkdtempSync(
    join(scratch, "mds01-video-privacy-failure-test-"),
  );
  try {
    writeFileSync(join(folder, "recording-one.e"), "synthetic-eeg-one");
    writeFileSync(join(folder, "recording-two.e"), "synthetic-eeg-two");
    writeFileSync(join(folder, "report.doc"), "synthetic-report");
    writeFileSync(join(folder, "clip-one.avi"), "synthetic-video-one");
    writeFileSync(join(folder, "clip-two.avi"), "synthetic-video-two");
    await page.goto("/upload");
    await page
      .locator('input[type="file"][webkitdirectory]')
      .setInputFiles(folder);
    await page.getByRole("button", { name: "Start processing" }).click();

    await expect(
      page.getByRole("heading", { name: "Processing finished with issues" }),
    ).toBeVisible();
    const videoProgress = page.getByRole("region", {
      name: "Video processing",
    });
    await expect(videoProgress.getByRole("alert")).toHaveCount(2);
    await expect(
      videoProgress.getByText(/privacy transform could not be validated/i),
    ).toHaveCount(2);
    await expect(page.getByText(/clip-one\.avi|clip-two\.avi/)).toHaveCount(0);
    expect(detectionPosts).toBe(2);
    expect(predictionRequests).toBe(0);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});
