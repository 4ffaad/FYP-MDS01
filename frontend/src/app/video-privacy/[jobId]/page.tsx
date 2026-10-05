import { redirect } from "next/navigation";

export const metadata = { title: "Video reviews" };

export default function VideoPrivacyJobPage() {
  redirect("/video-reviews");
}
