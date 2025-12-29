'use client';

import { useState, useEffect } from 'react';
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
  evaluateCase,
  listExceptions,
  listCPs,
  resolveException,
  waiveException,
} from '@/lib/api';

type Tab = 'documents' | 'dossier' | 'exceptions';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [dossier, setDossier] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any>(null);
  const [cps, setCps] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<Tab>('documents');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [ocrStatus, setOcrStatus] = useState<any>(null);
  const [selectedExc, setSelectedExc] = useState<any>(null);
  const [waiverReason, setWaiverReason] = useState('');
  const [userRole, setUserRole] = useState('Reviewer');

  useEffect(() => {
    checkAuthAndLoad();
  }, [caseId]);

  const checkAuthAndLoad = async () => {
    const token = await getToken();
    if (!token) {
      router.push('/');
      return;
    }
    // Decode role from token (simple decode, not verify)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUserRole(payload.role || 'Reviewer');
    } catch {}
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

  const loadExceptionsAndCPs = async () => {
    try {
      const [exc, cp] = await Promise.all([
        listExceptions(caseId),
        listCPs(caseId),
      ]);
      setExceptions(exc);
      setCps(cp);
    } catch (e: any) {
      console.error('Failed to load exceptions:', e);
    }
  };

  useEffect(() => {
    if (activeTab === 'dossier') {
      loadDossier();
    } else if (activeTab === 'exceptions') {
      loadExceptionsAndCPs();
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
      pollOcrStatus(docId);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const pollOcrStatus = async (docId: string) => {
    try {
      const status = await getOcrStatus(docId);
      setOcrStatus(status);
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

  const handleEvaluate = async () => {
    setEvaluating(true);
    setError('');
    try {
      await evaluateCase(caseId);
      await loadExceptionsAndCPs();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleResolve = async (excId: string) => {
    try {
      await resolveException(excId);
      await loadExceptionsAndCPs();
      setSelectedExc(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleWaive = async (excId: string) => {
    if (!waiverReason.trim()) {
      setError('Waiver reason is required');
      return;
    }
    try {
      await waiveException(excId, waiverReason);
      await loadExceptionsAndCPs();
      setSelectedExc(null);
      setWaiverReason('');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const canWaive = userRole === 'Admin' || userRole === 'Approver';
  const canResolve = userRole === 'Admin' || userRole === 'Approver' || userRole === 'Reviewer';

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
          <button onClick={() => setError('')} className="float-right">×</button>
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
        <button
          onClick={() => setActiveTab('exceptions')}
          className={`pb-3 px-1 ${activeTab === 'exceptions' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Exceptions & CPs
          {exceptions && exceptions.open_count > 0 && (
            <span className="ml-2 badge badge-error">{exceptions.open_count}</span>
          )}
        </button>
      </div>

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                    <button onClick={() => handleRunOcr(selectedDoc.id)} className="btn btn-primary">
                      Run OCR
                    </button>
                  )}

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
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p className="text-slate-400">Select a document to view details.</p>
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
            <p className="text-slate-400">No dossier fields yet.</p>
          ) : (
            <div className="space-y-6">
              {['party', 'property', 'risk'].map((category) => {
                const categoryFields = dossier.fields.filter((f: any) => 
                  f.field_key.startsWith(category)
                );
                if (categoryFields.length === 0) return null;

                return (
                  <div key={category}>
                    <h3 className="text-sm font-semibold text-cyan-400 uppercase mb-3">{category}</h3>
                    <div className="space-y-2">
                      {categoryFields.map((field: any) => (
                        <div key={field.id} className="flex items-center gap-3 p-3 bg-slate-700 rounded">
                          <div className="flex-1">
                            <p className="text-sm text-slate-400">{field.field_key}</p>
                            <p className="font-medium">{field.field_value || '—'}</p>
                          </div>
                          {field.needs_confirmation ? (
                            <button onClick={() => handleConfirmField(field.field_key)} className="btn btn-primary text-sm py-1">
                              Confirm
                            </button>
                          ) : (
                            <span className="badge badge-success">Confirmed</span>
                          )}
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

      {/* Exceptions & CPs Tab */}
      {activeTab === 'exceptions' && (
        <div className="space-y-6">
          {/* Evaluate Button & Summary */}
          <div className="card">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Rule Evaluation</h2>
                {exceptions && (
                  <div className="flex gap-3 mt-2">
                    <span className="badge badge-error">High: {exceptions.high_count}</span>
                    <span className="badge badge-warning">Medium: {exceptions.medium_count}</span>
                    <span className="badge badge-info">Low: {exceptions.low_count}</span>
                    <span className="text-slate-400">|</span>
                    <span className="text-slate-400">Open: {exceptions.open_count}</span>
                    <span className="text-green-400">Resolved: {exceptions.resolved_count}</span>
                    <span className="text-yellow-400">Waived: {exceptions.waived_count}</span>
                  </div>
                )}
              </div>
              <button 
                onClick={handleEvaluate} 
                className="btn btn-primary"
                disabled={evaluating}
              >
                {evaluating ? 'Evaluating...' : 'Evaluate Rules'}
              </button>
            </div>
          </div>

          {/* Exceptions List */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold mb-4">Exceptions</h3>
              {!exceptions || exceptions.exceptions.length === 0 ? (
                <p className="text-slate-400">No exceptions. Run evaluation first.</p>
              ) : (
                <ul className="space-y-2 max-h-96 overflow-y-auto">
                  {exceptions.exceptions.map((exc: any) => (
                    <li
                      key={exc.id}
                      onClick={() => setSelectedExc(exc)}
                      className={`p-3 rounded cursor-pointer transition-colors ${
                        selectedExc?.id === exc.id ? 'bg-cyan-500/20 border border-cyan-500' : 'bg-slate-700 hover:bg-slate-600'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium">{exc.title}</p>
                          <p className="text-sm text-slate-400">{exc.module} • {exc.rule_id}</p>
                        </div>
                        <div className="flex gap-1">
                          <span className={`badge ${
                            exc.severity === 'High' ? 'badge-error' :
                            exc.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                          }`}>
                            {exc.severity}
                          </span>
                          <span className={`badge ${
                            exc.status === 'Open' ? 'badge-neutral' :
                            exc.status === 'Resolved' ? 'badge-success' : 'badge-warning'
                          }`}>
                            {exc.status}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Exception Detail */}
            <div className="card">
              {selectedExc ? (
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold">{selectedExc.title}</h3>
                    <span className={`badge ${
                      selectedExc.severity === 'High' ? 'badge-error' :
                      selectedExc.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                    }`}>
                      {selectedExc.severity}
                    </span>
                  </div>
                  
                  <div>
                    <p className="text-slate-400 text-sm">Module</p>
                    <p>{selectedExc.module}</p>
                  </div>
                  
                  <div>
                    <p className="text-slate-400 text-sm">Description</p>
                    <p>{selectedExc.description || '—'}</p>
                  </div>
                  
                  <div>
                    <p className="text-slate-400 text-sm">Condition Precedent</p>
                    <p>{selectedExc.cp_text || '—'}</p>
                  </div>
                  
                  <div>
                    <p className="text-slate-400 text-sm">Resolution Conditions</p>
                    <p>{selectedExc.resolution_conditions || '—'}</p>
                  </div>

                  {selectedExc.evidence_refs && selectedExc.evidence_refs.length > 0 && (
                    <div>
                      <p className="text-slate-400 text-sm mb-2">Evidence References</p>
                      <ul className="space-y-1">
                        {selectedExc.evidence_refs.map((ref: any) => (
                          <li key={ref.id} className="text-sm bg-slate-600 p-2 rounded">
                            Doc: {ref.document_id?.substring(0, 8)}... 
                            {ref.page_number && ` • Page ${ref.page_number}`}
                            {ref.note && ` • ${ref.note}`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedExc.status === 'Open' && (
                    <div className="space-y-3 pt-4 border-t border-slate-600">
                      {canResolve && (
                        <button 
                          onClick={() => handleResolve(selectedExc.id)}
                          className="btn btn-primary w-full"
                        >
                          Mark as Resolved
                        </button>
                      )}
                      
                      {canWaive && (
                        <div className="space-y-2">
                          <input
                            type="text"
                            placeholder="Waiver reason..."
                            value={waiverReason}
                            onChange={(e) => setWaiverReason(e.target.value)}
                            className="input w-full"
                          />
                          <button 
                            onClick={() => handleWaive(selectedExc.id)}
                            className="btn btn-secondary w-full"
                          >
                            Waive Exception
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {selectedExc.status === 'Waived' && selectedExc.waiver_reason && (
                    <div className="bg-yellow-500/20 p-3 rounded">
                      <p className="text-yellow-400 text-sm">Waiver Reason:</p>
                      <p>{selectedExc.waiver_reason}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-slate-400">Select an exception to view details.</p>
              )}
            </div>
          </div>

          {/* CPs List */}
          <div className="card">
            <h3 className="font-semibold mb-4">
              Conditions Precedent
              {cps && <span className="text-slate-400 ml-2">({cps.open_count} open)</span>}
            </h3>
            {!cps || cps.cps.length === 0 ? (
              <p className="text-slate-400">No conditions precedent.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {cps.cps.map((cp: any) => (
                  <div key={cp.id} className="p-3 bg-slate-700 rounded">
                    <div className="flex justify-between items-start mb-2">
                      <span className={`badge ${
                        cp.severity === 'High' ? 'badge-error' :
                        cp.severity === 'Medium' ? 'badge-warning' : 'badge-info'
                      }`}>
                        {cp.severity}
                      </span>
                      <span className={`badge ${
                        cp.status === 'Open' ? 'badge-neutral' :
                        cp.status === 'Satisfied' ? 'badge-success' : 'badge-warning'
                      }`}>
                        {cp.status}
                      </span>
                    </div>
                    <p className="text-sm">{cp.text}</p>
                    {cp.evidence_required && (
                      <p className="text-xs text-slate-400 mt-2">Required: {cp.evidence_required}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
