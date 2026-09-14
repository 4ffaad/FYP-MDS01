import { redirect } from "next/navigation";

export const metadata = { title: "Video detection" };

export default function VideoPrivacyPage() {
  redirect("/video-detection");
}
