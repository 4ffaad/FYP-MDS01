import { redirect } from "next/navigation";

export default function VideoReviewsPage() {
  redirect("/video-detection?view=reviews");
}
