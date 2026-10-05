import { redirect } from "next/navigation";

export const metadata = { title: "Video" };

export default function VideoPrivacyPage() {
  redirect("/video-detection");
}
