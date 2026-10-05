"use client";

import Link from "next/link";
import { createContext, useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import { Mds01Logo } from "./Mds01Logo";
import { NavLink } from "./NavLink";
import { getCurrentUser, logoutAccount } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

export const WorkspaceUserContext = createContext<AuthUser | null>(null);

function WorkspaceNavigation({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Primary navigation" className="space-y-6">
      <div className="space-y-1.5">
        <p className="px-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">
          Workspace
        </p>
        <NavLink href="/dashboard" onNavigate={onNavigate}>
          <Icon name="activity" className="size-5" />
          Patient cases
        </NavLink>
        <NavLink href="/upload" exact onNavigate={onNavigate}>
          <Icon name="upload" className="size-5" />
          New patient review
        </NavLink>
      </div>

      <div className="space-y-1.5">
        <p className="px-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">
          EEG tools
        </p>
        <NavLink href="/upload/eeg" onNavigate={onNavigate}>
          <Icon name="activity" className="size-5" />
          EEG workspace
        </NavLink>
      </div>

      <div className="space-y-1.5">
        <p className="px-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">
          Video tools
        </p>
        <NavLink href="/video-detection" onNavigate={onNavigate}>
          <Icon name="video" className="size-5" />
          Video workspace
        </NavLink>
      </div>
    </nav>
  );
}

function WorkspaceAccount({
  user,
  loggingOut,
  onLogout,
}: {
  user: AuthUser;
  loggingOut: boolean;
  onLogout: () => void;
}) {
  const displayName = user.displayName?.trim() || "Workspace member";

  return (
    <div className="border-t border-rule pt-4">
      <div className="flex min-w-0 items-center gap-3">
        <span
          aria-hidden="true"
          className="grid size-10 shrink-0 place-items-center rounded-full bg-teal-soft text-sm font-semibold text-teal-dark"
        >
          {displayName.slice(0, 1).toUpperCase()}
        </span>
        <div className="min-w-0">
          <p
            className="truncate text-sm font-semibold text-ink"
            title={displayName}
          >
            {displayName}
          </p>
          <p className="truncate text-xs text-ink-muted" title={user.email}>
            {user.email}
          </p>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        type="button"
        className="mt-3 h-10 w-full justify-start px-3"
        onClick={onLogout}
        disabled={loggingOut}
      >
        {loggingOut ? "Signing out…" : "Sign out"}
      </Button>
    </div>
  );
}

/** Provide the shared MDS01 workspace chrome and persistent privacy boundary. */
export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [authStatus, setAuthStatus] = useState<
    "loading" | "authenticated" | "unauthenticated"
  >("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const isVideoDetection =
    pathname.startsWith("/video-detection") ||
    pathname.startsWith("/video-reviews");
  const isUpload = pathname === "/upload";
  const isDashboard = pathname.startsWith("/dashboard") || pathname === "/";
  const isLogin = pathname === "/login";
  const logoContext = isVideoDetection
    ? "detection"
    : isUpload
      ? "review"
      : isDashboard
        ? "workspace"
        : "eeg";
  const logoLabel = isVideoDetection
    ? "MDS01 video detection"
    : isUpload
      ? "MDS01 patient review"
      : isDashboard
        ? "MDS01 analysis workspace"
        : "MDS01 EEG analysis";

  useEffect(() => {
    let mounted = true;
    void getCurrentUser()
      .then((nextUser) => {
        if (!mounted) return;
        setUser(nextUser);
        setAuthStatus(nextUser ? "authenticated" : "unauthenticated");
        if (!nextUser && pathname !== "/login") router.replace("/login");
        if (nextUser && pathname === "/login") router.replace("/dashboard");
      })
      .catch(() => {
        if (!mounted) return;
        setUser(null);
        setAuthStatus("unauthenticated");
        if (pathname !== "/login") router.replace("/login");
      });
    return () => {
      mounted = false;
    };
  }, [pathname, router]);

  useEffect(() => {
    const redirectToLogin = () => {
      setUser(null);
      setAuthStatus("unauthenticated");
      if (pathname !== "/login") router.replace("/login");
    };
    window.addEventListener("mds01:auth-expired", redirectToLogin);
    return () =>
      window.removeEventListener("mds01:auth-expired", redirectToLogin);
  }, [pathname, router]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, []);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logoutAccount();
    } finally {
      setUser(null);
      setAuthStatus("unauthenticated");
      setLoggingOut(false);
      router.replace("/login");
    }
  }

  if (authStatus === "loading" && isLogin) {
    return (
      <main
        className="grid min-h-screen place-items-center bg-canvas px-6"
        aria-live="polite"
      >
        <p className="text-sm text-ink-muted">Checking workspace access…</p>
      </main>
    );
  }
  if (authStatus === "unauthenticated" && !isLogin) return null;
  if (authStatus === "authenticated" && isLogin) return null;
  if (isLogin) {
    return (
      <main className="min-h-screen bg-canvas" tabIndex={-1}>
        {children}
      </main>
    );
  }

  return (
    <WorkspaceUserContext.Provider value={user}>
      <div className="min-h-dvh bg-canvas text-ink lg:pl-64">
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>

        <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-rule bg-surface lg:flex">
          <div className="flex h-[4.5rem] items-center border-b border-rule px-6">
            <Link
              href="/dashboard"
              className="inline-flex min-h-11 items-center rounded-lg focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2"
              aria-label="MDS01 research workspace"
            >
              <Mds01Logo context="workspace" />
            </Link>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-6">
            <WorkspaceNavigation />
          </div>
          <div className="space-y-4 px-4 pb-4">
            <p className="rounded-xl border border-rule bg-amber-soft px-3 py-2.5 text-xs leading-5 text-ink">
              Research workspace. Model output is not a diagnosis.
            </p>
            {user && (
              <WorkspaceAccount
                user={user}
                loggingOut={loggingOut}
                onLogout={() => void handleLogout()}
              />
            )}
          </div>
        </aside>

        <div className="flex min-h-dvh min-w-0 flex-col">
          <header className="app-header lg:hidden">
            <div className="site-container flex min-h-16 items-center justify-between gap-3">
              <Link
                className="inline-flex min-h-11 min-w-0 items-center rounded-lg focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2"
                href="/dashboard"
                aria-label={logoLabel}
                onClick={() => setMenuOpen(false)}
              >
                <Mds01Logo context={logoContext} />
              </Link>
              <Button
                variant="outline"
                size="icon-lg"
                className="size-11 rounded-lg border-rule-strong bg-surface"
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
            <div
              id="mobile-navigation"
              className={
                menuOpen
                  ? "space-y-5 border-t border-rule bg-surface px-4 py-4"
                  : "hidden"
              }
            >
              <WorkspaceNavigation onNavigate={() => setMenuOpen(false)} />
              {user && (
                <WorkspaceAccount
                  user={user}
                  loggingOut={loggingOut}
                  onLogout={() => void handleLogout()}
                />
              )}
            </div>
          </header>

          <main id="main-content" className="min-w-0 flex-1" tabIndex={-1}>
            {authStatus === "authenticated" ? (
              children
            ) : (
              <div
                className="grid min-h-[50vh] place-items-center px-6"
                aria-live="polite"
              >
                <p className="text-sm text-ink-muted">
                  Checking workspace access…
                </p>
              </div>
            )}
          </main>

          <footer className="mt-auto shrink-0 border-t border-rule">
            <div className="site-container flex flex-col justify-between gap-2 py-5 text-xs leading-5 text-ink-faint sm:flex-row">
              <p>
                {isUpload ? "MDS01 · Patient review" : "MDS01 · Research only"}
              </p>
              <p>
                {isUpload
                  ? "One patient review can include every supported EEG recording and video clip."
                  : "Model output is not a diagnosis."}{" "}
                {isUpload
                  ? "Each modality keeps its own privacy treatment and evidence trail."
                  : isVideoDetection
                    ? "The redacted review video and predictions are encrypted, owner-only, and retained until expiry."
                    : "Original uploads are never displayed."}
              </p>
            </div>
          </footer>
        </div>
      </div>
    </WorkspaceUserContext.Provider>
  );
}
