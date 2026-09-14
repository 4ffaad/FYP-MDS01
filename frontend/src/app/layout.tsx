import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import "./globals.css";
import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  applicationName: "MDS01",
  title: {
    default: "MDS01 · EEG Analysis & Video Privacy",
    template: "%s · MDS01",
  },
  description:
    "A research workspace for privacy-aware EEG analysis and standalone patient-video privacy transformation.",
  authors: [{ name: "MDS01 Project Group" }],
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
