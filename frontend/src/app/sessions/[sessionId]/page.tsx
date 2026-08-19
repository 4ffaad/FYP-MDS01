import { SessionDetailScreen } from "@/components/SessionDetailScreen";

export const metadata = { title: "Analysis session" };

export default async function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <SessionDetailScreen sessionId={sessionId} />;
}
