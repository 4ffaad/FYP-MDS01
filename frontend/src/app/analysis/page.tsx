import { CombinedAnalysisScreen } from "@/components/CombinedAnalysisScreen";

export const metadata = { title: "Analysis report" };

export default async function AnalysisPage({
  searchParams,
}: {
  searchParams: Promise<{ sessionId?: string; videoJobId?: string }>;
}) {
  const params = await searchParams;
  return (
    <CombinedAnalysisScreen
      sessionId={params.sessionId}
      videoJobId={params.videoJobId}
    />
  );
}
