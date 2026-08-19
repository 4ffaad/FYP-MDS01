import { ResultScreen } from "@/components/ResultScreen";

export const metadata = { title: "Analysis result" };

export default async function ResultPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return <ResultScreen jobId={jobId} />;
}
