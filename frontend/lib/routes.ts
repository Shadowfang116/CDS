type QueryValue = string | number | boolean | null | undefined;

export const CASE_TABS = [
  { key: "summary", label: "Overview" },
  { key: "exceptions", label: "Exceptions" },
  { key: "cps", label: "Conditions" },
  { key: "documents", label: "Documents" },
  { key: "dossier", label: "Dossier" },
  { key: "audit", label: "Audit" },
  { key: "ocr-extractions", label: "OCR Review" },
  { key: "verification", label: "Checks" },
  { key: "drafts", label: "Drafts" },
  { key: "exports", label: "Exports" },
] as const;

export type CaseTabKey = (typeof CASE_TABS)[number]["key"];

const CASE_TAB_ALIASES: Record<string, CaseTabKey> = {
  insights: "summary",
  "exceptions-and-cps": "exceptions",
  ocr: "ocr-extractions",
};

export function getCaseDetailPath(
  caseId: string,
  query?: URLSearchParams | Record<string, QueryValue>
): string {
  const basePath = `/dashboard/cases/${caseId}`;

  if (!query) {
    return basePath;
  }

  const params =
    query instanceof URLSearchParams ? new URLSearchParams(query.toString()) : new URLSearchParams();

  if (!(query instanceof URLSearchParams)) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") {
        continue;
      }
      params.set(key, String(value));
    }
  }

  const search = params.toString();
  return search ? `${basePath}?${search}` : basePath;
}

export function normalizeCaseTab(value?: string | null): CaseTabKey {
  if (CASE_TABS.some((tab) => tab.key === value)) {
    return value as CaseTabKey;
  }

  if (value && CASE_TAB_ALIASES[value]) {
    return CASE_TAB_ALIASES[value];
  }

  return "summary";
}

export function getCaseTabPath(caseId: string, tab: CaseTabKey): string {
  return getCaseDetailPath(caseId, { tab });
}

export function getCaseDocumentFocusPath(
  caseId: string,
  documentId: string,
  page?: number,
  candidateId?: string
): string {
  return getCaseDetailPath(caseId, {
    tab: "documents",
    focusDocId: documentId,
    focusPage: page,
    focusCandidateId: candidateId,
  });
}
