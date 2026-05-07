import { redirect } from 'next/navigation';
import { getCaseDetailPath } from '@/lib/routes';

type LegacyCasePageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LegacyCasePage({ params, searchParams }: LegacyCasePageProps) {
  const { id } = await params;
  const rawSearchParams = searchParams ? await searchParams : undefined;
  const nextSearchParams = new URLSearchParams();

  if (rawSearchParams) {
    for (const [key, value] of Object.entries(rawSearchParams)) {
      if (Array.isArray(value)) {
        value.forEach((entry) => nextSearchParams.append(key, entry));
      } else if (value) {
        nextSearchParams.set(key, value);
      }
    }
  }

  redirect(getCaseDetailPath(id, nextSearchParams));
}
