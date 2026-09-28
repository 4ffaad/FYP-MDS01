import { CaseDetailScreen } from "@/components/CaseDetailScreen";

export const metadata = { title: "Case history" };

export default async function CasePage({
  params,
  searchParams,
}: {
  params: Promise<{ caseId: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { caseId } = await params;
  const query = await searchParams;
  const decodedCaseId = decodeURIComponent(caseId);
  return (
    <CaseDetailScreen
      key={decodedCaseId}
      caseId={decodedCaseId}
      videoRejectedCount={readPositiveCount(query.video_rejected_count)}
      videoUnconfirmedCount={readPositiveCount(query.video_unconfirmed_count)}
    />
  );
}

function readPositiveCount(value: string | string[] | undefined): number {
  if (typeof value !== "string" || !/^\d+$/.test(value)) return 0;
  const count = Number(value);
  return Number.isSafeInteger(count) && count > 0 ? count : 0;
}
