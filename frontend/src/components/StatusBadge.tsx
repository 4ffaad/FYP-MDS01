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
    className: "border-rule bg-surface-muted text-ink",
  },
  processing: {
    label: "Processing",
    icon: "spinner",
    className: "border-rule bg-cyan-soft text-teal-dark",
  },
  complete: {
    label: "Complete",
    icon: "check",
    className: "border-rule bg-teal-soft text-teal-dark",
  },
  partial: {
    label: "Partial · review",
    icon: "alert",
    className: "border-rule bg-amber-soft text-ink",
  },
  failed: {
    label: "Needs review",
    icon: "alert",
    className: "border-rule bg-red-soft text-red",
  },
};

export function StatusBadge({ status }: { status: DisplayStatus }) {
  const config = statusConfig[status];
  return (
    <Badge
      variant="outline"
      className={`min-h-7 rounded-full border px-2.5 py-1 text-xs font-semibold ${config.className}`}
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
