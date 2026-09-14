import { VideoPrivacyJobScreen } from "@/components/VideoPrivacyScreen";

export const metadata = { title: "Protected video job" };

export default async function VideoPrivacyJobPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return <VideoPrivacyJobScreen jobId={decodeURIComponent(jobId)} />;
}
