import Link from "next/link";

const WORKSPACES = {
  eeg: [
    { id: "upload", label: "New EEG analysis", href: "/upload/eeg" },
    {
      id: "reviews",
      label: "EEG reviews",
      href: "/upload/eeg?view=reviews",
    },
  ],
  video: [
    {
      id: "upload",
      label: "New video analysis",
      href: "/video-detection",
    },
    {
      id: "reviews",
      label: "Video reviews",
      href: "/video-detection?view=reviews",
    },
  ],
} as const;

/** Keep each modality's upload and past results together. */
export function ModalityWorkspaceTabs({
  modality,
  active,
}: {
  modality: keyof typeof WORKSPACES;
  active: "upload" | "reviews";
}) {
  return (
    <nav
      aria-label={`${modality.toUpperCase()} workspace`}
      className="mt-5 flex w-fit gap-1 rounded-xl border border-rule bg-surface-muted p-1"
    >
      {WORKSPACES[modality].map((tab) => (
        <Link
          key={tab.id}
          href={tab.href}
          aria-current={active === tab.id ? "page" : undefined}
          className={`inline-flex min-h-10 items-center rounded-lg px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal ${
            active === tab.id
              ? "bg-surface text-ink shadow-hard-sm"
              : "text-ink-muted hover:bg-surface-soft hover:text-ink"
          }`}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}
