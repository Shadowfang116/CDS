'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  getToken,
  getCase,
  listDocuments,
  uploadDocument,
  getDocument,
  getDocumentDownloadUrl,
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
  generateDiscrepancyLetter,
  generateUndertakingIndemnity,
  generateInternalOpinion,
  generateBankPack,
  listExports,
  listVerifications,
  updateVerificationKeys,
  openVerificationPortal,
  attachVerificationEvidence,
  markVerificationVerified,
  markVerificationFailed,
} from '@/lib/api';

type Tab = 'documents' | 'dossier' | 'verification' | 'exceptions' | 'drafts' | 'exports';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [dossier, setDossier] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any>(null);
  const [cps, setCps] = useState<any>(null);
  const [exports, setExports] = useState<any>(null);
  const [verifications, setVerifications] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('documents');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [ocrStatus, setOcrStatus] = useState<any>(null);
  const [selectedExc, setSelectedExc] = useState<any>(null);
  const [waiverReason, setWaiverReason] = useState('');
  const [userRole, setUserRole] = useState('Reviewer');
  const [generatedDrafts, setGeneratedDrafts] = useState<any[]>([]);

  useEffect(() => {
    checkAuthAndLoad();
  }, [caseId]);

  const checkAuthAndLoad = async () => {
    const token = await getToken();
    if (!token) {
      router.push('/');
      return;
    }
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

  const loadExports = async () => {
    try {
      const exp = await listExports(caseId);
      setExports(exp);
    } catch (e: any) {
      console.error('Failed to load exports:', e);
    }
  };

  const loadVerifications = async () => {
    try {
      const v = await listVerifications(caseId);
      setVerifications(v);
    } catch (e: any) {
      console.error('Failed to load verifications:', e);
    }
  };

  useEffect(() => {
    if (activeTab === 'dossier') {
      loadDossier();
    } else if (activeTab === 'verification') {
      loadVerifications();
    } else if (activeTab === 'exceptions') {
      loadExceptionsAndCPs();
    } else if (activeTab === 'drafts' || activeTab === 'exports') {
      loadExports();
    }
  }, [activeTab, caseId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      setError('Only PDF and image files (PNG, JPG) are allowed');
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

  const handleGenerateDraft = async (type: string) => {
    setGenerating(type);
    setError('');
    try {
      let result;
      switch (type) {
        case 'discrepancy':
          result = await generateDiscrepancyLetter(caseId);
          break;
        case 'undertaking':
          result = await generateUndertakingIndemnity(caseId);
          break;
        case 'opinion':
          result = await generateInternalOpinion(caseId);
          break;
        default:
          throw new Error('Unknown draft type');
      }
      setGeneratedDrafts(prev => [result, ...prev]);
      await loadExports();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(null);
    }
  };

  const handleGenerateBankPack = async () => {
    setGenerating('bankpack');
    setError('');
    try {
      const result = await generateBankPack(caseId);
      setGeneratedDrafts(prev => [result, ...prev]);
      await loadExports();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(null);
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
      <div className="flex gap-4 mb-6 border-b border-slate-700 overflow-x-auto">
        <button
          onClick={() => setActiveTab('documents')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'documents' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Documents
        </button>
        <button
          onClick={() => setActiveTab('dossier')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'dossier' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Dossier
        </button>
        <button
          onClick={() => setActiveTab('verification')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'verification' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Verification
        </button>
        <button
          onClick={() => setActiveTab('exceptions')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'exceptions' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Exceptions & CPs
          {exceptions && exceptions.open_count > 0 && (
            <span className="ml-2 badge badge-error">{exceptions.open_count}</span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('drafts')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'drafts' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Drafts
        </button>
        <button
          onClick={() => setActiveTab('exports')}
          className={`pb-3 px-1 whitespace-nowrap ${activeTab === 'exports' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400'}`}
        >
          Export
        </button>
      </div>

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Documents</h2>
              <label className="btn btn-primary cursor-pointer">
                {uploading ? 'Uploading...' : 'Upload File'}
                <input
                  type="file"
                  accept="application/pdf,image/png,image/jpeg,image/jpg"
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
                      <div className="flex gap-2 mb-3 flex-wrap">
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

      {/* Verification Tab */}
      {activeTab === 'verification' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Assisted Verification</h2>
            <p className="text-slate-400 mb-6">Verify e-Stamp and Registry/ROD documents via official government portals.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {verifications.map((v) => (
              <VerificationCard
                key={v.id}
                verification={v}
                caseId={caseId}
                documents={documents}
                onUpdate={loadVerifications}
                setError={setError}
              />
            ))}
          </div>
        </div>
      )}

      {/* Exceptions & CPs Tab */}
      {activeTab === 'exceptions' && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Rule Evaluation</h2>
                {exceptions && (
                  <div className="flex gap-3 mt-2 flex-wrap">
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

                  {selectedExc.evidence_refs && selectedExc.evidence_refs.length > 0 && (
                    <div>
                      <p className="text-slate-400 text-sm mb-2">Evidence References</p>
                      <ul className="space-y-1">
                        {selectedExc.evidence_refs.map((ref: any, i: number) => (
                          <li key={i} className="text-sm bg-slate-600 p-2 rounded">
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
                </div>
              ) : (
                <p className="text-slate-400">Select an exception to view details.</p>
              )}
            </div>
          </div>

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
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Drafts Tab */}
      {activeTab === 'drafts' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Generate Draft Documents</h2>
            <p className="text-slate-400 mb-6">Generate bank-style DOCX drafts based on case data, exceptions, and dossier fields.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-slate-700 rounded">
                <h3 className="font-medium mb-2">Discrepancy Letter</h3>
                <p className="text-sm text-slate-400 mb-4">Formal letter to borrower listing discrepancies and required actions.</p>
                <button 
                  onClick={() => handleGenerateDraft('discrepancy')}
                  className="btn btn-primary w-full"
                  disabled={generating === 'discrepancy'}
                >
                  {generating === 'discrepancy' ? 'Generating...' : 'Generate'}
                </button>
              </div>
              
              <div className="p-4 bg-slate-700 rounded">
                <h3 className="font-medium mb-2">Undertaking & Indemnity</h3>
                <p className="text-sm text-slate-400 mb-4">Standard undertaking and indemnity document for borrower signature.</p>
                <button 
                  onClick={() => handleGenerateDraft('undertaking')}
                  className="btn btn-primary w-full"
                  disabled={generating === 'undertaking'}
                >
                  {generating === 'undertaking' ? 'Generating...' : 'Generate'}
                </button>
              </div>
              
              <div className="p-4 bg-slate-700 rounded">
                <h3 className="font-medium mb-2">Internal Opinion</h3>
                <p className="text-sm text-slate-400 mb-4">Skeleton internal legal opinion with findings and recommendation.</p>
                <button 
                  onClick={() => handleGenerateDraft('opinion')}
                  className="btn btn-primary w-full"
                  disabled={generating === 'opinion'}
                >
                  {generating === 'opinion' ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>

          {generatedDrafts.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-4">Recently Generated</h3>
              <ul className="space-y-2">
                {generatedDrafts.map((draft, i) => (
                  <li key={i} className="p-3 bg-slate-700 rounded flex justify-between items-center">
                    <div>
                      <p className="font-medium">{draft.filename}</p>
                      <p className="text-sm text-slate-400">{draft.export_type}</p>
                    </div>
                    <a 
                      href={draft.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-primary text-sm"
                    >
                      Download
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Export Tab */}
      {activeTab === 'exports' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Bank Pack Export</h2>
            <p className="text-slate-400 mb-6">Generate a comprehensive PDF report with executive summary, all exceptions, conditions precedent, and document index.</p>
            
            <button 
              onClick={handleGenerateBankPack}
              className="btn btn-primary"
              disabled={generating === 'bankpack'}
            >
              {generating === 'bankpack' ? 'Generating Bank Pack...' : 'Generate Bank Pack PDF'}
            </button>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">
              Export History
              {exports && <span className="text-slate-400 ml-2">({exports.total} exports)</span>}
            </h3>
            {!exports || exports.exports.length === 0 ? (
              <p className="text-slate-400">No exports generated yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left border-b border-slate-700">
                      <th className="pb-2 text-slate-400 font-medium">Filename</th>
                      <th className="pb-2 text-slate-400 font-medium">Type</th>
                      <th className="pb-2 text-slate-400 font-medium">Created</th>
                      <th className="pb-2 text-slate-400 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exports.exports.map((exp: any) => (
                      <tr key={exp.id} className="border-b border-slate-700/50">
                        <td className="py-3">{exp.filename}</td>
                        <td className="py-3">
                          <span className={`badge ${
                            exp.export_type === 'bank_pack_pdf' ? 'badge-success' : 'badge-info'
                          }`}>
                            {exp.export_type}
                          </span>
                        </td>
                        <td className="py-3 text-slate-400">
                          {new Date(exp.created_at).toLocaleString()}
                        </td>
                        <td className="py-3">
                          <a 
                            href={`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/exports/${exp.id}/download`}
                            className="text-cyan-400 hover:text-cyan-300"
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                const token = await getToken();
                                const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/exports/${exp.id}/download`, {
                                  headers: { Authorization: `Bearer ${token}` }
                                });
                                const data = await res.json();
                                window.open(data.url, '_blank');
                              } catch (e: any) {
                                setError(e.message);
                              }
                            }}
                          >
                            Download
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// VerificationCard Component
// ============================================================

function VerificationCard({
  verification,
  caseId,
  documents,
  onUpdate,
  setError,
}: {
  verification: any;
  caseId: string;
  documents: any[];
  onUpdate: () => void;
  setError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [keys, setKeys] = useState<Record<string, string>>(verification.keys_json || {});
  const [notes, setNotes] = useState(verification.notes || '');
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');
  const [failedNotes, setFailedNotes] = useState('');
  const [showFailedInput, setShowFailedInput] = useState(false);
  const [loading, setLoading] = useState(false);

  const typeLabel = verification.verification_type === 'e_stamp' ? 'e-Stamp' : 'Registry / ROD';
  const statusColor = verification.status === 'Verified' ? 'badge-success' : 
                       verification.status === 'Failed' ? 'badge-error' : 'badge-warning';

  const handleSaveKeys = async () => {
    setLoading(true);
    try {
      await updateVerificationKeys(caseId, verification.verification_type, keys, notes);
      setEditing(false);
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddKey = () => {
    if (newKeyName.trim()) {
      setKeys({ ...keys, [newKeyName.trim()]: newKeyValue });
      setNewKeyName('');
      setNewKeyValue('');
    }
  };

  const handleRemoveKey = (key: string) => {
    const updated = { ...keys };
    delete updated[key];
    setKeys(updated);
  };

  const handleOpenPortal = async () => {
    try {
      const result = await openVerificationPortal(caseId, verification.verification_type);
      window.open(result.url, '_blank');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleAttachEvidence = async () => {
    if (!selectedDocId) {
      setError('Please select a document to attach');
      return;
    }
    setLoading(true);
    try {
      await attachVerificationEvidence(caseId, verification.verification_type, selectedDocId);
      setSelectedDocId('');
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkVerified = async () => {
    setLoading(true);
    try {
      await markVerificationVerified(caseId, verification.verification_type);
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkFailed = async () => {
    if (!failedNotes.trim()) {
      setError('Please provide notes explaining why verification failed');
      return;
    }
    setLoading(true);
    try {
      await markVerificationFailed(caseId, verification.verification_type, failedNotes);
      setShowFailedInput(false);
      setFailedNotes('');
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadEvidence = async (docId: string) => {
    try {
      const result = await getDocumentDownloadUrl(docId);
      window.open(result.url, '_blank');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const hasEvidence = verification.evidence_refs && verification.evidence_refs.length > 0;

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold">{typeLabel}</h3>
        <span className={`badge ${statusColor}`}>{verification.status}</span>
      </div>

      {/* Keys Section */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-slate-400">Verification Keys</span>
          {!editing && verification.status === 'Pending' && (
            <button 
              onClick={() => setEditing(true)} 
              className="text-sm text-cyan-400 hover:text-cyan-300"
            >
              Edit
            </button>
          )}
        </div>
        
        {editing ? (
          <div className="space-y-2">
            {Object.entries(keys).map(([key, value]) => (
              <div key={key} className="flex gap-2 items-center">
                <input
                  type="text"
                  value={key}
                  disabled
                  className="input flex-1 text-sm bg-slate-600"
                />
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setKeys({ ...keys, [key]: e.target.value })}
                  className="input flex-1 text-sm"
                />
                <button
                  onClick={() => handleRemoveKey(key)}
                  className="text-red-400 hover:text-red-300 px-2"
                >
                  ×
                </button>
              </div>
            ))}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Key name..."
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="input flex-1 text-sm"
              />
              <input
                type="text"
                placeholder="Value..."
                value={newKeyValue}
                onChange={(e) => setNewKeyValue(e.target.value)}
                className="input flex-1 text-sm"
              />
              <button onClick={handleAddKey} className="btn btn-secondary text-sm">
                Add
              </button>
            </div>
            <textarea
              placeholder="Notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full text-sm"
              rows={2}
            />
            <div className="flex gap-2">
              <button 
                onClick={handleSaveKeys} 
                className="btn btn-primary text-sm"
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save'}
              </button>
              <button 
                onClick={() => { setEditing(false); setKeys(verification.keys_json || {}); }}
                className="btn btn-secondary text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-slate-700 rounded p-3">
            {Object.keys(keys).length === 0 ? (
              <p className="text-slate-400 text-sm">No verification keys set. Click Edit to add.</p>
            ) : (
              <div className="space-y-1">
                {Object.entries(keys).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-slate-400">{key}:</span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            )}
            {verification.notes && (
              <p className="text-sm text-slate-400 mt-2 pt-2 border-t border-slate-600">
                {verification.notes}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Portal Button */}
      <button
        onClick={handleOpenPortal}
        className="btn btn-secondary w-full mb-4"
      >
        Open Verification Portal ↗
      </button>

      {/* Evidence Section */}
      <div className="mb-4">
        <span className="text-sm text-slate-400 block mb-2">Evidence</span>
        
        {hasEvidence ? (
          <ul className="space-y-2 mb-3">
            {verification.evidence_refs.map((ref: any) => {
              const doc = documents.find((d) => d.id === ref.document_id);
              return (
                <li key={ref.id} className="flex justify-between items-center p-2 bg-slate-700 rounded text-sm">
                  <span>{doc?.original_filename || ref.document_id.substring(0, 8)}</span>
                  <button 
                    onClick={() => handleDownloadEvidence(ref.document_id)}
                    className="text-cyan-400 hover:text-cyan-300 text-sm"
                  >
                    View
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-sm text-slate-400 mb-3">No evidence attached yet.</p>
        )}

        {verification.status === 'Pending' && (
          <div className="flex gap-2">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="input flex-1 text-sm"
            >
              <option value="">Select document...</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.original_filename}
                </option>
              ))}
            </select>
            <button
              onClick={handleAttachEvidence}
              className="btn btn-secondary text-sm"
              disabled={loading || !selectedDocId}
            >
              Attach
            </button>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {verification.status === 'Pending' && (
        <div className="space-y-2 pt-4 border-t border-slate-600">
          <button
            onClick={handleMarkVerified}
            className="btn btn-primary w-full"
            disabled={loading || !hasEvidence}
            title={!hasEvidence ? 'Attach evidence first' : ''}
          >
            {loading ? 'Processing...' : 'Mark as Verified'}
          </button>
          
          {showFailedInput ? (
            <div className="space-y-2">
              <textarea
                placeholder="Reason for failure..."
                value={failedNotes}
                onChange={(e) => setFailedNotes(e.target.value)}
                className="input w-full text-sm"
                rows={2}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleMarkFailed}
                  className="btn btn-secondary flex-1"
                  disabled={loading}
                >
                  Confirm Failed
                </button>
                <button
                  onClick={() => { setShowFailedInput(false); setFailedNotes(''); }}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowFailedInput(true)}
              className="btn btn-secondary w-full"
            >
              Mark as Failed
            </button>
          )}
        </div>
      )}

      {/* Verified/Failed info */}
      {verification.status === 'Verified' && verification.verified_at && (
        <p className="text-sm text-green-400 mt-4">
          ✓ Verified on {new Date(verification.verified_at).toLocaleString()}
        </p>
      )}
      {verification.status === 'Failed' && verification.notes && (
        <p className="text-sm text-red-400 mt-4">
          ✗ Failed: {verification.notes}
        </p>
      )}
    </div>
  );
}
