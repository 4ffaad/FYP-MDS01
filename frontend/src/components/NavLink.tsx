"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type NavLinkProps = {
  href: string;
  children: ReactNode;
  onNavigate?: () => void;
  className?: string;
  exact?: boolean;
};

/** Render a top-level navigation link with a route-aware active state. */
export function NavLink({
  href,
  children,
  onNavigate,
  className,
  exact = false,
}: NavLinkProps) {
  const pathname = usePathname();
  const matchesSection = (route: string) =>
    route === "/"
      ? pathname === "/"
      : pathname === route || (!exact && pathname.startsWith(`${route}/`));
  const active =
    matchesSection(href) ||
    (href === "/dashboard" && pathname === "/") ||
    (href === "/upload/eeg" &&
      (matchesSection("/sessions") || matchesSection("/results")));

  return (
    <Link
      className={cn(
        "relative inline-flex min-h-11 w-full items-center gap-3 rounded-xl border border-transparent px-3 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink focus-visible:bg-surface-soft active:translate-y-px",
        active &&
          "border-teal-dark bg-teal-dark font-semibold text-white shadow-hard-sm hover:bg-teal-dark hover:text-white",
        className,
      )}
      href={href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
    >
      {children}
    </Link>
  );
}
