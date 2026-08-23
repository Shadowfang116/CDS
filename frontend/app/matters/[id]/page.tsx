import { redirect } from "next/navigation";

type MatterAliasPageProps = {
  params: Promise<{ id: string }>;
};

export default async function MatterAliasPage({ params }: MatterAliasPageProps) {
  const { id } = await params;
  redirect(`/dashboard/cases/${id}`);
}
