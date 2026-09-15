import { CaseDetailScreen } from "@/components/CaseDetailScreen";

export const metadata = { title: "Case history" };

export default async function CasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <CaseDetailScreen caseId={decodeURIComponent(caseId)} />;
}
