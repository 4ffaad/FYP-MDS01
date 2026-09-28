import type { PatientProfileDetail } from "./types";

export interface PatientReportDraft {
  details: PatientProfileDetail[];
  truncated: boolean;
}

const MAX_DETAIL_COUNT = 80;
const MAX_DETAIL_LABEL = 80;
const MAX_DETAIL_VALUE = 6_000;
const MAX_DETAIL_TOTAL = 25_000;
const FIELD_SEPARATOR = /[:：\t]/;
const LABEL_PATTERN = /^[A-Za-z][A-Za-z0-9 ._()/-]{0,79}$/;
const KNOWN_LABELS = [
  "patient name",
  "technical summary",
  "technical findings",
  "technical description",
  "event description",
  "clinical events",
  "recorded events",
  "seizure description",
  "seizure events",
  "attack description",
  "specialist names",
  "specialist name",
  "medical record number",
  "medical record no.",
  "medical record id",
  "hospital number",
  "hospital no.",
  "hospital id",
  "date of birth",
  "clinical history",
  "report number",
  "report date",
  "interpretation",
  "recommendations",
  "medications",
  "medication",
  "findings",
  "results",
  "impression",
  "conclusion",
  "conclusions",
  "event",
  "events",
  "attack",
  "attacks",
  "diagnosis",
  "physician",
  "treatment",
  "national id",
  "gender",
  "patient age",
  "sex",
  "dob",
  "age",
  "mrn",
  "name",
  "plan",
];
const KNOWN_LABEL_PATTERN = new RegExp(
  `(?:^|\\s)(${KNOWN_LABELS.sort((left, right) => right.length - left.length)
    .map((label) =>
      label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replaceAll(" ", "\\s+"),
    )
    .join("|")})\\s*[:：\\t-]\\s*`,
  "gi",
);
const BARE_KNOWN_LABEL_PATTERN = new RegExp(
  `^\\s*(${KNOWN_LABELS.sort((left, right) => right.length - left.length)
    .map((label) =>
      label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replaceAll(" ", "\\s+"),
    )
    .join("|")})\\s*$`,
  "i",
);

function parseInlineKnownFields(line: string): PatientProfileDetail[] {
  const matches = [...line.matchAll(KNOWN_LABEL_PATTERN)];
  if (matches.length === 0) return [];
  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length;
    const end = matches[index + 1]?.index ?? line.length;
    const label = (match[1] ?? "").trim();
    return { label, value: line.slice(start, end).trim() };
  });
}

/** Extracts visible report fields as editable drafts; it never approves or stores them. */
export function extractPatientReportDraft(text: string): PatientReportDraft {
  const lines = text
    .replace(/\u0000/g, "")
    .replace(/\r\n?|\u2028|\u2029|\f/g, "\n")
    .split("\n");
  const parsed: PatientProfileDetail[] = [];
  let activeLabel = "";
  let activeValue: string[] = [];
  let unlabelled: string[] = [];
  const finishActive = () => {
    const value = activeValue.join("\n").trim();
    if (activeLabel && value) parsed.push({ label: activeLabel, value });
    activeLabel = "";
    activeValue = [];
  };
  const finishUnlabelled = () => {
    const value = unlabelled.join("\n").trim();
    if (value) parsed.push({ label: "Report text", value });
    unlabelled = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      if (activeLabel) activeValue.push("");
      else if (unlabelled.length) unlabelled.push("");
      continue;
    }

    const inlineFields = parseInlineKnownFields(line);
    if (inlineFields.length) {
      finishActive();
      finishUnlabelled();
      for (const field of inlineFields.slice(0, -1)) {
        if (field.value) parsed.push(field);
      }
      const last = inlineFields[inlineFields.length - 1];
      activeLabel = last.label;
      activeValue = last.value ? [last.value] : [];
      continue;
    }

    const separator = line.search(FIELD_SEPARATOR);
    if (separator > 0) {
      const label = line.slice(0, separator).trim();
      if (LABEL_PATTERN.test(label)) {
        finishActive();
        finishUnlabelled();
        activeLabel = label;
        activeValue = [line.slice(separator + 1).trim()];
        continue;
      }
    }

    const bareLabel = line.match(BARE_KNOWN_LABEL_PATTERN)?.[1]?.trim();
    if (bareLabel) {
      finishActive();
      finishUnlabelled();
      activeLabel = bareLabel;
      activeValue = [];
      continue;
    }

    if (activeLabel) activeValue.push(line);
    else unlabelled.push(line);
  }
  finishActive();
  finishUnlabelled();

  const details: PatientProfileDetail[] = [];
  let totalChars = 0;
  let truncated = false;
  for (const detail of parsed) {
    const label = detail.label.trim().slice(0, MAX_DETAIL_LABEL);
    const value = detail.value.trim();
    if (value.length > MAX_DETAIL_VALUE) truncated = true;
    const boundedValue = value.slice(0, MAX_DETAIL_VALUE);
    const fieldChars = label.length + boundedValue.length;
    if (
      details.length >= MAX_DETAIL_COUNT ||
      totalChars + fieldChars > MAX_DETAIL_TOTAL
    ) {
      truncated = true;
      break;
    }
    if (!label || !boundedValue) continue;
    details.push({ label, value: boundedValue });
    totalChars += fieldChars;
  }

  return { details, truncated };
}
