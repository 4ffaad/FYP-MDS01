import type { CaseSummary } from "@/lib/types";

export function CaseStatusBadge({ status }: { status: CaseSummary["status"] }) {
  const appearance = {
    processing: "bg-teal-soft text-teal-dark",
    complete: "bg-surface-muted text-ink",
    needs_review: "bg-amber-soft text-ink",
  }[status];
  const label = {
    processing: "Processing",
    complete: "Complete",
    needs_review: "Needs review",
  }[status];

  return (
    <span
      className={`rounded-full border border-rule px-2.5 py-1 text-xs font-semibold ${appearance}`}
    >
      {label}
    </span>
  );
}
