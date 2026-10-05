import { VideoDetectionJobScreen } from "@/components/VideoDetectionScreen";

export default async function VideoDetectionPage({
  params,
  searchParams,
}: {
  params: Promise<{ jobId: string }>;
  searchParams: Promise<{ time?: string }>;
}) {
  const [{ jobId }, query] = await Promise.all([params, searchParams]);
  const time = query.time === undefined ? Number.NaN : Number(query.time);
  const initialVideoTimeSeconds = Number.isFinite(time)
    ? Math.max(0, time)
    : undefined;
  return (
    <VideoDetectionJobScreen
      jobId={jobId}
      initialVideoTimeSeconds={initialVideoTimeSeconds}
    />
  );
}
