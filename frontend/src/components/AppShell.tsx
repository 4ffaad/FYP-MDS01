"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuList,
} from "@/components/ui/navigation-menu";
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
      <a className="skip-link" href="#main-content">Skip to main content</a>

      <header className="relative z-40 shrink-0 border-b border-rule bg-surface">
        <div className="site-container grid min-h-[4.25rem] grid-cols-[auto_1fr_auto] items-center gap-5">
          <Link
            className="inline-flex min-h-11 min-w-0 items-center rounded-lg focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2"
            href="/dashboard"
            aria-label={isVideoPrivacy ? "MDS01 video privacy" : "MDS01 EEG analysis"}
            onClick={() => setMenuOpen(false)}
          >
            <Mds01Logo context={isVideoPrivacy ? "video" : "eeg"} />
          </Link>

          <NavigationMenu
            aria-label="Primary navigation"
            viewport={false}
            className="hidden justify-self-center lg:flex"
          >
            <NavigationMenuList className="gap-1">
              <NavigationMenuItem>
                <NavLink href="/dashboard">
                  <Icon name="activity" className="size-4" />
                  EEG analysis
                </NavLink>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavLink href="/upload">
                  <Icon name="upload" className="size-4" />
                  New EEG analysis
                </NavLink>
              </NavigationMenuItem>
              <NavigationMenuItem className="ml-1 border-l border-rule pl-2">
                <NavLink href="/video-privacy">
                  <Icon name="shield" className="size-4" />
                  Video privacy
                </NavLink>
              </NavigationMenuItem>
            </NavigationMenuList>
          </NavigationMenu>

          <div className="flex items-center justify-self-end gap-2">
            <div className="hidden items-center gap-2 text-xs font-medium text-ink-muted xl:flex">
              <Icon name={isVideoPrivacy ? "shield" : "activity"} className="size-4 text-teal" />
              <span>{isVideoPrivacy ? "Video privacy workspace" : "EEG analysis workspace"}</span>
            </div>
            <span className="hidden min-h-7 items-center gap-1.5 rounded-full border border-rule-strong bg-surface-soft px-2.5 text-[0.64rem] font-bold uppercase tracking-[0.1em] text-ink-muted md:inline-flex">
              <span className="size-1.5 rounded-full bg-teal" aria-hidden="true" />
              Development
            </span>
            <Button
              variant="outline"
              size="icon-lg"
              className="size-11 rounded-lg border-rule-strong bg-surface lg:hidden"
              type="button"
              aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              onClick={() => setMenuOpen((open) => !open)}
            >
              <Icon name={menuOpen ? "close" : "menu"} className="size-5" weight="bold" />
            </Button>
          </div>

          <nav
            id="mobile-navigation"
            className={menuOpen ? "col-span-3 flex w-full flex-col gap-1 border-t border-rule py-3 lg:hidden" : "hidden"}
            aria-label="Primary navigation"
          >
            <NavLink href="/dashboard" onNavigate={() => setMenuOpen(false)}>
              <Icon name="activity" className="size-4" />
              EEG analysis
            </NavLink>
            <NavLink href="/upload" onNavigate={() => setMenuOpen(false)}>
              <Icon name="upload" className="size-4" />
              New EEG analysis
            </NavLink>
            <NavLink href="/video-privacy" onNavigate={() => setMenuOpen(false)}>
              <Icon name="shield" className="size-4" />
              Video privacy
            </NavLink>
          </nav>
        </div>
      </header>

      <main id="main-content" className="flex-1" tabIndex={-1}>{children}</main>

      <footer className="mt-auto shrink-0 border-t border-rule bg-surface-muted">
        <div className="site-container grid gap-6 py-7 text-xs leading-5 text-ink-muted sm:grid-cols-2">
          <div className="flex gap-3">
            <Icon name="lock" className="mt-0.5 size-4 shrink-0 text-teal" />
            <p><span className="font-semibold text-ink">Protected data handling.</span> Original uploads are encrypted at rest and are not exposed through this interface.</p>
          </div>
          <div className="flex gap-3 sm:justify-self-end sm:text-right">
            <Icon name="info" className="mt-0.5 size-4 shrink-0 text-amber sm:order-2" />
            <p><span className="font-semibold text-ink">MDS01 Project Group.</span> {isVideoPrivacy ? "Research privacy transform; anonymity is not guaranteed." : "Research prototype; model output is not a diagnosis."}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
