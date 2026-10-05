import type { PatientProfile, PatientProfileDetail } from "@/lib/types";

const NAME_LABELS = new Set(["name", "patient name", "full name"]);
const PROFILE_FIELD_LABELS = {
  name: NAME_LABELS,
  hospitalId: new Set(["hospital id", "hospital identifier", "hospital no"]),
  age: new Set(["age"]),
  findings: new Set([
    "report findings",
    "findings",
    "conclusion",
    "conclusions",
    "impression",
  ]),
} as const;
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
  patientRecording: PatientProfileDetail[];
  interictal: PatientProfileDetail[];
  ictal: PatientProfileDetail[];
  attacks: PatientProfileDetail[];
  findings: PatientProfileDetail[];
  conclusion: PatientProfileDetail[];
  reportSignoff: PatientProfileDetail[];
  other: PatientProfileDetail[];
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
  const details =
    profile.details?.filter(
      (detail) => detail.label.trim() && detail.value.trim(),
    ) ?? [];
  const fields = [
    { key: "name", label: "Name", value: profile.name },
    { key: "hospitalId", label: "Hospital ID", value: profile.hospitalId },
    { key: "age", label: "Age", value: profile.age },
    { key: "findings", label: "Report findings", value: profile.findings },
  ] as const;
  const normalizedValue = (value: string) =>
    value.trim().replace(/\s+/g, " ").toLocaleLowerCase("en-US");
  const missingProfileFields = fields.filter(({ key, value }) => {
    if (!value.trim()) return false;
    const normalized = normalizedValue(value);
    return !details.some(
      (detail) =>
        PROFILE_FIELD_LABELS[key].has(normalizedLabel(detail.label)) &&
        normalizedValue(detail.value) === normalized,
    );
  });
  return [
    ...details,
    ...missingProfileFields.map(({ label, value }) => ({ label, value })),
  ];
}

export function patientDisplayName(
  profile: PatientProfile | null,
  apiName: string | null | undefined,
  fallback = "Patient review",
): string {
  if (profile?.name.trim() && !containsPrivateValue(profile.name))
    return profile.name.trim();
  const detailName = profile
    ? patientProfileDetails(profile).find((detail) =>
        NAME_LABELS.has(normalizedLabel(detail.label)),
      )?.value
    : null;
  const candidate = detailName?.trim() || apiName?.trim() || "";
  return candidate && !containsPrivateValue(candidate) ? candidate : fallback;
}

export function reportDetails(
  profile: PatientProfile | null,
): PatientReportDetailGroups {
  const groups: PatientReportDetailGroups = {
    patientRecording: [],
    interictal: [],
    ictal: [],
    attacks: [],
    findings: [],
    conclusion: [],
    reportSignoff: [],
    other: [],
  };
  if (!profile) return groups;

  for (const detail of patientProfileDetails(profile)) {
    const label = normalizedLabel(detail.label);
    if (!label) continue;
    if (label.includes("interictal")) groups.interictal.push(detail);
    else if (label.includes("ictal")) groups.ictal.push(detail);
    else if (CONCLUSION_LABELS.has(label)) groups.conclusion.push(detail);
    else if (
      EVENT_LABELS.has(label) ||
      /\b(?:attack|event|seizure)s?\b/.test(label)
    ) {
      groups.attacks.push(detail);
    } else if (TECHNICAL_LABELS.has(label)) groups.findings.push(detail);
    else if (
      /\b(?:specialist|consultant|report date|sign.?off)\b/.test(label)
    ) {
      groups.reportSignoff.push(detail);
    } else if (
      /\b(?:patient|recording|eeg|test|diagnosis|hospital|institution|medical record|mrn|ic|age|sex|gender|race|physician|technologist|dominance|date|time)\b/.test(
        label,
      ) ||
      NAME_LABELS.has(label) ||
      PROFILE_FIELD_LABELS.hospitalId.has(label) ||
      PROFILE_FIELD_LABELS.age.has(label)
    ) {
      groups.patientRecording.push(detail);
    } else groups.other.push(detail);
  }
  return groups;
}
