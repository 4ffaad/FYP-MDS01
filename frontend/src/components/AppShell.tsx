"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import { Mds01Logo } from "./Mds01Logo";
import { NavLink } from "./NavLink";

/** Provide the shared MDS01 workspace chrome and persistent privacy boundary. */
export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const isVideoPrivacy = pathname.startsWith("/video-privacy");

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="relative z-40 shrink-0 border-b border-rule bg-surface">
        <div className="site-container flex min-h-[4.25rem] flex-wrap items-center gap-x-8">
          <Link
            className="inline-flex min-h-11 min-w-0 items-center rounded-lg focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2"
            href="/dashboard"
            aria-label={
              isVideoPrivacy ? "MDS01 video privacy" : "MDS01 EEG analysis"
            }
            onClick={() => setMenuOpen(false)}
          >
            <Mds01Logo context={isVideoPrivacy ? "video" : "eeg"} />
          </Link>

          <nav
            aria-label="Primary navigation"
            className="hidden items-center gap-1 lg:flex"
          >
            <NavLink href="/dashboard">
              <Icon name="activity" className="size-4" />
              EEG analysis
            </NavLink>
            <NavLink href="/video-privacy">
              <Icon name="shield" className="size-4" />
              Video privacy
            </NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-4">
            <span className="text-xs text-ink-faint">Research prototype</span>
            <Button
              variant="outline"
              size="icon-lg"
              className="size-11 rounded-lg border-rule-strong bg-surface lg:hidden"
              type="button"
              aria-label={
                menuOpen ? "Close navigation menu" : "Open navigation menu"
              }
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              onClick={() => setMenuOpen((open) => !open)}
            >
              <Icon
                name={menuOpen ? "close" : "menu"}
                className="size-5"
                weight="bold"
              />
            </Button>
          </div>

          <nav
            id="mobile-navigation"
            className={
              menuOpen
                ? "flex w-full flex-col gap-1 border-t border-rule py-3 lg:hidden"
                : "hidden"
            }
            aria-label="Primary navigation"
          >
            <NavLink href="/dashboard" onNavigate={() => setMenuOpen(false)}>
              <Icon name="activity" className="size-4" />
              EEG analysis
            </NavLink>
            <NavLink
              href="/video-privacy"
              onNavigate={() => setMenuOpen(false)}
            >
              <Icon name="shield" className="size-4" />
              Video privacy
            </NavLink>
          </nav>
        </div>
      </header>

      <main id="main-content" className="flex-1" tabIndex={-1}>
        {children}
      </main>

      <footer className="mt-auto shrink-0 border-t border-rule">
        <div className="site-container flex flex-col justify-between gap-2 py-5 text-xs leading-5 text-ink-faint sm:flex-row">
          <p>MDS01 · Research only</p>
          <p>
            {isVideoPrivacy
              ? "Privacy transforms do not guarantee anonymity."
              : "Model output is not a diagnosis."}{" "}
            Original uploads are never displayed.
          </p>
        </div>
      </footer>
    </div>
  );
}
