import { Icon } from "./Icon";
import type { DisplayStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const statusConfig: Record<
  DisplayStatus,
  {
    label: string;
    icon: "clock" | "spinner" | "check" | "alert";
    className: string;
  }
> = {
  queued: {
    label: "Queued",
    icon: "clock",
    className: "border-rule-strong bg-surface-muted text-ink-muted",
  },
  processing: {
    label: "Processing",
    icon: "spinner",
    className: "border-cyan/40 bg-cyan-soft text-teal-dark",
  },
  complete: {
    label: "Complete",
    icon: "check",
    className: "border-teal/30 bg-teal-soft text-teal-dark",
  },
  partial: {
    label: "Partial · review",
    icon: "alert",
    className: "border-amber/30 bg-amber-soft text-amber",
  },
  failed: {
    label: "Needs review",
    icon: "alert",
    className: "border-red/30 bg-red-soft text-red",
  },
};

export function StatusBadge({ status }: { status: DisplayStatus }) {
  const config = statusConfig[status];
  return (
    <Badge
      variant="outline"
      className={`min-h-7 rounded-full px-2.5 py-1 text-xs font-semibold ${config.className}`}
      aria-label={`Status: ${config.label}`}
    >
      <Icon
        name={config.icon}
        className={`size-3.5 ${status === "processing" ? "animate-spin" : ""}`}
      />
      <span>{config.label}</span>
    </Badge>
  );
}
