type Mds01LogoProps = {
  context?: "workspace" | "eeg" | "video" | "detection";
};

/** Render the MDS01 monogram and research workspace wordmark. */
export function Mds01Logo({ context = "eeg" }: Mds01LogoProps) {
  return (
    <span className="logo-link group/logo inline-flex min-w-0 items-center gap-3">
      <svg
        className="logo-mark size-10 shrink-0"
        viewBox="0 0 40 40"
        fill="none"
        role="img"
        aria-label="MDS01 VEEG signal mark"
      >
        <path
          d="M5.5 22.5c5.2 0 5.2-10.5 10.3-10.5 5.2 0 5.2 17.2 10.4 17.2 5.1 0 5.1-10.7 8.3-10.7"
          stroke="#111318"
          strokeWidth="4.6"
          strokeLinecap="round"
        />
        <circle cx="5.5" cy="22.5" r="3.15" fill="#1473e6" />
        <circle cx="34.5" cy="18.5" r="3.15" fill="#1473e6" />
      </svg>
      <span className="min-w-0 leading-none">
        <span className="block text-[1rem] font-bold tracking-[-0.04em] text-ink">
          MDS<span className="text-teal">01</span>
        </span>
        <span className="mt-1 block truncate text-[0.57rem] font-semibold uppercase tracking-[0.14em] text-ink-faint">
          {context === "detection"
            ? "Video Detection"
            : context === "video"
              ? "Video Privacy"
              : context === "workspace"
                ? "Analysis Workspace"
                : "VEEG Research"}
        </span>
      </span>
    </span>
  );
}
