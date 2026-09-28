import type { Metadata } from "next";
import { PatientFolderScreen } from "@/components/PatientFolderScreen";

export const metadata: Metadata = {
  title: "New patient review | MDS01",
  description:
    "Create one patient review from EEG recordings, video clips, and a patient report.",
};

export default function UploadPage() {
  return <PatientFolderScreen />;
}
