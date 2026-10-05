import { redirect } from "next/navigation";

export default function SessionsPage() {
  redirect("/upload/eeg?view=reviews");
}
