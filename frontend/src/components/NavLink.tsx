"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavLinkProps = {
  href: string;
  children: ReactNode;
  onNavigate?: () => void;
};

/** Render a top-level navigation link with a route-aware active state. */
export function NavLink({ href, children, onNavigate }: NavLinkProps) {
  const pathname = usePathname();
  const active = href === "/dashboard" ? pathname.startsWith("/dashboard") : pathname.startsWith(href);

  return (
    <Link
      className={`inline-flex min-h-11 w-full items-center gap-2 rounded-md border-b-2 px-3 text-[0.8rem] font-semibold transition-colors lg:min-h-10 lg:w-auto ${
        active ? "border-teal bg-teal-soft text-teal-dark lg:bg-transparent" : "border-transparent text-ink-muted hover:bg-surface-muted hover:text-ink lg:hover:border-rule-strong lg:hover:bg-transparent"
      }`}
      href={href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
    >
      {children}
    </Link>
  );
}
