export type EvidenceRef = {
  doc_id: string;
  page: number;
  snippet?: string;
};

export type EvidenceItem = {
  id: string;
  title: string;
  refs: EvidenceRef[];
  created_at?: string;
};
