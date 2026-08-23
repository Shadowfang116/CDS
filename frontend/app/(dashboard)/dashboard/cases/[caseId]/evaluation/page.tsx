import { redirect } from "next/navigation";

type EvaluationRedirectPageProps = {
  params: Promise<{ caseId: string }>;
};

export default async function EvaluationRedirectPage({ params }: EvaluationRedirectPageProps) {
  const { caseId } = await params;
  redirect(`/dashboard/cases/${caseId}`);
}
