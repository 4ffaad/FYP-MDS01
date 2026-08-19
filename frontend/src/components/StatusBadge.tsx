import { Icon } from "./Icon";
import type { JobStatus } from "@/lib/types";

const statusConfig: Record<JobStatus, { label: string; icon: "clock" | "spinner" | "check" | "alert"; className: string }> = {
  queued: { label: "Queued", icon: "clock", className: "border-rule-strong bg-surface-muted text-ink-muted" },
  processing: { label: "Processing", icon: "spinner", className: "border-cyan/40 bg-cyan-soft text-teal-dark" },
  complete: { label: "Complete", icon: "check", className: "border-teal/30 bg-teal-soft text-teal-dark" },
  failed: { label: "Needs review", icon: "alert", className: "border-red/30 bg-red-soft text-red" },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const config = statusConfig[status];
  return (
    <span className={`inline-flex min-h-7 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${config.className}`} role="status" aria-label={`Status: ${config.label}`}>
      <Icon name={config.icon} className="size-3.5" />
      <span>{config.label}</span>
    </span>
  );
}
