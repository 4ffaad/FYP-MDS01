import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import "./globals.css";
export const metadata: Metadata = {
  applicationName: "MDS01",
  title: {
    default: "MDS01 · VEEG Analysis & Video Privacy",
    template: "%s · MDS01",
  },
  description:
    "A premium research workspace for privacy-aware VEEG analysis and integrated patient-video model review.",
  authors: [{ name: "MDS01 Project Group" }],
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
