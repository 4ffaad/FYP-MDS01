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
};

/** Render a top-level navigation link with a route-aware active state. */
export function NavLink({ href, children, onNavigate, className }: NavLinkProps) {
  const pathname = usePathname();
  const active = href === "/dashboard"
    ? ["/dashboard", "/sessions", "/results"].some((route) => pathname.startsWith(route))
    : pathname.startsWith(href);

  return (
    <Link
      className={cn(
        "relative inline-flex min-h-11 w-full items-center gap-2 rounded-lg px-3.5 text-[0.8rem] font-semibold text-ink-muted transition-colors hover:bg-surface-soft hover:text-ink focus-visible:bg-surface-soft lg:min-h-10 lg:w-auto",
        active && "bg-teal-soft text-teal-dark lg:bg-surface-muted lg:text-ink lg:after:absolute lg:after:inset-x-3 lg:after:-bottom-[1px] lg:after:h-0.5 lg:after:rounded-full lg:after:bg-teal",
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
