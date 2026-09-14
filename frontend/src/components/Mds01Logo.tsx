type Mds01LogoProps = {
  context?: "workspace" | "eeg" | "video" | "detection";
};

/** Render the MDS01 monogram and research workspace wordmark. */
export function Mds01Logo({ context = "eeg" }: Mds01LogoProps) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2.5">
      <svg
        className="size-9 shrink-0"
        viewBox="0 0 36 36"
        fill="none"
        aria-hidden="true"
      >
        <rect x="1" y="1" width="34" height="34" rx="9" fill="#1D1D1F" />
        <path
          d="M9 25V11L18 21.5L27 11V25"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="min-w-0 leading-none">
        <span className="block text-[0.96rem] font-bold tracking-[-0.035em] text-ink">
          MDS<span className="text-teal">01</span>
        </span>
        <span className="mt-1 block truncate text-[0.57rem] font-semibold uppercase tracking-[0.13em] text-ink-faint">
          {context === "detection"
            ? "Video Detection"
            : context === "video"
              ? "Video Privacy"
              : context === "workspace"
                ? "Analysis Workspace"
                : "EEG Research"}
        </span>
      </span>
    </span>
  );
}
