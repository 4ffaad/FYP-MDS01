import Link from "next/link";
import type { ReactNode } from "react";
import { Icon } from "./Icon";
import { NavLink } from "./NavLink";

/** Provide the shared MDS01 workspace chrome and the persistent privacy boundary. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-rule bg-surface">
        <div className="mx-auto flex min-h-14 max-w-[1400px] flex-wrap items-center gap-x-8 gap-y-2 px-4 py-1 sm:px-8 lg:px-12">
          <Link className="inline-flex min-h-10 items-center gap-2.5" href="/upload" aria-label="MDS01 new analysis">
            <span className="grid size-8 place-items-center rounded-md bg-ink text-white" aria-hidden="true">
              <Icon name="activity" className="size-[1.05rem]" weight="bold" />
            </span>
            <span className="leading-none">
              <span className="block text-[0.92rem] font-bold tracking-[-0.03em]">MDS01</span>
              <span className="mt-1 block text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-ink-faint">EEG decision support</span>
            </span>
          </Link>

          <nav className="order-3 flex w-full items-center gap-1 sm:order-none sm:w-auto" aria-label="Primary navigation">
            <NavLink href="/upload"><Icon name="upload" className="size-4" />New analysis</NavLink>
            <NavLink href="/dashboard"><Icon name="list" className="size-4" />Dashboard</NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-[0.72rem] font-medium text-ink-muted md:inline-flex">
              <Icon name="shield" className="size-4 text-teal" />Private workspace
            </span>
            <span className="inline-flex min-h-7 items-center gap-1.5 rounded-full border border-rule-strong bg-surface px-2.5 text-[0.64rem] font-bold uppercase tracking-[0.1em] text-ink-muted">
              <span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Development
            </span>
          </div>
        </div>
      </header>

      <main>{children}</main>

      <footer className="border-t border-rule bg-surface-muted">
        <div className="mx-auto grid max-w-[1400px] gap-6 px-4 py-7 text-xs leading-5 text-ink-muted sm:grid-cols-2 sm:px-8 lg:px-12">
          <div className="flex gap-3">
            <Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" />
            <p><span className="font-semibold text-ink">Private by boundary.</span> Original uploads stay in protected session storage and are not rendered in this interface.</p>
          </div>
          <div className="flex gap-3 sm:justify-self-end sm:text-right">
            <Icon name="info" className="mt-0.5 size-4 shrink-0 text-amber sm:order-2" />
            <p><span className="font-semibold text-ink">Development output.</span> Predictions and overlays are non-clinical inspection aids.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
