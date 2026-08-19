import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "MDS01 · EEG decision support",
    template: "%s · MDS01",
  },
  description: "Privacy-preserving EEG seizure detection decision support.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* Design contract: an Apple-inspired light workspace translated for clinical EEG review. */}
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
