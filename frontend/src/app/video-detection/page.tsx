import { VideoDetectionUploadScreen } from "@/components/VideoDetectionScreen";
import { VideoDetectionHistoryScreen } from "@/components/VideoDetectionHistoryScreen";
import { WorkspaceViewTransition } from "@/components/WorkspaceViewTransition";

export const metadata = { title: "Video workspace | MDS01" };

export default async function VideoDetectionPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string | string[] }>;
}) {
  const { view } = await searchParams;
  const reviewsVisible = view === "reviews";
  return (
    <WorkspaceViewTransition
      reviewsVisible={reviewsVisible}
      upload={<VideoDetectionUploadScreen />}
      reviews={<VideoDetectionHistoryScreen />}
    />
  );
}
