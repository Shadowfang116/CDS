/**
 * Case list types for server-paginated GET /api/v1/cases
 * Backend returns: id, org_id, title, status, created_at, updated_at.
 * reference is optional for future use.
 */

export type CaseListItem = {
  id: string | number;
  title?: string | null;
  reference?: string | null;
  status?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  org_id?: string | null;
};

export type CaseListResponse = {
  items: CaseListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};
