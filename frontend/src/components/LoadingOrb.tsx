"use client";

import { ThinkingOrb, type OrbSize, type OrbState } from "thinking-orbs";

export function LoadingOrb({
  label,
  state = "working",
  size = 64,
  className = "",
}: {
  label: string;
  state?: OrbState;
  size?: OrbSize;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center gap-3 ${className}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <ThinkingOrb state={state} size={size} theme="light" aria-hidden="true" />
      <span className="text-sm font-medium text-ink">{label}</span>
    </div>
  );
}
