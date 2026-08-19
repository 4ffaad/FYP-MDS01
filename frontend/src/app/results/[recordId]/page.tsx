import { ResultScreen } from "@/components/ResultScreen";
import { redirect } from "next/navigation";

export const metadata = { title: "Analysis result" };

export default async function ResultPage({ params }: { params: Promise<{ recordId: string }> }) {
  const { recordId } = await params;
  if (recordId.startsWith("SES-")) redirect(`/sessions/${encodeURIComponent(recordId)}`);
  return <ResultScreen recordId={recordId} />;
}
