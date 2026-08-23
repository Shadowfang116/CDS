import { redirect } from "next/navigation";

type OcrRedirectPageProps = {
  params: Promise<{ caseId: string; documentId: string; pageNumber: string }>;
};

export default async function OcrRedirectPage({ params }: OcrRedirectPageProps) {
  const { caseId, documentId, pageNumber } = await params;
  redirect(`/dashboard/cases/${caseId}?doc=${documentId}&page=${pageNumber}`);
}
