import type { PatientProfileDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";

export interface PatientDetailDraft extends PatientProfileDetail {
  id: string;
  included: boolean;
  manual?: boolean;
}

export function PatientDetailsEditor({
  fields,
  truncated,
  readOnly,
  onToggle,
  onChange,
  onAddManualField,
  onRemoveManualField,
}: {
  fields: PatientDetailDraft[];
  truncated: boolean;
  readOnly: boolean;
  onToggle: (id: string, included: boolean) => void;
  onChange: (id: string, key: "label" | "value", value: string) => void;
  onAddManualField: () => void;
  onRemoveManualField: (id: string) => void;
}) {
  const includedFields = fields.filter(
    (field) => field.included && field.label.trim() && field.value.trim(),
  );
  const completeFieldCount = fields.filter(
    (field) => field.label.trim() && field.value.trim(),
  ).length;

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
            {includedFields.length} field
            {includedFields.length === 1 ? "" : "s"} selected
          </span>
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
          Review extracted details and opt in to each value you want saved with
          this case. Unchecked details are not sent.
        </p>
      </header>

      <div className="p-5 sm:p-7">
        {fields.length === 0 ? (
          <div className="border-y border-rule py-4">
            <p className="text-sm text-ink-muted" role="status">
              No report details were extracted. Add only the details you approve
              for this case.
            </p>
            <Button
              type="button"
              variant="outline"
              className="mt-4"
              disabled={readOnly}
              onClick={onAddManualField}
            >
              Add approved detail
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-rule border-y border-rule">
            {fields.map((field, index) => (
              <div
                key={field.id}
                className="grid gap-3 py-4 sm:grid-cols-[minmax(9rem,0.32fr)_minmax(0,1fr)] sm:gap-6"
              >
                {field.manual ? (
                  <div className="grid gap-2 self-start">
                    <label className="text-xs font-semibold text-ink-muted">
                      Detail name
                      <input
                        className="mt-1 min-h-10 w-full rounded-lg border border-rule bg-white px-3 text-sm text-ink"
                        aria-label={`Report field name ${index + 1}`}
                        value={field.label}
                        disabled={readOnly}
                        onChange={(event) =>
                          onChange(field.id, "label", event.target.value)
                        }
                      />
                    </label>
                    <label className="text-xs font-semibold text-ink-muted">
                      Detail value
                      <textarea
                        className="mt-1 min-h-24 w-full rounded-lg border border-rule bg-white px-3 py-2 text-sm leading-6 text-ink"
                        aria-label={`Report field value ${index + 1}`}
                        value={field.value}
                        disabled={readOnly}
                        onChange={(event) =>
                          onChange(field.id, "value", event.target.value)
                        }
                      />
                    </label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={readOnly}
                      onClick={() => onRemoveManualField(field.id)}
                    >
                      Remove detail
                    </Button>
                  </div>
                ) : (
                  <>
                    <dt className="break-words text-xs font-semibold text-ink-muted">
                      {field.label}
                    </dt>
                    <dd className="min-w-0 break-words whitespace-pre-wrap text-sm leading-6 text-ink">
                      {field.value}
                    </dd>
                  </>
                )}
                <label className="flex min-h-10 items-center gap-2 text-xs font-semibold text-ink-muted sm:col-span-2">
                  <input
                    className="size-4 accent-teal"
                    type="checkbox"
                    aria-label={`Include detail ${field.label.trim() || index + 1}`}
                    checked={field.included}
                    disabled={
                      readOnly || !field.label.trim() || !field.value.trim()
                    }
                    onChange={(event) =>
                      onToggle(field.id, event.target.checked)
                    }
                  />
                  Include this detail in the case
                </label>
              </div>
            ))}
          </div>
        )}
        {completeFieldCount > 0 && (
          <p className="mt-3 text-xs text-ink-muted" aria-live="polite">
            {includedFields.length} of {completeFieldCount} complete fields
            selected.
          </p>
        )}

        {truncated && (
          <div className="mt-4 border-l-2 border-amber bg-amber-soft/40 px-4 py-3">
            <p className="text-xs leading-5 text-ink-muted" role="status">
              Some source text exceeded the extraction limit and is not included
              above. Attach a PDF on the case page to retain the complete source
              document.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
