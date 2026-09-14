import { VideoDetectionJobScreen } from "@/components/VideoDetectionScreen";

export default async function VideoDetectionPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return <VideoDetectionJobScreen jobId={jobId} />;
}
