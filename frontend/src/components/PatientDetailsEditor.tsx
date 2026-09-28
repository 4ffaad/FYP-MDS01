import type { PatientProfileDetail } from "@/lib/types";

export interface PatientDetailDraft extends PatientProfileDetail {
  id: string;
}

export function PatientDetailsSummary({
  fields,
  truncated,
  reportMessage,
  reportReading,
}: {
  fields: PatientDetailDraft[];
  truncated: boolean;
  reportMessage: string | null;
  reportReading: boolean;
}) {
  const completeFields = fields.filter(
    (field) => field.label.trim() && field.value.trim(),
  );

  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="patient-details-heading"
    >
      <header className="border-b border-rule px-5 py-5 sm:px-7">
        <p className="eyebrow">Imported report</p>
        <div className="mt-2 flex flex-wrap items-baseline justify-between gap-3">
          <h2 id="patient-details-heading" className="text-lg font-bold">
            Patient details
          </h2>
          <span className="text-xs tabular-nums text-ink-muted">
            {completeFields.length} extracted field
            {completeFields.length === 1 ? "" : "s"}
          </span>
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
          All extracted values are saved to this case&apos;s encrypted,
          owner-only profile when processing starts. Automatically extracted
          details stay unverified until you review them on the case page.
        </p>
      </header>

      <div className="p-5 sm:p-7">
        {reportMessage ? (
          <div className="border-y border-rule py-4">
            <p className="text-sm text-ink-muted" role="status">
              {reportMessage}
            </p>
            {!reportReading && (
              <p className="mt-2 text-xs leading-5 text-ink-faint">
                EEG and video processing can continue without report details; no
                report values will be saved to this case.
              </p>
            )}
          </div>
        ) : completeFields.length > 0 ? (
          <details className="border-y border-rule">
            <summary className="cursor-pointer py-4 text-sm font-semibold text-ink">
              View extracted details
            </summary>
            <p className="pb-3 text-xs leading-5 text-ink-muted">
              Report details can contain sensitive identifiers. Review the
              source report before relying on these unverified values.
            </p>
            <dl className="divide-y divide-rule">
              {completeFields.map((field) => (
                <div
                  key={field.id}
                  className="grid gap-2 py-4 sm:grid-cols-[minmax(9rem,0.32fr)_minmax(0,1fr)] sm:gap-6"
                >
                  <dt className="break-words text-xs font-semibold text-ink-muted">
                    {field.label}
                  </dt>
                  <dd className="min-w-0 break-words whitespace-pre-wrap text-sm leading-6 text-ink">
                    {field.value}
                  </dd>
                </div>
              ))}
            </dl>
          </details>
        ) : (
          <p
            className="border-y border-rule py-4 text-sm text-ink-muted"
            role="status"
          >
            No patient details were extracted. EEG and video processing can
            still continue; add the patient name in Patient History if needed.
          </p>
        )}

        {truncated && (
          <div className="mt-4 border-l-2 border-amber bg-amber-soft/40 px-4 py-3">
            <p className="text-xs leading-5 text-ink-muted" role="status">
              Some source text exceeded the extraction limit. Only the fields
              shown above are included; review the complete report on the case
              page before relying on the profile.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
