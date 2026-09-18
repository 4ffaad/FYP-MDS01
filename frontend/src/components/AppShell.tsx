"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import { Mds01Logo } from "./Mds01Logo";
import { NavLink } from "./NavLink";
import { getCurrentUser, logoutAccount } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

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
  const isVideoPrivacy = pathname.startsWith("/video-privacy");
  const isVideoDetection = pathname.startsWith("/video-detection");
  const isDashboard = pathname.startsWith("/dashboard") || pathname === "/";
  const isLogin = pathname === "/login";

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
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="app-header">
        <div className="app-header-inner site-container flex flex-wrap items-center gap-x-8">
          <Link
            className="inline-flex min-h-11 min-w-0 items-center rounded-lg focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2"
            href="/dashboard"
            aria-label={
              isVideoDetection
                ? "MDS01 video detection"
                : isVideoPrivacy
                  ? "MDS01 video privacy"
                  : isDashboard
                    ? "MDS01 analysis workspace"
                    : "MDS01 EEG analysis"
            }
            onClick={() => setMenuOpen(false)}
          >
            <Mds01Logo
              context={
                isVideoDetection
                  ? "detection"
                  : isVideoPrivacy
                    ? "video"
                    : isDashboard
                      ? "workspace"
                      : "eeg"
              }
            />
          </Link>

          <nav
            aria-label="Primary navigation"
            className="hidden items-center gap-1 lg:flex"
          >
            <NavLink href="/dashboard">
              <Icon name="activity" className="size-4" />
              Workspace
            </NavLink>
            <NavLink href="/upload">
              <Icon name="upload" className="size-4" />
              New analysis
            </NavLink>
            <NavLink href="/cases">
              <Icon name="list" className="size-4" />
              Cases
            </NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden rounded-full border border-rule bg-white/70 px-3 py-1.5 text-[0.68rem] font-semibold tracking-wide text-ink-faint sm:inline-flex">
              Research workspace
            </span>
            {user && (
              <div className="hidden items-center gap-2 border-l border-rule pl-4 sm:flex">
                <span
                  className="max-w-48 truncate text-xs font-medium text-ink-muted"
                  title={user.email}
                >
                  {user.email}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => void handleLogout()}
                  disabled={loggingOut}
                >
                  {loggingOut ? "Signing out…" : "Sign out"}
                </Button>
              </div>
            )}
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
              Workspace
            </NavLink>
            {user && (
              <div className="mt-2 flex items-center justify-between border-t border-rule px-3 pt-3 lg:hidden">
                <span className="max-w-52 truncate text-xs text-ink-muted">
                  {user.email}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => void handleLogout()}
                  disabled={loggingOut}
                >
                  {loggingOut ? "Signing out…" : "Sign out"}
                </Button>
              </div>
            )}
            <NavLink href="/upload" onNavigate={() => setMenuOpen(false)}>
              <Icon name="upload" className="size-4" />
              New analysis
            </NavLink>
            <NavLink href="/cases" onNavigate={() => setMenuOpen(false)}>
              <Icon name="list" className="size-4" />
              Cases
            </NavLink>
          </nav>
        </div>
      </header>

      <main id="main-content" className="flex-1" tabIndex={-1}>
        {authStatus === "authenticated" ? (
          children
        ) : (
          <div
            className="grid min-h-[50vh] place-items-center px-6"
            aria-live="polite"
          >
            <p className="text-sm text-ink-muted">Checking workspace access…</p>
          </div>
        )}
      </main>

      <footer className="mt-auto shrink-0 border-t border-rule">
        <div className="site-container flex flex-col justify-between gap-2 py-5 text-xs leading-5 text-ink-faint sm:flex-row">
          <p>MDS01 · Research only</p>
          <p>
            {isVideoPrivacy
              ? "Privacy transforms do not guarantee anonymity."
              : "Model output is not a diagnosis."}{" "}
            {isVideoDetection
              ? "Encrypted privacy-safe preview and model results are retained only for the configured review period."
              : "Original uploads are never displayed."}
          </p>
        </div>
      </footer>
    </div>
  );
}
