import { PatientFolderScreen } from "@/components/PatientFolderScreen";
import { EegSessionsScreen } from "@/components/EegSessionsScreen";
import { WorkspaceViewTransition } from "@/components/WorkspaceViewTransition";

export const metadata = { title: "EEG workspace | MDS01" };

export default async function EegUploadPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string | string[] }>;
}) {
  const { view } = await searchParams;
  const reviewsVisible = view === "reviews";
  return (
    <WorkspaceViewTransition
      reviewsVisible={reviewsVisible}
      upload={<PatientFolderScreen mode="eeg-only" />}
      reviews={<EegSessionsScreen />}
    />
  );
}
