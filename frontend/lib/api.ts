/**
 * API client for Bank Diligence Platform
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function getToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export async function setToken(token: string): Promise<void> {
  localStorage.setItem('token', token);
}

export async function clearToken(): Promise<void> {
  localStorage.removeItem('token');
}

async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<any> {
  const token = await getToken();
  const headers: HeadersInit = {
    ...options.headers,
  };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  // Only set Content-Type for JSON requests (not for FormData)
  if (!(options.body instanceof FormData)) {
    (headers as Record<string, string>)['Content-Type'] = 'application/json';
  }
  
  const res = await fetch(`${API_BASE_URL}/api/v1${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  
  return res.json();
}

// Auth
export async function devLogin(email: string, orgName: string, role: string): Promise<{ access_token: string }> {
  return fetchApi('/auth/dev-login', {
    method: 'POST',
    body: JSON.stringify({ email, org_name: orgName, role }),
  });
}

// Cases
export async function listCases(): Promise<any[]> {
  return fetchApi('/cases');
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
export async function listDocuments(caseId: string): Promise<any[]> {
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

// OCR
export async function enqueueOcr(documentId: string): Promise<{ status: string; document_id: string; task_id?: string }> {
  return fetchApi(`/documents/${documentId}/ocr`, { method: 'POST' });
}

export async function getOcrStatus(documentId: string): Promise<any> {
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

export async function getException(exceptionId: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}`);
}

export async function resolveException(exceptionId: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ action: 'resolve' }),
  });
}

export async function waiveException(exceptionId: string, reason: string): Promise<any> {
  return fetchApi(`/exceptions/${exceptionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ action: 'waive', reason }),
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

