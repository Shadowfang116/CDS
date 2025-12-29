'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  getToken,
  getCase,
  listDocuments,
  uploadDocument,
  getDocument,
  enqueueOcr,
  getOcrStatus,
  extractDossier,
  getDossier,
  updateDossierField,
  updateDocType,
} from '@/lib/api';

type Tab = 'documents' | 'dossier';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [dossier, setDossier] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<Tab>('documents');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [ocrStatus, setOcrStatus] = useState<any>(null);

  useEffect(() => {
    checkAuthAndLoad();
  }, [caseId]);

  const checkAuthAndLoad = async () => {
    const token = await getToken();
    if (!token) {
      router.push('/');
      return;
    }
    await loadCase();
  };

  const loadCase = async () => {
    setLoading(true);
    try {
      const [c, docs] = await Promise.all([
        getCase(caseId),
        listDocuments(caseId),
      ]);
      setCaseData(c);
      setDocuments(docs);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDossier = async () => {
    try {
      const d = await getDossier(caseId);
      setDossier(d);
    } catch (e: any) {
      console.error('Failed to load dossier:', e);
    }
  };

  useEffect(() => {
    if (activeTab === 'dossier') {
      loadDossier();
    }
  }, [activeTab, caseId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      setError('Only PDF files are allowed');
      return;
    }

    setUploading(true);
    setError('');
    try {
      await uploadDocument(caseId, file);
      const docs = await listDocuments(caseId);
      setDocuments(docs);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleRunOcr = async (docId: string) => {
    try {
      await enqueueOcr(docId);
      setError('');
      // Start polling for status
      pollOcrStatus(docId);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const pollOcrStatus = async (docId: string) => {
    try {
      const status = await getOcrStatus(docId);
      setOcrStatus(status);
      // Continue polling if not all done/failed
      const pending = (status.status_counts.NotStarted || 0) + 
                      (status.status_counts.Queued || 0) + 
                      (status.status_counts.Processing || 0);
      if (pending > 0) {
        setTimeout(() => pollOcrStatus(docId), 2000);
      }
    } catch (e: any) {
      console.error('OCR status poll failed:', e);
    }
  };

  const handleViewDoc = async (docId: string) => {
    try {
      const doc = await getDocument(docId);
      setSelectedDoc(doc);
      const status = await getOcrStatus(docId);
      setOcrStatus(status);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleExtract = async () => {
    try {
      await extractDossier(caseId);
      await loadDossier();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleConfirmField = async (fieldKey: string) => {
    try {
      await updateDossierField(caseId, fieldKey, undefined, true);
      await loadDossier();
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <header className="flex justify-between items-center mb-6">
        <div>
          <a href="/" className="text-cyan-400 hover:text-cyan-300 text-sm">← Back to Cases</a>
          <h1 className="text-2xl font-bold mt-2">{caseData?.title || 'Case'}</h1>
        </div>
      </header>

      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-400 p-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-slate-700">
        <button
          onClick={() => setActiveTab('documents')}
          className={`pb-3 px-1 ${activeTab === 'documents' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Documents
        </button>
        <button
          onClick={() => setActiveTab('dossier')}
          className={`pb-3 px-1 ${activeTab === 'dossier' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Dossier
        </button>
      </div>

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Document List */}
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Documents</h2>
              <label className="btn btn-primary cursor-pointer">
                {uploading ? 'Uploading...' : 'Upload PDF'}
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={uploading}
                />
              </label>
            </div>

            {documents.length === 0 ? (
              <p className="text-slate-400">No documents uploaded yet.</p>
            ) : (
              <ul className="space-y-2">
                {documents.map((doc) => (
                  <li
                    key={doc.id}
                    className={`p-3 rounded cursor-pointer transition-colors ${
                      selectedDoc?.id === doc.id ? 'bg-cyan-500/20 border border-cyan-500' : 'bg-slate-700 hover:bg-slate-600'
                    }`}
                    onClick={() => handleViewDoc(doc.id)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium truncate">{doc.original_filename}</p>
                        <p className="text-sm text-slate-400">
                          {doc.page_count || '?'} pages • {doc.status}
                        </p>
                      </div>
                      <span className={`badge ${
                        doc.status === 'Split' ? 'badge-success' : 
                        doc.status === 'Failed' ? 'badge-error' : 'badge-warning'
                      }`}>
                        {doc.status}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Document Detail / OCR */}
          <div className="card">
            {selectedDoc ? (
              <>
                <h2 className="text-lg font-semibold mb-4">{selectedDoc.original_filename}</h2>
                
                <div className="space-y-4">
                  <div>
                    <span className="text-slate-400 text-sm">Status: </span>
                    <span className={`badge ${
                      selectedDoc.status === 'Split' ? 'badge-success' : 
                      selectedDoc.status === 'Failed' ? 'badge-error' : 'badge-warning'
                    }`}>
                      {selectedDoc.status}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 text-sm">Pages: </span>
                    <span>{selectedDoc.page_count || 0}</span>
                  </div>

                  {selectedDoc.status === 'Split' && (
                    <button
                      onClick={() => handleRunOcr(selectedDoc.id)}
                      className="btn btn-primary"
                    >
                      Run OCR
                    </button>
                  )}

                  {/* OCR Status */}
                  {ocrStatus && (
                    <div className="mt-4">
                      <h3 className="font-medium mb-2">OCR Status</h3>
                      <div className="flex gap-2 mb-3">
                        {Object.entries(ocrStatus.status_counts).map(([status, count]) => (
                          <span key={status} className={`badge ${
                            status === 'Done' ? 'badge-success' :
                            status === 'Failed' ? 'badge-error' :
                            status === 'Processing' ? 'badge-info' : 'badge-neutral'
                          }`}>
                            {status}: {count as number}
                          </span>
                        ))}
                      </div>
                      
                      <div className="max-h-60 overflow-y-auto space-y-1">
                        {ocrStatus.pages.map((page: any) => (
                          <div key={page.page_number} className="flex items-center gap-2 text-sm">
                            <span className="w-16">Page {page.page_number}</span>
                            <span className={`badge ${
                              page.status === 'Done' ? 'badge-success' :
                              page.status === 'Failed' ? 'badge-error' :
                              page.status === 'Processing' ? 'badge-info' : 'badge-neutral'
                            }`}>
                              {page.status}
                            </span>
                            {page.has_text && <span className="text-green-400">✓ Text</span>}
                            {page.error && <span className="text-red-400 text-xs">{page.error}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p className="text-slate-400">Select a document to view details and run OCR.</p>
            )}
          </div>
        </div>
      )}

      {/* Dossier Tab */}
      {activeTab === 'dossier' && (
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-semibold">Case Dossier</h2>
              {dossier && (
                <p className="text-sm text-slate-400">
                  {dossier.confirmed_count} confirmed / {dossier.pending_count} pending
                </p>
              )}
            </div>
            <button onClick={handleExtract} className="btn btn-primary">
              Extract from OCR
            </button>
          </div>

          {!dossier || dossier.fields.length === 0 ? (
            <p className="text-slate-400">
              No dossier fields yet. Upload documents, run OCR, then extract.
            </p>
          ) : (
            <div className="space-y-6">
              {/* Group fields by category */}
              {['party', 'property', 'risk'].map((category) => {
                const categoryFields = dossier.fields.filter((f: any) => 
                  f.field_key.startsWith(category)
                );
                if (categoryFields.length === 0) return null;

                return (
                  <div key={category}>
                    <h3 className="text-sm font-semibold text-cyan-400 uppercase mb-3">
                      {category}
                    </h3>
                    <div className="space-y-2">
                      {categoryFields.map((field: any) => (
                        <div key={field.id} className="flex items-center gap-3 p-3 bg-slate-700 rounded">
                          <div className="flex-1">
                            <p className="text-sm text-slate-400">{field.field_key}</p>
                            <p className="font-medium">{field.field_value || '—'}</p>
                            {field.confidence && (
                              <p className="text-xs text-slate-500">
                                Confidence: {(field.confidence * 100).toFixed(0)}%
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {field.needs_confirmation ? (
                              <button
                                onClick={() => handleConfirmField(field.field_key)}
                                className="btn btn-primary text-sm py-1"
                              >
                                Confirm
                              </button>
                            ) : (
                              <span className="badge badge-success">Confirmed</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

