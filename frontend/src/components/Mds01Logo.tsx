import { Icon } from "./Icon";

type Mds01LogoProps = {
  compact?: boolean;
};

/** Render the MDS01 wordmark and restrained EEG waveform mark. */
export function Mds01Logo({ compact = false }: Mds01LogoProps) {
  return (
    <span className="inline-flex min-w-0 items-center gap-3">
      <span className="grid size-9 shrink-0 place-items-center rounded-[0.65rem] bg-ink text-white shadow-sm" aria-hidden="true">
        <Icon name="activity" className="size-[1.1rem]" weight="bold" />
      </span>
      <span className="min-w-0 leading-none">
        <span className="block text-[0.94rem] font-bold tracking-[-0.035em] text-ink">MDS01</span>
        {!compact && <span className="mt-1 block truncate text-[0.58rem] font-semibold uppercase tracking-[0.16em] text-ink-faint">EEG Research Review</span>}
      </span>
    </span>
  );
}
