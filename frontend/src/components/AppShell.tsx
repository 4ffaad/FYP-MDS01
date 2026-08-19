"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { Icon } from "./Icon";
import { NavLink } from "./NavLink";

/** Provide the shared MDS01 workspace chrome and the persistent privacy boundary. */
export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <header className="shrink-0 border-b border-rule bg-surface">
        <div className="mx-auto flex min-h-[4.5rem] max-w-[1200px] flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-8 lg:px-10 lg:py-2">
          <Link className="inline-flex min-h-11 min-w-0 items-center gap-2.5" href="/dashboard" aria-label="MDS01 EEG decision support dashboard" onClick={() => setMenuOpen(false)}>
            <span className="grid size-8 place-items-center rounded-md bg-ink text-white" aria-hidden="true">
              <Icon name="activity" className="size-[1.05rem]" weight="bold" />
            </span>
            <span className="leading-none">
              <span className="block text-[0.92rem] font-bold tracking-[-0.03em]">MDS01</span>
              <span className="mt-1 block text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-ink-faint">EEG decision support</span>
            </span>
          </Link>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-[0.72rem] font-medium text-ink-muted sm:inline-flex">
              <Icon name="shield" className="size-4 text-teal" />Private workspace
            </span>
            <span className="hidden min-h-7 items-center gap-1.5 rounded-full border border-rule-strong bg-surface-muted px-2.5 text-[0.64rem] font-bold uppercase tracking-[0.1em] text-ink-muted sm:inline-flex">
              <span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />Development
            </span>
            <button className="inline-grid size-11 place-items-center rounded-md border border-rule-strong bg-surface text-ink transition-colors hover:bg-surface-muted lg:hidden" type="button" aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"} aria-expanded={menuOpen} aria-controls="primary-navigation" onClick={() => setMenuOpen((open) => !open)}>
              <Icon name={menuOpen ? "close" : "menu"} className="size-5" weight="bold" />
            </button>
          </div>

          <nav id="primary-navigation" className={menuOpen ? "flex order-3 w-full flex-col gap-1 border-t border-rule pt-2 lg:order-none lg:flex lg:w-auto lg:flex-row lg:border-t-0 lg:pt-0" : "hidden order-3 w-full flex-col gap-1 border-t border-rule pt-2 lg:order-none lg:flex lg:w-auto lg:flex-row lg:border-t-0 lg:pt-0"} aria-label="Primary navigation">
            <NavLink href="/upload" onNavigate={() => setMenuOpen(false)}><Icon name="upload" className="size-4" />New analysis</NavLink>
            <NavLink href="/dashboard" onNavigate={() => setMenuOpen(false)}><Icon name="list" className="size-4" />Dashboard</NavLink>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="mt-auto shrink-0 border-t border-rule bg-surface-muted">
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
