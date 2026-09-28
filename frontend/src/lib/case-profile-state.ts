import type { PatientProfile } from "./types";

export interface PatientProfileLoad {
  caseId: string;
  profile: PatientProfile | null;
  error: string | null;
}

/** Hide profile results until they belong to the currently displayed case. */
export function profileLoadForCase(
  caseId: string,
  load: PatientProfileLoad | null,
): PatientProfileLoad | null {
  return load?.caseId === caseId ? load : null;
}
