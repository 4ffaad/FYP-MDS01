const SUBMITTED_AT_FORMATTER = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatSubmittedAt(value: string): string {
  return SUBMITTED_AT_FORMATTER.format(new Date(value));
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatRelativeTime(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "—";
  const roundedTenths = Math.round(value * 10);
  const wholeSeconds = Math.floor(roundedTenths / 10);
  const tenths = roundedTenths % 10;
  const seconds = wholeSeconds % 60;
  const minutes = Math.floor(wholeSeconds / 60);
  const hours = Math.floor(minutes / 60);
  const minuteRemainder = minutes % 60;
  const base =
    hours > 0
      ? `${hours}:${String(minuteRemainder).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
      : `${minutes}:${String(seconds).padStart(2, "0")}`;
  return tenths > 0 ? `${base}.${tenths}` : base;
}
