"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavLinkProps = {
  href: string;
  children: ReactNode;
};

/** Render a top-level navigation link with a route-aware active state. */
export function NavLink({ href, children }: NavLinkProps) {
  const pathname = usePathname();
  const active = href === "/dashboard" ? pathname.startsWith("/dashboard") : pathname.startsWith(href);

  return (
    <Link
      className={`inline-flex min-h-10 items-center gap-2 rounded-md px-3 text-[0.8rem] font-semibold transition-colors ${
        active ? "bg-teal-soft text-teal-dark" : "text-ink-muted hover:bg-surface-muted hover:text-ink"
      }`}
      href={href}
      aria-current={active ? "page" : undefined}
    >
      {children}
    </Link>
  );
}
