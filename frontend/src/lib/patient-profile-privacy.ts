import type { PatientProfile, PatientProfileDetail } from "@/lib/types";

const NAME_LABELS = new Set(["name", "patient name", "full name"]);
const PRIVATE_LABEL =
  /\b(address|phone|telephone|mobile|contact|email|mrn|medical record|record number|hospital|organization|institution|clinic|department|national id|patient id|id number|ic number|ssn|date of birth|dob|birth date|passport|ward|location|specialist|physician|operator)\b/i;
const PRIVATE_VALUE =
  /(?:@|\b(?:phone|telephone|mobile|address|street|road|avenue|postcode|postal code|zip|unit|block|apartment|suite|district|city|town|jalan|jln|taman|kampung)\b)/i;
const PRIVATE_ID_VALUE = /\b[A-Z]*\d{6,}\b|\b\d{6,}[-/.]\d{1,}[-/.]?\d*\b/i;
const PRIVATE_PHONE_VALUE = /\+?\d[\d(). -]{7,}\d/;
const DATE_LABEL = /\b(date|time)\b/i;
const DATE_VALUE =
  /^\s*\d{1,4}[./-]\d{1,2}[./-]\d{2,4}(?:\s+\d{1,2}[.:]\d{2}(?::\d{2})?\s*(?:AM|PM)?)?\s*$/i;
const TECHNICAL_LABELS = new Set([
  "technical summary",
  "technical findings",
  "technical description",
  "eeg findings",
  "findings",
  "report findings",
]);
const EVENT_LABELS = new Set([
  "event",
  "events",
  "event description",
  "clinical events",
  "recorded events",
  "seizure description",
  "seizure events",
  "attack description",
]);
const CONCLUSION_LABELS = new Set([
  "conclusion",
  "conclusions",
  "impression",
  "clinical conclusion",
]);

export type PatientReportDetailGroups = {
  technical: PatientProfileDetail[];
  events: PatientProfileDetail[];
  conclusion: PatientProfileDetail[];
  additional: PatientProfileDetail[];
};

export function normalizedLabel(label: string): string {
  return label
    .trim()
    .toLocaleLowerCase("en-US")
    .replace(/[’']/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function containsPrivateValue(value: string, label = ""): boolean {
  return (
    PRIVATE_VALUE.test(value) ||
    PRIVATE_ID_VALUE.test(value) ||
    (PRIVATE_PHONE_VALUE.test(value) &&
      !(DATE_LABEL.test(label) && DATE_VALUE.test(value)))
  );
}

function patientProfileDetails(
  profile: PatientProfile,
): PatientProfileDetail[] {
  const details = profile.details?.filter(
    (detail) => detail.label.trim() && detail.value.trim(),
  );
  if (details?.length) return details;

  return [
    { label: "Name", value: profile.name },
    { label: "Age", value: profile.age },
    { label: "Report findings", value: profile.findings },
  ].filter((detail) => detail.value.trim());
}

export function patientDisplayName(
  profile: PatientProfile | null,
  apiName: string | null | undefined,
): string {
  if (profile?.name.trim() && !containsPrivateValue(profile.name))
    return profile.name.trim();
  const detailName = profile
    ? patientProfileDetails(profile).find((detail) =>
        NAME_LABELS.has(normalizedLabel(detail.label)),
      )?.value
    : null;
  const candidate = detailName?.trim() || apiName?.trim() || "";
  return candidate && !containsPrivateValue(candidate)
    ? candidate
    : "Patient review";
}

export function reportDetails(
  profile: PatientProfile | null,
): PatientReportDetailGroups {
  const groups: PatientReportDetailGroups = {
    technical: [],
    events: [],
    conclusion: [],
    additional: [],
  };
  if (!profile) return groups;

  for (const detail of patientProfileDetails(profile)) {
    const label = normalizedLabel(detail.label);
    if (
      !label ||
      PRIVATE_LABEL.test(label) ||
      containsPrivateValue(detail.value, label) ||
      NAME_LABELS.has(label)
    )
      continue;
    if (TECHNICAL_LABELS.has(label)) groups.technical.push(detail);
    else if (EVENT_LABELS.has(label)) groups.events.push(detail);
    else if (CONCLUSION_LABELS.has(label)) groups.conclusion.push(detail);
    else groups.additional.push(detail);
  }
  return groups;
}
