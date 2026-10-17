import { deleteJson, getJson, postJson } from "@/lib/api";

export const CLINICAL_OBSERVATION_TYPES = [
  "left_arm_movement",
  "right_arm_movement",
  "left_leg_movement",
  "right_leg_movement",
  "bilateral_movement",
  "head_or_eye_deviation",
  "other_observed_behavior",
  "uncertain_or_unobservable",
] as const;

export type ClinicalObservationType =
  (typeof CLINICAL_OBSERVATION_TYPES)[number];

export interface ClinicalAnnotation {
  annotation_id: string;
  provenance: "clinician_observation";
  annotator: string;
  created_at: string;
  start_seconds: number;
  end_seconds: number;
  observations: ClinicalObservationType[];
  description: string;
}

export interface ClinicalAnnotationDraft {
  start_seconds: number;
  end_seconds: number;
  observations: ClinicalObservationType[];
  description: string;
}

const pathFor = (recordId: string) =>
  `/api/recordings/${encodeURIComponent(recordId)}/clinical-annotations`;

export async function listClinicalAnnotations(
  recordId: string,
  signal?: AbortSignal,
): Promise<ClinicalAnnotation[]> {
  const response = await getJson<{ annotations: ClinicalAnnotation[] }>(
    pathFor(recordId),
    signal,
  );
  return response.annotations;
}

export async function createClinicalAnnotation(
  recordId: string,
  draft: ClinicalAnnotationDraft,
): Promise<ClinicalAnnotation> {
  const response = await postJson<{
    annotation: ClinicalAnnotation;
  }>(pathFor(recordId), draft);
  return response.annotation;
}

export async function deleteClinicalAnnotation(
  recordId: string,
  annotationId: string,
): Promise<void> {
  await deleteJson(`${pathFor(recordId)}/${encodeURIComponent(annotationId)}`);
}
