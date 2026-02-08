'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  listDocuments,
  getPageDownloadUrl,
  getPageThumbnailUrl,
  getOcrText,
  getOcrStatus,
  enqueueOcr,
  getMe,
  listExceptions,
  listCPs,
  attachExceptionEvidenceSnippet,
  attachCPEvidenceSnippet,
  putOcrTextCorrection,
  deleteOcrTextCorrection,
  autofillDossier,
} from '@/lib/api';
import { useRouter } from 'next/navigation';

interface DocumentViewerProps {
  caseId: string;
  documents?: any[]; // Passed from parent (single source of truth) - if provided, don't fetch independently
  onAttachEvidence?: (documentId: string, pageNumber: number) => void;
  initialDocId?: string;
  initialPage?: number;
}

export function DocumentViewer({ caseId, documents: documentsProp, onAttachEvidence, initialDocId, initialPage }: DocumentViewerProps) {
  const router = useRouter();
  // Use documents from prop if provided (single source of truth), otherwise fetch independently
  const [documentsState, setDocumentsState] = useState<any[]>([]);
  const documents = documentsProp ?? documentsState;
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [selectedPage, setSelectedPage] = useState<number>(1);
  const [pageImageUrl, setPageImageUrl] = useState<string | null>(null);
  const [ocrText, setOcrText] = useState<string>('');
  const [ocrTextData, setOcrTextData] = useState<any>(null);
  const [ocrMode, setOcrMode] = useState<'effective' | 'raw' | 'corrected'>('effective');
  const [editingOcr, setEditingOcr] = useState(false);
  const [ocrCorrectionText, setOcrCorrectionText] = useState('');
  const [ocrCorrectionNote, setOcrCorrectionNote] = useState('');
  const [savingCorrection, setSavingCorrection] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pageLoading, setPageLoading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [ocrStatus, setOcrStatus] = useState<any>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [cps, setCps] = useState<any[]>([]);
  const [selectedSnippet, setSelectedSnippet] = useState<string>('');
  const [showSnippetModal, setShowSnippetModal] = useState(false);
  const [snippetTarget, setSnippetTarget] = useState<'exception' | 'cp' | null>(null);
  const [snippetTargetId, setSnippetTargetId] = useState<string>('');
  const [autofilling, setAutofilling] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedRef = useRef<{ caseId: string | null; initialDocSet: boolean }>({ caseId: null, initialDocSet: false });

  // Only fetch documents if not provided as prop (parent is single source of truth)
  const loadDocuments = useCallback(async () => {
    // Skip if documents are provided as prop
    if (documentsProp) {
      setLoading(false);
      return;
    }
    
    // Prevent duplicate loads for the same caseId
    if (loadedRef.current.caseId === caseId) {
      return;
    }
    
    // Abort previous request if still in flight
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    setLoading(true);
    try {
      const docs = await listDocuments(caseId);
      
      if (abortController.signal.aborted) {
        return;
      }
      
      setDocumentsState(docs);
      if (docs.length > 0 && !selectedDoc) {
        setSelectedDoc(docs[0]);
      }
      loadedRef.current.caseId = caseId;
      
      // Get current user info for role check
      const userData = await getMe();
      if (abortController.signal.aborted) return;
      
      setCurrentUser(userData);
      // Load exceptions and CPs for snippet attachment
      if (userData && (userData.role === 'Admin' || userData.role === 'Reviewer')) {
        Promise.all([
          listExceptions(caseId).then(excData => setExceptions(excData.exceptions || [])).catch(() => {}),
          listCPs(caseId).then(cpData => setCps(cpData.cps || [])).catch(() => {}),
        ]);
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        return;
      }
      console.error('Failed to load documents:', e);
    } finally {
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    }
  }, [caseId, selectedDoc, documentsProp]);

  // Initial load effect - only depends on caseId and documentsProp
  useEffect(() => {
    loadDocuments();
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadDocuments]);
  
  // Update selectedDoc when documents prop changes
  useEffect(() => {
    if (documentsProp && documentsProp.length > 0 && !selectedDoc) {
      setSelectedDoc(documentsProp[0]);
    }
  }, [documentsProp, selectedDoc]);

  // P14: Handle initial doc/page from URL params - only run once after documents are loaded
  useEffect(() => {
    if (initialDocId && documents.length > 0 && !loadedRef.current.initialDocSet) {
      const doc = documents.find(d => d.id === initialDocId);
      if (doc) {
        setSelectedDoc(doc);
        if (initialPage && initialPage >= 1) {
          setSelectedPage(initialPage);
        }
        loadedRef.current.initialDocSet = true;
      }
    }
  }, [initialDocId, initialPage, documents]);

  useEffect(() => {
    if (selectedDoc && selectedPage) {
      loadPage();
    }
  }, [selectedDoc, selectedPage]);

  useEffect(() => {
    if (selectedDoc) {
      loadOcrStatus();
    }
  }, [selectedDoc]);


  const loadPage = async () => {
    if (!selectedDoc) return;
    
    setPageLoading(true);
    try {
      // Load page image
      const imageResult = await getPageThumbnailUrl(selectedDoc.id, selectedPage);
      setPageImageUrl(imageResult.url);

      // Load OCR text (P14: use new API with corrections support)
      try {
        const ocrResult = await getOcrText(selectedDoc.id, selectedPage, ocrMode);
        setOcrTextData(ocrResult);
        setOcrText(ocrResult.effective_text || ocrResult.raw_text || '');
      } catch (e) {
        setOcrText('OCR not available');
        setOcrTextData(null);
      }
    } catch (e: any) {
      console.error('Failed to load page:', e);
    } finally {
      setPageLoading(false);
    }
  };

  const loadOcrStatus = async () => {
    if (!selectedDoc) return;
    try {
      const status = await getOcrStatus(selectedDoc.id);
      setOcrStatus(status);
    } catch (e) {
      console.error('Failed to load OCR status:', e);
    }
  };

  const handleForceOcr = async () => {
    if (!selectedDoc) return;
    setOcrLoading(true);
    try {
      await enqueueOcr(selectedDoc.id, true);
      // Poll for status update
      setTimeout(() => {
        loadOcrStatus();
        setOcrLoading(false);
      }, 2000);
    } catch (e) {
      console.error('Failed to re-run OCR:', e);
      setOcrLoading(false);
    }
  };

  const getOcrStatusBadge = () => {
    if (!ocrStatus) return null;
    const status = ocrStatus.status_counts;
    if (status?.Done === ocrStatus.total_pages && ocrStatus.failed_count === 0) {
      return <Badge className="bg-green-500/20 text-green-400 border-green-500/50">Done</Badge>;
    } else if (status?.Processing || status?.Queued) {
      return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/50">Processing</Badge>;
    } else if (ocrStatus.failed_count > 0) {
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/50">Failed</Badge>;
    }
    return <Badge variant="outline">Queued</Badge>;
  };

  const handleSearch = (query: string) => {
    if (!ocrText || !query) return;
    // Simple highlight: would need more sophisticated text highlighting in real implementation
    const regex = new RegExp(`(${query})`, 'gi');
    return ocrText.replace(regex, '<mark>$1</mark>');
  };

  if (loading) {
    return <Skeleton className="h-96 w-full" />;
  }

  if (documents.length === 0) {
    return <div className="text-slate-400 p-8 text-center">No documents uploaded</div>;
  }

  return (
    <div className="flex h-[calc(100vh-200px)] bg-slate-900">
      {/* Left: Document List */}
      <div className="w-64 border-r border-slate-700 overflow-y-auto">
        <div className="p-4 space-y-2">
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => {
                setSelectedDoc(doc);
                setSelectedPage(1);
              }}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedDoc?.id === doc.id
                  ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400'
                  : 'bg-slate-800/50 border-slate-700 text-slate-300 hover:bg-slate-700/50'
              }`}
            >
              <div className="font-medium text-sm">{doc.original_filename}</div>
              <div className="flex items-center gap-2 mt-1">
                {doc.doc_type && (
                  <Badge variant="outline" className="text-xs">
                    {doc.doc_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Badge>
                )}
                <span className="text-xs text-slate-500">
                  {doc.page_count || 0} pages
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Middle: Page Thumbnails */}
      {selectedDoc && (
        <div className="w-32 border-r border-slate-700 overflow-y-auto bg-slate-800/30">
          <div className="p-2 space-y-2">
            {Array.from({ length: selectedDoc.page_count || 0 }, (_, i) => i + 1).map((pageNum) => (
              <button
                key={pageNum}
                onClick={() => setSelectedPage(pageNum)}
                className={`w-full aspect-[3/4] rounded border-2 transition-colors ${
                  selectedPage === pageNum
                    ? 'border-cyan-500'
                    : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <div className="w-full h-full bg-slate-700/50 flex items-center justify-center text-xs text-slate-400">
                  {pageNum}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main: Page Viewer */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="border-b border-slate-700 bg-slate-800/50">
          <div className="h-12 flex items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-300">
                Page {selectedPage} of {selectedDoc?.page_count || 0}
              </span>
              {selectedDoc && selectedDoc.doc_type && (
                <Badge variant="outline" className="text-xs">
                  Type: {selectedDoc.doc_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </Badge>
              )}
              {selectedDoc && getOcrStatusBadge()}
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}>
                -
              </Button>
              <span className="text-xs text-slate-400 w-12 text-center">{Math.round(zoom * 100)}%</span>
              <Button size="sm" variant="outline" onClick={() => setZoom(Math.min(2, zoom + 0.25))}>
                +
              </Button>
              {onAttachEvidence && selectedDoc && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onAttachEvidence(selectedDoc.id, selectedPage)}
                >
                  Attach as Evidence
                </Button>
              )}
              {selectedDoc && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleForceOcr}
                  disabled={ocrLoading}
                >
                  {ocrLoading ? 'Processing...' : 'Re-run OCR (force)'}
                </Button>
              )}
            </div>
          </div>
          
          {/* OCR Quality Info */}
          {ocrStatus && (
            <div className="px-4 py-2 border-t border-slate-700/50 bg-slate-800/30">
              <div className="flex items-center gap-4 text-xs text-slate-400">
                {ocrStatus.average_ocr_chars_per_page && (
                  <span>Avg chars/page: {Math.round(ocrStatus.average_ocr_chars_per_page)}</span>
                )}
                {ocrStatus.processing_seconds && (
                  <span>Processing: {Math.round(ocrStatus.processing_seconds)}s</span>
                )}
                {ocrStatus.failed_pages && ocrStatus.failed_pages.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-red-400">Failed pages:</span>
                    {ocrStatus.failed_pages.map((fp: any, idx: number) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedPage(fp.page_number)}
                        className="text-red-400 hover:text-red-300 underline"
                      >
                        {fp.page_number}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Page Image */}
        <div className="flex-1 overflow-auto bg-slate-900 p-4 flex items-center justify-center">
          {pageLoading ? (
            <Skeleton className="w-full h-full max-w-4xl" />
          ) : pageImageUrl ? (
            <img
              src={pageImageUrl}
              alt={`Page ${selectedPage}`}
              className="max-w-full h-auto shadow-lg"
              style={{ transform: `scale(${zoom})` }}
            />
          ) : (
            <div className="text-slate-400">No image available</div>
          )}
        </div>

        {/* OCR Text Panel - P14: Correction Support */}
        <div className="h-64 border-t border-slate-700 bg-slate-800/50 overflow-y-auto p-4">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-medium text-slate-100">OCR Text</h4>
              {ocrTextData?.has_correction && (
                <Badge className="bg-amber-600/20 text-amber-200 border-amber-600/50 text-xs">
                  Corrected
                </Badge>
              )}
              {!editingOcr && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setOcrMode('raw');
                      loadPage();
                    }}
                    className={ocrMode === 'raw' ? 'bg-cyan-600/20' : ''}
                  >
                    Raw
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setOcrMode('effective');
                      loadPage();
                    }}
                    className={ocrMode === 'effective' ? 'bg-cyan-600/20' : ''}
                  >
                    Effective
                  </Button>
                  {ocrTextData?.has_correction && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setOcrMode('corrected');
                        loadPage();
                      }}
                      className={ocrMode === 'corrected' ? 'bg-cyan-600/20' : ''}
                    >
                      Corrected
                    </Button>
                  )}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              {!editingOcr && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setEditingOcr(true);
                      setOcrCorrectionText(ocrTextData?.corrected_text || ocrTextData?.raw_text || ocrText);
                      setOcrCorrectionNote('');
                    }}
                  >
                    Edit OCR Text
                  </Button>
                  {ocrTextData?.has_correction && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        if (confirm('Revert to raw OCR? This will delete the correction.')) {
                          try {
                            await deleteOcrTextCorrection(selectedDoc.id, selectedPage);
                            await loadPage();
                            alert('Correction reverted');
                          } catch (e: any) {
                            alert('Failed to revert: ' + (e.message || 'Unknown error'));
                          }
                        }
                      }}
                    >
                      Revert to Raw
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="default"
                    onClick={async () => {
                      setAutofilling(true);
                      try {
                        await autofillDossier(caseId, false);
                        alert('Autofill completed. Check OCR Extractions tab.');
                        router.push(`/cases/${caseId}?tab=ocr-extractions`);
                      } catch (e: any) {
                        alert('Autofill failed: ' + (e.message || 'Unknown error'));
                      } finally {
                        setAutofilling(false);
                      }
                    }}
                    disabled={autofilling}
                  >
                    {autofilling ? 'Running...' : 'Re-run Autofill'}
                  </Button>
                </>
              )}
              {selectedSnippet && !editingOcr && (currentUser?.role === 'Admin' || currentUser?.role === 'Reviewer') && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setShowSnippetModal(true)}
                >
                  Attach Selected Text
                </Button>
              )}
              {!editingOcr && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    if (ocrText) {
                      navigator.clipboard.writeText(ocrText);
                    }
                  }}
                >
                  Copy
                </Button>
              )}
            </div>
          </div>

          {editingOcr ? (
            <div className="space-y-3">
              <div className="bg-amber-900/20 border border-amber-700 rounded p-2 text-xs text-amber-200">
                You are editing OCR text corrections (does not overwrite raw OCR).
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Corrected Text</label>
                <textarea
                  value={ocrCorrectionText}
                  onChange={(e) => setOcrCorrectionText(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 font-mono text-xs"
                  rows={8}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Note <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={ocrCorrectionNote}
                  onChange={(e) => setOcrCorrectionNote(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                  rows={2}
                  placeholder="Explain the correction (min 5 characters)"
                />
                {ocrCorrectionNote.length > 0 && ocrCorrectionNote.length < 5 && (
                  <p className="text-xs text-red-400 mt-1">Note must be at least 5 characters</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditingOcr(false);
                    setOcrCorrectionText('');
                    setOcrCorrectionNote('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  onClick={async () => {
                    if (ocrCorrectionNote.trim().length < 5) {
                      alert('Note must be at least 5 characters');
                      return;
                    }
                    setSavingCorrection(true);
                    try {
                      await putOcrTextCorrection(selectedDoc.id, selectedPage, {
                        corrected_text: ocrCorrectionText,
                        note: ocrCorrectionNote,
                      });
                      setEditingOcr(false);
                      setOcrCorrectionText('');
                      setOcrCorrectionNote('');
                      await loadPage();
                      alert('Correction saved');
                    } catch (e: any) {
                      alert('Failed to save correction: ' + (e.message || 'Unknown error'));
                    } finally {
                      setSavingCorrection(false);
                    }
                  }}
                  disabled={savingCorrection || ocrCorrectionNote.trim().length < 5}
                >
                  {savingCorrection ? 'Saving...' : 'Save Correction'}
                </Button>
              </div>
            </div>
          ) : (
            <div
              className="text-xs text-slate-300 font-mono whitespace-pre-wrap select-text"
              onMouseUp={() => {
                const selection = window.getSelection();
                if (selection && selection.toString().trim()) {
                  setSelectedSnippet(selection.toString().trim());
                } else {
                  setSelectedSnippet('');
                }
              }}
            >
              {ocrText || 'OCR text not available'}
            </div>
          )}
        </div>

        {/* Snippet Attachment Modal */}
        {showSnippetModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold text-slate-100 mb-4">Attach Snippet as Evidence</h3>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-300 mb-2">Selected Text:</label>
                <div className="bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-300 max-h-32 overflow-y-auto">
                  {selectedSnippet}
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-300 mb-2">Attach to:</label>
                <select
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                  value={snippetTarget || ''}
                  onChange={(e) => {
                    setSnippetTarget(e.target.value as 'exception' | 'cp' | '');
                    setSnippetTargetId('');
                  }}
                >
                  <option value="">Select target...</option>
                  <option value="exception">Exception</option>
                  <option value="cp">Condition Precedent (CP)</option>
                </select>
              </div>

              {snippetTarget && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    {snippetTarget === 'exception' ? 'Exception:' : 'CP:'}
                  </label>
                  <select
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                    value={snippetTargetId}
                    onChange={(e) => setSnippetTargetId(e.target.value)}
                  >
                    <option value="">Select {snippetTarget === 'exception' ? 'exception' : 'CP'}...</option>
                    {snippetTarget === 'exception' && exceptions.map((exc) => (
                      <option key={exc.id} value={exc.id}>
                        {exc.title} ({exc.severity})
                      </option>
                    ))}
                    {snippetTarget === 'cp' && cps.map((cp) => (
                      <option key={cp.id} value={cp.id}>
                        {cp.text} ({cp.severity})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowSnippetModal(false);
                    setSelectedSnippet('');
                    setSnippetTarget(null);
                    setSnippetTargetId('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  disabled={!snippetTarget || !snippetTargetId || !selectedSnippet}
                  onClick={async () => {
                    if (!selectedDoc || !snippetTarget || !snippetTargetId || !selectedSnippet) return;
                    
                    try {
                      if (snippetTarget === 'exception') {
                        await attachExceptionEvidenceSnippet(
                          snippetTargetId,
                          selectedDoc.id,
                          selectedPage,
                          selectedSnippet
                        );
                      } else {
                        await attachCPEvidenceSnippet(
                          snippetTargetId,
                          selectedDoc.id,
                          selectedPage,
                          selectedSnippet
                        );
                      }

                      setShowSnippetModal(false);
                      setSelectedSnippet('');
                      setSnippetTarget(null);
                      setSnippetTargetId('');
                      alert('Snippet attached successfully!');
                    } catch (e: any) {
                      console.error('Failed to attach snippet:', e);
                      alert(`Failed to attach snippet: ${e.message || 'Unknown error'}`);
                    }
                  }}
                >
                  Attach
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

