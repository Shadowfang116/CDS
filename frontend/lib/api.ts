/**
 * API client for CDS Platform
 * 
 * Uses same-origin proxy (/api/v1) to avoid CORS issues.
 * The Next.js rewrite config proxies /api/v1/* to the API container.
 * For server-side rendering, use API_INTERNAL_BASE_URL (http://api:8000).
 * For client-side, use relative paths (no NEXT_PUBLIC_API_BASE_URL needed).
 */

// Note: This API client is only used from client-side code (uses localStorage).
// All requests use relative paths (/api/v1/*) which are proxied by Next.js to the API container.
// The Next.js rewrite config (next.config.js) handles the proxy to http://api:8000.

/**
 * API Error class for structured error handling
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public originalError?: any
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

function normalizeErrorDetail(value: unknown, fallback: string): string {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed || fallback;
  }

  if (Array.isArray(value)) {
    const parts = value
      .map((item) => normalizeErrorDetail(item, ''))
      .filter(Boolean);
    return parts.length > 0 ? parts.join('; ') : fallback;
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const preferred =
      record.detail ??
      record.message ??
      record.msg ??
      record.error ??
      record.reason;

    if (preferred !== undefined && preferred !== value) {
      return normalizeErrorDetail(preferred, fallback);
    }

    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }

  if (value == null) {
    return fallback;
  }

  return String(value);
}

// Request de-duplication: prevent concurrent identical GET requests
const inFlightRequests = new Map<string, Promise<any>>();

// Response cache with TTL (for GET requests only)
interface CachedResponse {
  data: any;
  timestamp: number;
  ttl: number;
}
const responseCache = new Map<string, CachedResponse>();
const CACHE_TTL_MS = 300; // 300ms cache to prevent rapid re-render storms

interface ApiFetchOptions extends RequestInit {
  cacheTtlMs?: number;
  bypassCache?: boolean;
}

// Per-endpoint counters for dev instrumentation
const requestCounters = new Map<string, number>();

async function fetchApi(endpoint: string, options: ApiFetchOptions = {}): Promise<any> {
  const method = options.method || 'GET';
  const requestKey = `${method}:${endpoint}`;
  const cacheTtlMs = options.cacheTtlMs ?? CACHE_TTL_MS;
  const bypassCache = options.bypassCache === true;
  
  // DEV ONLY: Enhanced instrumentation to identify callers
  const isDev = process.env.NODE_ENV !== 'production' || process.env.NEXT_PUBLIC_DEBUG_API === '1';
  const isCasesEndpoint = endpoint.includes('/cases/') || endpoint.includes('/documents') || endpoint.includes('/controls');
  
  if (isDev && method === 'GET' && isCasesEndpoint) {
    const counter = (requestCounters.get(requestKey) || 0) + 1;
    requestCounters.set(requestKey, counter);
    
    // Log every request with counter
    console.log(`[fetchApi #${counter}] ${method} ${endpoint}`);
    
    // Show trace at specific thresholds to identify loops
    if (counter === 5 || counter === 20 || counter === 50 || (counter > 50 && counter % 50 === 0)) {
      console.trace(`âš ï¸ REPEATED REQUEST #${counter}: ${method} ${endpoint}`);
    }
  }
  
  // Check response cache for GET requests (short TTL to prevent rapid re-render storms)
  if (method === 'GET' && !bypassCache) {
    const cached = responseCache.get(requestKey);
    if (cached && Date.now() - cached.timestamp < cached.ttl) {
      if (isDev && endpoint.includes('/cases/')) {
        console.log(`[fetchApi] Cache HIT: ${endpoint}`);
      }
      return cached.data;
    }
  }
  
  // Request de-duplication: for GET requests, reuse in-flight promise
  if (method === 'GET' && !bypassCache && inFlightRequests.has(requestKey)) {
    if (isDev && endpoint.includes('/cases/')) {
      console.log(`[fetchApi] De-duplicating in-flight GET request: ${endpoint}`);
    }
    return inFlightRequests.get(requestKey)!;
  }
  
  // Create the fetch promise
  const fetchPromise = (async () => {
    const headers: HeadersInit = {
      ...options.headers,
    };

    // Only set Content-Type for JSON requests (not for FormData)
    if (!(options.body instanceof FormData)) {
      (headers as Record<string, string>)['Content-Type'] = 'application/json';
    }
    
    // Build URL: server-side uses full URL, client-side uses relative path (proxied by Next.js)
    // This function is only called from client-side code (uses localStorage), so always use relative path
    const basePath = '/api/v1';
    const res = await fetch(`${basePath}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include', // Include cookies for same-origin requests (safe with proxy)
      signal: options.signal, // Support AbortController
    });
  
    if (!res.ok) {
      let errorDetail = res.statusText;
      let errorBody: any = undefined;
      try {
        errorBody = await res.json();
        errorDetail = normalizeErrorDetail(
          errorBody?.detail ?? errorBody?.message ?? errorBody,
          errorDetail
        );
      } catch {
        // If response is not JSON, use statusText
      }
      
      // Handle 401 Unauthorized: redirect to login
      if (res.status === 401) {
        if (typeof window !== 'undefined') {
          const currentPath = window.location.pathname;
          if (currentPath !== '/login') {
            window.location.href = '/login';
          }
        }
        throw new ApiError(
          401,
          normalizeErrorDetail(errorDetail, 'Authentication required.'),
          errorBody
        );
      }

      if (
        res.status === 403
        && errorDetail === 'Password change required'
        && typeof window !== 'undefined'
        && window.location.pathname !== '/change-password'
      ) {
        window.location.href = '/change-password';
      }
      
      // Throw structured ApiError with status and detail
      throw new ApiError(
        res.status,
        normalizeErrorDetail(errorDetail, res.statusText || 'Request failed'),
        errorBody
      );
    }
    
    const data = await res.json();
    
    // Cache successful GET responses (short TTL to prevent rapid re-render storms)
    if (method === 'GET' && !options.signal?.aborted) {
      responseCache.set(requestKey, {
        data,
        timestamp: Date.now(),
        ttl: cacheTtlMs,
      });
      // Clean up old cache entries periodically
      if (responseCache.size > 100) {
        const now = Date.now();
        for (const [key, cached] of responseCache.entries()) {
          if (now - cached.timestamp > cached.ttl) {
            responseCache.delete(key);
          }
        }
      }
    }
    
    return data;
  })();
  
  // Store in-flight promise for GET requests
  if (method === 'GET') {
    inFlightRequests.set(requestKey, fetchPromise);
    // Clean up on completion or error
    fetchPromise
      .then(() => {
        inFlightRequests.delete(requestKey);
      })
      .catch((err) => {
        inFlightRequests.delete(requestKey);
        // If aborted, don't cache
        if (err.name === 'AbortError') {
          responseCache.delete(requestKey);
        }
      });
  }
  
  return fetchPromise;
}

export async function login(email: string, password: string): Promise<any> {
  return fetchApi('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<{ message: string }> {
  return fetchApi('/auth/logout', {
    method: 'POST',
  });
}

export async function getMe(): Promise<any> {
  return fetchApi('/auth/me');
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<any> {
  return fetchApi('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

// Cases
export async function listCases(): Promise<any[]> {
  return fetchApi('/cases');
}

export interface ListCasesParams {
  q?: string;
  page?: number;
  page_size?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

function normalizeCasesListResponse(
  raw: any,
  params: ListCasesParams = {}
): import('@/types/cases').CaseListResponse {
  const fallbackPage = params.page ?? 1;
  const fallbackPageSize = params.page_size ?? 20;

  if (Array.isArray(raw)) {
    const total = raw.length;
    return {
      items: raw,
      page: fallbackPage,
      page_size: fallbackPageSize,
      total,
      total_pages: total > 0 ? Math.ceil(total / fallbackPageSize) : 1,
    };
  }

  const items = Array.isArray(raw?.items)
    ? raw.items
    : Array.isArray(raw?.value)
      ? raw.value
      : Array.isArray(raw?.data)
        ? raw.data
        : [];

  return {
    items,
    page: typeof raw?.page === 'number' ? raw.page : fallbackPage,
    page_size: typeof raw?.page_size === 'number' ? raw.page_size : fallbackPageSize,
    total:
      typeof raw?.total === 'number'
        ? raw.total
        : typeof raw?.count === 'number'
          ? raw.count
          : typeof raw?.Count === 'number'
            ? raw.Count
          : items.length,
    total_pages:
      typeof raw?.total_pages === 'number'
        ? raw.total_pages
        : typeof raw?.pages === 'number'
          ? raw.pages
          : 1,
  };
}

/** Server-paginated cases list (GET /cases?q=&page=&page_size=&sort=&order=). */
export async function listCasesPaginated(params: ListCasesParams = {}): Promise<import('@/types/cases').CaseListResponse> {
  const sp = new URLSearchParams();
  if (params.q != null && params.q !== '') sp.set('q', params.q);
  if (params.page != null) sp.set('page', String(params.page));
  if (params.page_size != null) sp.set('page_size', String(params.page_size));
  if (params.sort != null) sp.set('sort', params.sort);
  if (params.order != null) sp.set('order', params.order);
  const qs = sp.toString();
  const endpoint = `/cases${qs ? `?${qs}` : ''}`;

  try {
    const raw = await fetchApi(endpoint);
    return normalizeCasesListResponse(raw, params);
  } catch (error) {
    throw error;
  }
}

export async function listAllCases(
  params: Omit<ListCasesParams, 'page'> = {}
): Promise<import('@/types/cases').CaseListItem[]> {
  const pageSize = params.page_size ?? 100;
  const firstPage = await listCasesPaginated({ ...params, page: 1, page_size: pageSize });
  const items = [...firstPage.items];

  for (let page = 2; page <= firstPage.total_pages; page += 1) {
    const nextPage = await listCasesPaginated({ ...params, page, page_size: pageSize });
    items.push(...nextPage.items);
  }

  return items;
}

export async function approveCase(caseId: string, payload: any): Promise<any> {
  return fetchApi(`/cases/${caseId}/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCaseAssignment(caseId: string, action: 'claim' | 'unassign'): Promise<any> {
  return fetchApi(`/cases/${caseId}/assignment`, {
    method: 'PATCH',
    body: JSON.stringify({ action }),
  });
}

export async function createCase(title: string): Promise<any> {
  return fetchApi('/cases', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function getCase(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}`);
}

// Documents
export interface CaseDocumentItem {
  id: string;
  original_filename: string;
  page_count?: number | null;
  status?: string | null;
  error_message?: string | null;
  doc_type?: string | null;
  predicted_doc_type?: string | null;
  classification_confidence?: number | null;
  classification_status?: string | null;
  corrected_doc_type?: string | null;
  needs_review?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentOcrStatusPage {
  page_number: number;
  status: string;
  error?: string | null;
  has_text: boolean;
}

export interface DocumentOcrStatus {
  document_id: string;
  total_pages: number;
  queued_count: number;
  processing_count: number;
  done_count: number;
  failed_count: number;
  status_counts: Record<string, number>;
  last_error?: string | null;
  pages: DocumentOcrStatusPage[];
  average_ocr_chars_per_page?: number | null;
  failed_pages: Array<{ page_number: number; error?: string | null }>;
  processing_seconds?: number | null;
  quality_level?: string | null;
  quality_reasons?: string[];
  ocr_lang_used?: string | null;
  dpi_used?: number | null;
  preprocess_enabled?: boolean | null;
}

export async function listDocuments(caseId: string): Promise<CaseDocumentItem[]> {
  return fetchApi(`/cases/${caseId}/documents`);
}

export async function uploadDocument(caseId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  
  return fetchApi(`/cases/${caseId}/documents`, {
    method: 'POST',
    body: formData,
  });
}

export async function getDocument(documentId: string): Promise<any> {
  return fetchApi(`/documents/${documentId}`);
}

export async function getDocumentDownloadUrl(documentId: string): Promise<{ url: string; expires_in_seconds: number }> {
  return fetchApi(`/documents/${documentId}/download`);
}

export async function getPageDownloadUrl(documentId: string, pageNumber: number): Promise<{ url: string; expires_in_seconds: number }> {
  return fetchApi(`/documents/${documentId}/pages/${pageNumber}/download`);
}

export async function getPageThumbnailUrl(documentId: string, pageNumber: number): Promise<{ url: string; expires_in_seconds: number }> {
  return fetchApi(`/documents/${documentId}/pages/${pageNumber}/thumbnail`);
}

export async function getPageOcrText(documentId: string, pageNumber: number): Promise<{ page_number: number; ocr_text: string; ocr_status: string; ocr_confidence: number | null }> {
  return fetchApi(`/documents/${documentId}/pages/${pageNumber}/ocr-text`);
}

// OCR
export async function enqueueOcr(documentId: string, force: boolean = false): Promise<{ status: string; document_id: string; task_id?: string }> {
  return fetchApi(`/documents/${documentId}/ocr?force=${force}`, { method: 'POST' });
}

export async function getOcrStatus(documentId: string): Promise<DocumentOcrStatus> {
  return fetchApi(`/documents/${documentId}/ocr-status`);
}

export async function updateDocType(documentId: string, docType: string): Promise<any> {
  return fetchApi(`/documents/${documentId}/doc-type`, {
    method: 'PATCH',
    body: JSON.stringify({ doc_type: docType }),
  });
}

// Dossier
export async function extractDossier(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/extract`, { method: 'POST' });
}

export async function getDossier(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/dossier`);
}

export async function updateDossierField(caseId: string, fieldKey: string, fieldValue?: string, confirm?: boolean): Promise<any> {
  return fetchApi(`/cases/${caseId}/dossier`, {
    method: 'PATCH',
    body: JSON.stringify({ field_key: fieldKey, field_value: fieldValue, confirm }),
  });
}

export async function autofillDossier(caseId: string, overwrite: boolean = false, documentIds?: string[]): Promise<any> {
  const body: any = {};
  if (documentIds) {
    body.document_ids = documentIds;
  }
  return fetchApi(`/cases/${caseId}/dossier/autofill?overwrite=${overwrite}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function attachExceptionEvidenceSnippet(exceptionId: string, documentId: string, pageNumber: number, snippet: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}/evidence-snippet`, {
    method: 'POST',
    body: JSON.stringify({ document_id: documentId, page_number: pageNumber, snippet }),
  });
}

export async function attachCPEvidenceSnippet(cpId: string, documentId: string, pageNumber: number, snippet: string): Promise<any> {
  return fetchApi(`/cps/${cpId}/evidence-snippet`, {
    method: 'POST',
    body: JSON.stringify({ document_id: documentId, page_number: pageNumber, snippet }),
  });
}

// Rules
export async function evaluateCase(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/evaluate`, { method: 'POST' });
}

export async function listExceptions(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/exceptions`);
}

export async function listCPs(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/cps`);
}

export async function getCaseExceptions(caseId: string): Promise<any> {
  return listExceptions(caseId);
}

export async function getException(exceptionId: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}`);
}

export async function resolveException(exceptionId: string, reason?: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ action: 'resolve', reason }),
  });
}

export async function waiveException(exceptionId: string, reason: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ action: 'waive', waiver_reason: reason }),
  });
}

// Exports
export async function generateDiscrepancyLetter(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/drafts/discrepancy-letter`, { method: 'POST' });
}

export async function generateUndertakingIndemnity(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/drafts/undertaking-indemnity`, { method: 'POST' });
}

export async function generateInternalOpinion(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/drafts/internal-opinion`, { method: 'POST' });
}

export async function generateBankPack(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/exports/bank-pack`, { method: 'POST' });
}

export async function listExports(caseId: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/exports`);
}

export async function getExportDownloadUrl(exportId: string): Promise<any> {
  return fetchApi(`/exports/${exportId}/download`);
}

// Verifications
export async function listVerifications(caseId: string): Promise<any[]> {
  return fetchApi(`/cases/${caseId}/verifications`);
}

export async function updateVerificationKeys(caseId: string, verificationType: string, keysJson?: any, notes?: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/verifications/${verificationType}`, {
    method: 'PATCH',
    body: JSON.stringify({ keys_json: keysJson, notes }),
  });
}

export async function openVerificationPortal(caseId: string, verificationType: string): Promise<{ url: string; guidance_steps: string[] }> {
  return fetchApi(`/cases/${caseId}/verifications/${verificationType}/open-portal`, { method: 'POST' });
}

export async function attachVerificationEvidence(caseId: string, verificationType: string, documentId: string, pageNumber?: number, note?: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/verifications/${verificationType}/attach-evidence`, {
    method: 'POST',
    body: JSON.stringify({ document_id: documentId, page_number: pageNumber || 1, note }),
  });
}

export async function markVerificationVerified(caseId: string, verificationType: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/verifications/${verificationType}/mark-verified`, { method: 'POST' });
}

export async function markVerificationFailed(caseId: string, verificationType: string, notes: string): Promise<any> {
  return fetchApi(`/cases/${caseId}/verifications/${verificationType}/mark-failed`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

// Dashboard
export interface DashboardKPIs {
  active_cases: number;
  open_high_exceptions: number;
  pending_verifications: number;
  cp_completion_pct: number;
  verification_completion_pct: number;
}

export interface NeedsAttentionItem {
  case_id: string;
  title: string;
  status: string;
  open_high: number;
  open_medium: number;
  open_low: number;
  pending_verifications: number;
  updated_at: string;
  assigned_to_user_id?: string | null;
  assigned_to_email?: string | null;
  assigned_to_name?: string | null;
}

export interface ActivityItem {
  created_at: string;
  actor_email: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  case_id?: string | null;
  case_title?: string | null;
}

export interface TimeseriesEntry {
  date: string;
  cases_created: number;
  exports_generated: number;
  high_exceptions_created: number;
}

export interface ExceptionsBySeverity {
  high: number;
  medium: number;
  low: number;
}

export interface ApprovalPreviewItem {
  id: string;
  case_id: string;
  request_type: string;
  request_type_label: string;
  case_title: string;
  created_at: string;
  assigned_to_user_id?: string | null;
  assigned_to_email?: string | null;
  assigned_to_name?: string | null;
}

export interface ReadyForApprovalItem {
  case_id: string;
  title: string;
  status: string;
  cp_completion_pct: number;
  updated_at: string;
  assigned_to_user_id?: string | null;
  assigned_to_email?: string | null;
  assigned_to_name?: string | null;
}

export interface DashboardResponse {
  range_days: number;
  kpis: DashboardKPIs;
  processing_cases_count: number;
  oldest_processing_case_updated_at: string | null;
  cases_by_status: Record<string, number>;
  exceptions_by_severity: ExceptionsBySeverity;
  timeseries: TimeseriesEntry[];
  needs_attention: NeedsAttentionItem[];
  recent_activity: ActivityItem[];
  // Phase 8: Approvals overlay
  approvals_pending_count: number;
  approvals_pending_preview: ApprovalPreviewItem[];
  ready_for_approval_count: number;
  ready_for_approval_list: ReadyForApprovalItem[];
}

export interface DashboardSummaryResponse {
  range_days: number;
  kpis: DashboardKPIs;
  processing_cases_count: number;
  oldest_processing_case_updated_at: string | null;
  needs_attention: NeedsAttentionItem[];
  recent_activity: ActivityItem[];
  approvals_pending_count: number;
  approvals_pending_preview: ApprovalPreviewItem[];
  ready_for_approval_count: number;
  ready_for_approval_list: ReadyForApprovalItem[];
}

export interface DashboardAnalyticsResponse {
  range_days: number;
  cases_by_status: Record<string, number>;
  exceptions_by_severity: ExceptionsBySeverity;
  timeseries: TimeseriesEntry[];
}

export async function getDashboard(days: number = 30, force = false): Promise<DashboardResponse> {
  return fetchApi(`/dashboard?days=${days}`, {
    cacheTtlMs: 5000,
    bypassCache: force,
  });
}

export async function getDashboardSummary(days: number = 30, force = false): Promise<DashboardSummaryResponse> {
  try {
    return await fetchApi(`/dashboard/summary?days=${days}`, {
      cacheTtlMs: 10000,
      bypassCache: force,
    });
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 404) {
      throw error;
    }

    const fallback = await getDashboard(days, force);
    return {
      range_days: fallback.range_days,
      kpis: fallback.kpis,
      processing_cases_count: fallback.processing_cases_count,
      oldest_processing_case_updated_at: fallback.oldest_processing_case_updated_at,
      needs_attention: fallback.needs_attention,
      recent_activity: fallback.recent_activity,
      approvals_pending_count: fallback.approvals_pending_count,
      approvals_pending_preview: fallback.approvals_pending_preview,
      ready_for_approval_count: fallback.ready_for_approval_count,
      ready_for_approval_list: fallback.ready_for_approval_list,
    };
  }
}

export async function getDashboardAnalytics(days: number = 30, force = false): Promise<DashboardAnalyticsResponse> {
  try {
    return await fetchApi(`/dashboard/analytics?days=${days}`, {
      cacheTtlMs: 20000,
      bypassCache: force,
    });
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 404) {
      throw error;
    }

    const fallback = await getDashboard(days, force);
    return {
      range_days: fallback.range_days,
      cases_by_status: fallback.cases_by_status,
      exceptions_by_severity: fallback.exceptions_by_severity,
      timeseries: fallback.timeseries,
    };
  }
}

// Cohort (drilldown)
export interface CohortFilters {
  severity?: string | null;
  status?: string | null;
  date?: string | null;
  owner?: string | null;
  escalation?: string | null;
}

export interface CohortCounts {
  cases: number;
  activity: number;
}

export interface CohortCaseItem {
  case_id: string;
  title: string;
  status: string;
  updated_at: string;
  open_high: number;
  open_medium: number;
  open_low: number;
  pending_verifications: number;
  assigned_to_user_id?: string | null;
  assigned_to_email?: string | null;
  assigned_to_name?: string | null;
}

export interface CohortActivityItem {
  created_at: string;
  actor_email?: string | null;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  case_id?: string | null;
  case_title?: string | null;
}

export interface CohortResponse {
  range_days: number;
  filters: CohortFilters;
  cases: CohortCaseItem[];
  activity: CohortActivityItem[];
  counts: CohortCounts;
}

export interface GetCohortParams {
  days?: number;
  severity?: string | null;
  status?: string | null;
  date?: string | null;
  owner?: string | null;
  escalation?: string | null;
  limit?: number;
}

export async function getDashboardCohort(params: GetCohortParams = {}): Promise<CohortResponse> {
  const searchParams = new URLSearchParams();
  if (params.days) searchParams.set('days', String(params.days));
  if (params.severity) searchParams.set('severity', params.severity);
  if (params.status) searchParams.set('status', params.status);
  if (params.date) searchParams.set('date', params.date);
  if (params.owner) searchParams.set('owner', params.owner);
  if (params.escalation) searchParams.set('escalation', params.escalation);
  if (params.limit) searchParams.set('limit', String(params.limit));
  
  const queryString = searchParams.toString();
  return fetchApi(`/dashboard/cohort${queryString ? `?${queryString}` : ''}`);
}

// Saved Views (with sharing support)
export interface SavedViewConfig {
  days: number;
  severity?: string | null;
  status?: string | null;
  owner?: string | null;
}

export interface SavedView {
  id: string;
  name: string;
  is_default: boolean;
  config_json: SavedViewConfig;
  visibility: 'private' | 'org';
  shared_with_roles: string[];
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
}

export interface SavedViewCreate {
  name: string;
  config_json: SavedViewConfig;
  is_default?: boolean;
  visibility?: 'private' | 'org';
  shared_with_roles?: string[];
}

export interface SavedViewUpdate {
  name?: string;
  config_json?: SavedViewConfig;
  is_default?: boolean;
  visibility?: 'private' | 'org';
  shared_with_roles?: string[];
}

export async function listDashboardViews(): Promise<SavedView[]> {
  return fetchApi('/dashboard/views');
}

export async function createDashboardView(payload: SavedViewCreate): Promise<SavedView> {
  return fetchApi('/dashboard/views', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateDashboardView(viewId: string, payload: SavedViewUpdate): Promise<SavedView> {
  return fetchApi(`/dashboard/views/${viewId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteDashboardView(viewId: string): Promise<void> {
  return fetchApi(`/dashboard/views/${viewId}`, {
    method: 'DELETE',
  });
}

export async function recordViewUsage(viewId: string): Promise<{ status: string }> {
  return fetchApi(`/dashboard/views/${viewId}/use`, {
    method: 'POST',
  });
}

// Cohort Export
export interface CohortExportResponse {
  export_id: string;
  filename: string;
  url: string;
  expires_in_seconds: number;
  created_at: string;
  row_count: number;
}

export async function exportCohortCsv(params: GetCohortParams = {}): Promise<CohortExportResponse> {
  const searchParams = new URLSearchParams();
  if (params.days) searchParams.set('days', String(params.days));
  if (params.severity) searchParams.set('severity', params.severity);
  if (params.status) searchParams.set('status', params.status);
  if (params.date) searchParams.set('date', params.date);
  if (params.owner) searchParams.set('owner', params.owner);
  if (params.escalation) searchParams.set('escalation', params.escalation);
  
  const queryString = searchParams.toString();
  return fetchApi(`/dashboard/cohort/export${queryString ? `?${queryString}` : ''}`, {
    method: 'POST',
  });
}

// Case Insights
export interface CaseInsightsSummary {
  open_exceptions_high: number;
  open_exceptions_medium: number;
  open_exceptions_low: number;
  cp_completion_pct: number;
  verification_completion_pct: number;
  exports_generated: number;
  last_rule_run_at: string | null;
  last_ocr_at: string | null;
}

export interface CaseInsightsTimeseries {
  date: string;
  exceptions_opened: number;
  exceptions_resolved: number;
  cps_satisfied: number;
  verifications_verified: number;
  exports_generated: number;
  rule_evaluations: number;
  ocr_pages_done: number;
}

export interface CaseInsightsResponse {
  case_id: string;
  range_days: number;
  summary: CaseInsightsSummary;
  timeseries: CaseInsightsTimeseries[];
}

export async function getCaseInsights(caseId: string, days: number = 30): Promise<CaseInsightsResponse> {
  return fetchApi(`/cases/${caseId}/insights?days=${days}`);
}

// Cohort PDF Export
export async function exportCohortPdf(params: GetCohortParams = {}): Promise<CohortExportResponse> {
  const searchParams = new URLSearchParams();
  if (params.days) searchParams.set('days', String(params.days));
  if (params.severity) searchParams.set('severity', params.severity);
  if (params.status) searchParams.set('status', params.status);
  if (params.date) searchParams.set('date', params.date);
  if (params.owner) searchParams.set('owner', params.owner);
  if (params.escalation) searchParams.set('escalation', params.escalation);
  
  const queryString = searchParams.toString();
  return fetchApi(`/dashboard/cohort/export-pdf${queryString ? `?${queryString}` : ''}`, {
    method: 'POST',
  });
}

// Digest Schedules
export interface DigestFiltersConfig {
  days: number;
  severity?: string | null;
  status?: string | null;
}

export interface DigestSchedule {
  id: string;
  name: string;
  cadence: 'daily' | 'weekly';
  hour_local: number;
  weekday: number | null;
  is_enabled: boolean;
  filters_json: DigestFiltersConfig;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface DigestScheduleCreate {
  name: string;
  cadence: 'daily' | 'weekly';
  hour_local: number;
  weekday?: number;
  is_enabled?: boolean;
  filters_json?: DigestFiltersConfig;
}

export interface DigestScheduleUpdate {
  name?: string;
  cadence?: 'daily' | 'weekly';
  hour_local?: number;
  weekday?: number;
  is_enabled?: boolean;
  filters_json?: DigestFiltersConfig;
}

export interface DigestRun {
  id: string;
  schedule_id: string;
  run_at: string;
  status: 'pending' | 'success' | 'failed';
  output_export_id: string | null;
  error_message: string | null;
  created_at: string;
}

export interface DigestRunNowResponse {
  run_id: string;
  status: string;
  message: string;
}

export async function listDigestSchedules(): Promise<DigestSchedule[]> {
  return fetchApi('/digests/schedules');
}

export async function createDigestSchedule(payload: DigestScheduleCreate): Promise<DigestSchedule> {
  return fetchApi('/digests/schedules', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateDigestSchedule(scheduleId: string, payload: DigestScheduleUpdate): Promise<DigestSchedule> {
  return fetchApi(`/digests/schedules/${scheduleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteDigestSchedule(scheduleId: string): Promise<void> {
  return fetchApi(`/digests/schedules/${scheduleId}`, {
    method: 'DELETE',
  });
}

export async function runDigestNow(scheduleId: string): Promise<DigestRunNowResponse> {
  return fetchApi(`/digests/schedules/${scheduleId}/run-now`, {
    method: 'POST',
  });
}

export async function listDigestRuns(limit: number = 50): Promise<DigestRun[]> {
  return fetchApi(`/digests/runs?limit=${limit}`);
}

// ============ Notifications API (Phase 8) ============

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  severity: 'info' | 'warning' | 'critical';
  entity_type: string | null;
  entity_id: string | null;
  case_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
  total: number;
}

export async function listNotifications(unreadOnly: boolean = false, limit: number = 50): Promise<NotificationListResponse> {
  return fetchApi(`/notifications?unread_only=${unreadOnly}&limit=${limit}`);
}

export async function markNotificationRead(notificationId: string): Promise<{ success: boolean }> {
  return fetchApi(`/notifications/${notificationId}/read`, { method: 'POST' });
}

export async function markAllNotificationsRead(): Promise<{ success: boolean; message: string }> {
  return fetchApi('/notifications/read-all', { method: 'POST' });
}

export async function getUnreadNotificationCount(): Promise<{ unread_count: number }> {
  return fetchApi('/notifications/unread-count');
}

// ============ Approvals API (Phase 8) ============

export interface ApprovalRequest {
  id: string;
  case_id: string;
  case_title: string | null;
  requested_by_user_id: string;
  requested_by_email: string | null;
  requested_by_role: string;
  request_type: string;
  request_type_label: string;
  status: 'Pending' | 'Approved' | 'Rejected' | 'Cancelled';
  payload_json: Record<string, any>;
  decided_by_user_id: string | null;
  decided_by_email: string | null;
  decided_at: string | null;
  decision_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalListResponse {
  approvals: ApprovalRequest[];
  total: number;
}

export interface ApprovalRequestCreate {
  case_id: string;
  request_type: string;
  payload: Record<string, any>;
}

export interface CaseReadiness {
  case_id: string;
  ready: boolean;
  reasons: string[];
  metrics: {
    open_high_exceptions: number;
    pending_verifications: number;
    cp_completion_pct: number;
    cp_threshold_pct: number;
  };
}

export async function listApprovals(params: {
  status?: string;
  mine_only?: boolean;
  limit?: number;
} = {}): Promise<ApprovalListResponse> {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set('status', params.status);
  if (params.mine_only) searchParams.set('mine_only', 'true');
  if (params.limit) searchParams.set('limit', String(params.limit));
  const qs = searchParams.toString();
  return fetchApi(`/approvals${qs ? `?${qs}` : ''}`);
}

export async function createApproval(payload: ApprovalRequestCreate): Promise<ApprovalRequest> {
  return fetchApi('/approvals', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function approveRequest(approvalId: string, reason?: string): Promise<ApprovalRequest> {
  return fetchApi(`/approvals/${approvalId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function rejectRequest(approvalId: string, reason?: string): Promise<ApprovalRequest> {
  return fetchApi(`/approvals/${approvalId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function cancelApproval(approvalId: string): Promise<ApprovalRequest> {
  return fetchApi(`/approvals/${approvalId}/cancel`, { method: 'POST' });
}

export async function getCaseReadiness(caseId: string): Promise<CaseReadiness> {
  return fetchApi(`/approvals/case/${caseId}/readiness`);
}

// ============ Integrations API (Phase 9) ============

export interface WebhookEndpoint {
  id: string;
  name: string;
  url: string;
  is_enabled: boolean;
  secret_preview: string;
  subscribed_events: string[];
  created_at: string;
  updated_at: string;
}

export interface WebhookEndpointCreate {
  name: string;
  url: string;
  subscribed_events: string[];
}

export interface WebhookEndpointUpdate {
  name?: string;
  url?: string;
  is_enabled?: boolean;
  subscribed_events?: string[];
}

export interface WebhookDelivery {
  id: string;
  endpoint_id: string;
  event_type: string;
  status: string;
  attempt_count: number;
  http_status: number | null;
  response_body_snippet: string | null;
  last_error: string | null;
  created_at: string;
  delivered_at: string | null;
}

export interface EmailTemplate {
  id: string;
  template_key: string;
  subject: string;
  body_md: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateCreate {
  template_key: string;
  subject: string;
  body_md: string;
  is_enabled?: boolean;
}

export interface EmailTemplateUpdate {
  subject?: string;
  body_md?: string;
  is_enabled?: boolean;
}

export interface EmailDelivery {
  id: string;
  to_email: string;
  template_key: string;
  subject: string;
  status: string;
  attempt_count: number;
  last_error: string | null;
  created_at: string;
  sent_at: string | null;
}

export async function listWebhooks(): Promise<WebhookEndpoint[]> {
  return fetchApi('/integrations/webhooks');
}

export async function createWebhook(payload: WebhookEndpointCreate): Promise<{ id: string; name: string; url: string; secret: string; warning: string }> {
  return fetchApi('/integrations/webhooks', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateWebhook(endpointId: string, payload: WebhookEndpointUpdate): Promise<WebhookEndpoint> {
  return fetchApi(`/integrations/webhooks/${endpointId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteWebhook(endpointId: string): Promise<void> {
  return fetchApi(`/integrations/webhooks/${endpointId}`, { method: 'DELETE' });
}

export async function listWebhookDeliveries(endpointId: string, limit: number = 50): Promise<WebhookDelivery[]> {
  return fetchApi(`/integrations/webhooks/${endpointId}/deliveries?limit=${limit}`);
}

export async function testWebhook(endpointId: string): Promise<{ message: string; event_id: string }> {
  return fetchApi(`/integrations/webhooks/${endpointId}/test`, { method: 'POST' });
}

export async function listEmailTemplates(): Promise<EmailTemplate[]> {
  return fetchApi('/integrations/email/templates');
}

export async function createEmailTemplate(payload: EmailTemplateCreate): Promise<EmailTemplate> {
  return fetchApi('/integrations/email/templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateEmailTemplate(templateId: string, payload: EmailTemplateUpdate): Promise<EmailTemplate> {
  return fetchApi(`/integrations/email/templates/${templateId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function listEmailDeliveries(limit: number = 50): Promise<EmailDelivery[]> {
  return fetchApi(`/integrations/email/deliveries?limit=${limit}`);
}

export async function testEmail(): Promise<{ message: string; event_id: string; to_email: string }> {
  return fetchApi('/integrations/email/test', { method: 'POST' });
}

// ============ Admin API (Phase 10) ============

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  org_id?: string;
  case_id?: string | null;
  actor_user_id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  event_metadata: Record<string, any> | null;
  created_at: string;
}

export async function listAdminUsers(): Promise<AdminUser[]> {
  return fetchApi('/admin/users');
}

export async function createAdminUser(payload: { email: string; full_name: string; role: string; temporary_password: string }): Promise<AdminUser> {
  return fetchApi('/admin/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAdminUserRole(userId: string, role: string): Promise<AdminUser> {
  return fetchApi(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
}

export async function listAuditLogs(params: { days?: number; limit?: number; action_prefix?: string } = {}): Promise<AuditLogEntry[]> {
  const searchParams = new URLSearchParams();
  if (params.days) searchParams.set('days', String(params.days));
  if (params.limit) searchParams.set('limit', String(params.limit));
  if (params.action_prefix) searchParams.set('action_prefix', params.action_prefix);
  const qs = searchParams.toString();
  return fetchApi(`/admin/audit${qs ? `?${qs}` : ''}`);
}

export async function resetDemoCase(): Promise<{ message: string; org_id: string; admin_user_id: string; case_id: string }> {
  return fetchApi('/admin/demo/reset', {
    method: 'POST',
  });
}

export async function deleteDocument(documentId: string): Promise<{ message: string }> {
  return fetchApi(`/admin/documents/${documentId}`, {
    method: 'DELETE',
  });
}


export async function listGlobalAuditLogs(params: { limit?: number } = {}): Promise<AuditLogEntry[]> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set('limit', String(params.limit));
  const qs = searchParams.toString();
  return fetchApi(`/audit${qs ? `?${qs}` : ''}`);
}

export interface CaseAuditEvent {
  timestamp: string;
  user_id: string;
  user_name?: string | null;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  details: Record<string, any>;
}

export interface CaseAuditTimelineResponse {
  case_id: string;
  events: CaseAuditEvent[];
}

function normalizeCaseAuditFallback(raw: any): CaseAuditTimelineResponse {
  const rows = Array.isArray(raw)
    ? raw
    : Array.isArray(raw?.events)
      ? raw.events
      : Array.isArray(raw?.items)
        ? raw.items
        : [];

  return {
    case_id: typeof raw?.case_id === 'string' ? raw.case_id : '',
    events: rows.map((row: any) => ({
      timestamp: row.timestamp ?? row.created_at ?? '',
      user_id: row.user_id ?? row.actor_user_id ?? '',
      user_name: row.user_name ?? row.actor_email ?? row.actor ?? null,
      action: row.action ?? '',
      entity_type: row.entity_type ?? row.module ?? null,
      entity_id: row.entity_id ?? row.object_id ?? null,
      details: {
        ...(row.details ?? row.event_metadata ?? row.metadata ?? {}),
        before_snapshot: row.before_snapshot ?? row.before_json ?? null,
        after_snapshot: row.after_snapshot ?? row.after_json ?? null,
      },
    })),
  };
}

function normalizeCaseAuditResponse(raw: any, caseId: string): CaseAuditTimelineResponse {
  const normalized = normalizeCaseAuditFallback(raw);
  return {
    case_id: normalized.case_id || caseId,
    events: normalized.events,
  };
}

export async function getCaseAuditTimeline(caseId: string): Promise<CaseAuditTimelineResponse> {
  try {
    const primary = await fetchApi(`/cases/${caseId}/audit`);
    return normalizeCaseAuditResponse(primary, caseId);
  } catch (error: any) {
    if (error instanceof ApiError && error.status !== 404) {
      throw error;
    }

    const fallback = await fetchApi(`/audit-log?case_id=${caseId}`);
    return normalizeCaseAuditResponse(fallback, caseId);
  }
}

// ============ Evidence Attachment API (Phase 10) ============

export async function attachExceptionEvidence(exceptionId: string, documentId: string, pageNumber: number, note?: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}/evidence`, {
    method: 'POST',
    body: JSON.stringify({ document_id: documentId, page_number: pageNumber, note }),
  });
}

export async function attachCPEvidence(cpId: string, documentId: string, pageNumber: number, note?: string): Promise<any> {
  return fetchApi(`/cps/${cpId}/evidence`, {
    method: 'POST',
    body: JSON.stringify({ document_id: documentId, page_number: pageNumber, note }),
  });
}

export async function setDossierFieldSource(caseId: string, fieldKey: string, documentId: string, pageNumber: number): Promise<any> {
  return fetchApi(`/cases/${caseId}/dossier/source`, {
    method: 'PATCH',
    body: JSON.stringify({ field_key: fieldKey, source_document_id: documentId, source_page_number: pageNumber }),
  });
}

// ============ OCR Extractions API (Phase P7) ============

export interface OCRExtractionItem {
  id: string;
  field_key: string;
  proposed_value: string;
  edited_value: string | null;
  final_value: string | null;
  is_overridden?: boolean;
  override_note?: string | null;
  status: string;
  confidence: number | null;
  quality_score?: number | null;
  document_id: string;
  document_name: string;
  page_number: number;
  snippet: string | null;
  updated_at: string;
  is_low_quality?: boolean;
  quality_level?: string;
  warning_reason?: string;
  needs_review?: boolean;
  review_status?: string | null;
  extraction_method?: string | null;
  evidence_json?: {
    extractor?: string;
    model?: string;
    label?: string;
    token_indices?: number[];
    bbox?: number[];
    bbox_norm_1000?: number[];
    span_start?: number | null;
    span_end?: number | null;
    snippet?: string;
    ocr_engine?: string;
    extractor_version?: string;
  } | null;
}

export interface OCRExtractionsResponse {
  case_id: string;
  counts: { pending: number; confirmed: number; rejected: number };
  items: OCRExtractionItem[];
}

export async function listOCRExtractions(caseId: string, status?: string): Promise<OCRExtractionsResponse> {
  const qs = status ? `?status=${status}` : '';
  return fetchApi(`/cases/${caseId}/ocr-extractions${qs}`);
}

export async function editOCRExtraction(extractionId: string, editedValue: string | null): Promise<OCRExtractionItem> {
  return fetchApi(`/ocr-extractions/${extractionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ edited_value: editedValue }),
  });
}

export async function confirmOCRExtraction(
  extractionId: string,
  target?: string,
  fieldPath?: string,
  forceConfirm?: boolean,
  forceFormat?: boolean
): Promise<OCRExtractionItem> {
  return fetchApi(`/ocr-extractions/${extractionId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({
      target: target || 'dossier',
      field_path: fieldPath,
      force_confirm: forceConfirm,
      force_format: forceFormat,
    }),
  });
}

export async function rejectOCRExtraction(extractionId: string, reason: string): Promise<OCRExtractionItem> {
  return fetchApi(`/ocr-extractions/${extractionId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function overrideOCRExtraction(
  extractionId: string,
  valueOverride: string,
  overrideNote?: string
): Promise<OCRExtractionItem> {
  return fetchApi(`/ocr-extractions/${extractionId}/override`, {
    method: 'PATCH',
    body: JSON.stringify({
      value_override: valueOverride,
      override_note: overrideNote || undefined,
    }),
  });
}

// ============ Public Config API (Phase P7) ============

export interface PublicConfig {
  registry_verify_url: string;
  estamp_verify_url: string;
}

export async function getPublicConfig(): Promise<PublicConfig> {
  return fetchApi('/config/public');
}

// ============ Case Controls API (Phase P9) ============

export interface RegimeInfo {
  regime: string;
  confidence: number;
  reasons: string[];
}

export interface PlaybookInfo {
  id: string;
  label: string;
  regimes: string[];
  rulesets: string[];
  hard_stops: string[];
  required_evidence: Array<{
    code: string;
    label: string;
    acceptable_doc_types: string[];
  }>;
}

export interface ProvidedDocument {
  document_id: string;
  filename: string;
  doc_type: string | null;
  page_count: number | null;
}

export interface EvidenceChecklistItem {
  code: string;
  label: string;
  acceptable_doc_types: string[];
  provided_documents: ProvidedDocument[];
  status: 'Provided' | 'Missing';
}

export interface CaseRiskInfo {
  score: number;
  label: 'Green' | 'Amber' | 'Red';
  open_counts: {
    high: number;
    medium: number;
    low: number;
    hard_stop: number;
  };
}

export interface ReadinessInfo {
  ready: boolean;
  blocked_reasons: string[];
}

export interface CaseControlsResponse {
  case_id: string;
  regime: RegimeInfo;
  playbooks: PlaybookInfo[];
  evidence_checklist: EvidenceChecklistItem[];
  risk: CaseRiskInfo;
  readiness: ReadinessInfo;
}

export async function getCaseControls(caseId: string): Promise<CaseControlsResponse> {
  return fetchApi(`/cases/${caseId}/controls`);
}

// ============ Dossier Fields API (Phase P10/P14) ============

export interface DossierFieldItem {
  field_key: string;
  field_value: string | null;
  source_document_id: string | null;
  source_page_number: number | null;
  source_snippet: any | null;
  last_edited_by: string | null;
  last_edited_at: string | null;
  needs_confirmation: boolean;
}

export interface DossierFieldsResponse {
  case_id: string;
  fields: DossierFieldItem[];
}

export interface DossierFieldHistoryItem {
  id: string;
  old_value: string | null;
  new_value: string | null;
  edited_by: string;
  edited_at: string;
  source_type: string;
  source_document_id: string | null;
  source_page_number: number | null;
  note: string | null;
}

export interface DossierFieldHistoryResponse {
  field_key: string;
  history: DossierFieldHistoryItem[];
}

export async function getDossierFields(caseId: string): Promise<DossierFieldsResponse> {
  return fetchApi(`/cases/${caseId}/dossier/fields`);
}

export async function patchDossierField(
  caseId: string,
  fieldKey: string,
  payload: { value: string; note: string; evidence?: { document_id?: string; page_number?: number; snippet_json?: any }; force?: boolean }
): Promise<DossierFieldItem> {
  return fetchApi(`/cases/${caseId}/dossier/fields/${fieldKey}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function getDossierFieldHistory(caseId: string, fieldKey: string): Promise<DossierFieldHistoryResponse> {
  return fetchApi(`/cases/${caseId}/dossier/fields/${fieldKey}/history`);
}

export async function linkDossierFieldEvidence(
  caseId: string,
  fieldKey: string,
  payload: { document_id?: string; page_number?: number; snippet_json?: any }
): Promise<void> {
  return fetchApi(`/cases/${caseId}/dossier/fields/${fieldKey}/link-evidence`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ============ OCR Text Corrections API (Phase P14) ============

export interface OCRTextResponse {
  page_number: number;
  raw_text: string;
  effective_text: string;
  ocr_status: string;
  ocr_confidence: number | null;
  has_correction: boolean;
  corrected_text: string | null;
  correction_note: string | null;
  corrected_at: string | null;
  corrected_by_email: string | null;
}

export interface OCRTextCorrectionRequest {
  corrected_text: string;
  note: string;
}

export interface OCRTextCorrectionResponse {
  id: string;
  document_id: string;
  page_number: number;
  corrected_text: string;
  note: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export async function getOcrText(docId: string, page: number, mode: 'effective' | 'raw' | 'corrected' = 'effective'): Promise<OCRTextResponse> {
  return fetchApi(`/documents/${docId}/pages/${page}/ocr-text?mode=${mode}`);
}

export async function putOcrTextCorrection(docId: string, page: number, payload: OCRTextCorrectionRequest): Promise<OCRTextCorrectionResponse> {
  return fetchApi(`/documents/${docId}/pages/${page}/ocr-text/correction`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteOcrTextCorrection(docId: string, page: number): Promise<{ message: string }> {
  return fetchApi(`/documents/${docId}/pages/${page}/ocr-text/correction`, {
    method: 'DELETE',
  });
}

export interface OcrReviewOverride {
  user_id: string;
  updated_at: string | null;
  reason?: string | null;
}

export interface OcrReviewResponse {
  page_id: string;
  page_number: number;
  image_url: string;
  ocr_quality_signal?: string;
  ocr: {
    text: string;
    source: string;
    confidence: number | null;
    has_override: boolean;
    override: OcrReviewOverride | null;
  };
  meta: Record<string, any>;
}

export interface OcrOverrideRequest {
  override_text: string;
  reason?: string;
}

export interface OcrRerunRequest {
  force_profile?: 'basic' | 'enhanced';
  force_detect?: boolean;
  force_lang?: 'urd' | 'urd+eng' | 'eng';
  force_layout?: boolean;
  force_pdf_text_layer?: boolean;
  engine_mode?: 'tesseract' | 'ensemble';
}

export interface OcrRerunResponse {
  queued: boolean;
  page_id: string;
  page_number: number;
  task: string;
}

export async function getPageOcrReview(
  caseId: string,
  documentId: string,
  pageNumber: number
): Promise<OcrReviewResponse> {
  return fetchApi(`/cases/${caseId}/documents/${documentId}/pages/${pageNumber}/ocr`);
}

export async function setPageOcrOverride(
  caseId: string,
  documentId: string,
  pageNumber: number,
  payload: OcrOverrideRequest
): Promise<{ message: string; page_id: string }> {
  return fetchApi(`/cases/${caseId}/documents/${documentId}/pages/${pageNumber}/ocr`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function clearPageOcrOverride(
  caseId: string,
  documentId: string,
  pageNumber: number
): Promise<{ message: string; page_id: string }> {
  return fetchApi(`/cases/${caseId}/documents/${documentId}/pages/${pageNumber}/ocr`, {
    method: 'DELETE',
  });
}

export async function rerunPageOcr(
  caseId: string,
  documentId: string,
  pageNumber: number,
  payload: OcrRerunRequest = {}
): Promise<OcrRerunResponse> {
  return fetchApi(`/cases/${caseId}/documents/${documentId}/pages/${pageNumber}/ocr/rerun`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Golden Case Evaluation
// ---------------------------------------------------------------------------

export interface EvaluationFinding {
  id: string;
  evaluation_run_id: string;
  expectation_id: string | null;
  finding_type: 'exception' | 'cp';
  expected_rule_id: string | null;
  actual_rule_id: string | null;
  expected_title: string | null;
  actual_title: string | null;
  expected_text: string | null;
  actual_text: string | null;
  expected_severity: string | null;
  actual_severity: string | null;
  match_status: 'matched' | 'missed' | 'extra';
  similarity_score: number | null;
  notes: string | null;
}

export interface EvaluationRun {
  id: string;
  org_id: string;
  case_id: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  critical_recall: number | null;
  overall_recall: number | null;
  precision: number | null;
  expected_count: number;
  matched_count: number;
  missed_count: number;
  extra_count: number;
  status: 'running' | 'completed' | 'failed';
  created_by: string;
  error_message: string | null;
  findings: EvaluationFinding[];
}

export interface EvaluationRunListItem extends Omit<EvaluationRun, 'findings'> {}

export interface Expectation {
  id: string;
  org_id: string;
  case_id: string;
  finding_type: 'exception' | 'cp';
  expected_rule_id: string | null;
  expected_title: string;
  expected_severity: string | null;
  expected_text: string | null;
  is_critical: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpectationCreate {
  finding_type: 'exception' | 'cp';
  expected_rule_id?: string;
  expected_title: string;
  expected_severity?: string;
  expected_text?: string;
  is_critical?: boolean;
  notes?: string;
}

export interface ExpectationUpdate {
  finding_type?: 'exception' | 'cp';
  expected_rule_id?: string;
  expected_title?: string;
  expected_severity?: string;
  expected_text?: string;
  is_critical?: boolean;
  notes?: string;
}

export async function triggerEvaluationRun(caseId: string): Promise<EvaluationRun> {
  return fetchApi(`/cases/${caseId}/evaluations/run`, { method: 'POST', bypassCache: true });
}

export async function getLatestEvaluationRun(caseId: string): Promise<EvaluationRun> {
  return fetchApi(`/cases/${caseId}/evaluations/latest`, { bypassCache: true });
}

export async function listEvaluationHistory(caseId: string): Promise<EvaluationRunListItem[]> {
  return fetchApi(`/cases/${caseId}/evaluations/history`);
}

export async function listExpectations(caseId: string): Promise<Expectation[]> {
  return fetchApi(`/cases/${caseId}/expectations`);
}

export async function createExpectation(caseId: string, payload: ExpectationCreate): Promise<Expectation> {
  return fetchApi(`/cases/${caseId}/expectations`, {
    method: 'POST',
    body: JSON.stringify(payload),
    bypassCache: true,
  });
}

export async function updateExpectation(expectationId: string, payload: ExpectationUpdate): Promise<Expectation> {
  return fetchApi(`/expectations/${expectationId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
    bypassCache: true,
  });
}

export async function deleteExpectation(expectationId: string): Promise<void> {
  return fetchApi(`/expectations/${expectationId}`, { method: 'DELETE', bypassCache: true });
}

