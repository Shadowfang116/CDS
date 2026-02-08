'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { getDossierFields, patchDossierField, getDossierFieldHistory, listDocuments, getMe, DossierFieldItem, DossierFieldHistoryItem } from '@/lib/api';

interface DossierFieldsEditorProps {
  caseId: string;
  documents?: any[]; // Passed from parent (single source of truth) - if provided, don't fetch independently
}

const CRITICAL_FIELDS = new Set([
  'property.plot_number',
  'property.khasra_numbers',
  'registration.registry_number',
  'stamp.estamp_id_or_number',
]);

const FIELD_SECTIONS: Record<string, string[]> = {
  Property: [
    'property.plot_number',
    'property.block',
    'property.phase',
    'property.scheme_name',
    'property.khasra_numbers',
    'property.location',
  ],
  Parties: [
    'party.name.borrower',
    'party.name.seller',
    'party.seller.names',
    'party.buyer.names',
    'party.witness.names',
    'party.cnic',
  ],
  Registration: [
    'registration.registry_number',
    'registration.registry_date',
    'registration.registry_office',
  ],
  Stamp: [
    'stamp.estamp_id_or_number',
    'stamp.stamp_paper_value',
  ],
  Possession: [
    'possession.status',
    'possession.date',
  ],
};

function getFieldSection(fieldKey: string): string {
  for (const [section, keys] of Object.entries(FIELD_SECTIONS)) {
    if (keys.includes(fieldKey)) {
      return section;
    }
  }
  return 'Other';
}

function getFieldLabel(fieldKey: string): string {
  // Custom labels for specific fields
  const customLabels: Record<string, string> = {
    'party.seller.names': 'Seller(s)',
    'party.buyer.names': 'Buyer(s)',
    'party.witness.names': 'Witness(es)',
    'party.name.borrower': 'Borrower',
    'party.name.seller': 'Seller',
    'party.cnic': 'CNIC',
  };
  
  if (customLabels[fieldKey]) {
    return customLabels[fieldKey];
  }
  
  // Default: capitalize last part
  const parts = fieldKey.split('.');
  return parts[parts.length - 1].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

export function DossierFieldsEditor({ caseId, documents: documentsProp }: DossierFieldsEditorProps) {
  const router = useRouter();
  const [fields, setFields] = useState<DossierFieldItem[]>([]);
  // Use documents from prop if provided (single source of truth), otherwise fetch independently
  const [documentsState, setDocumentsState] = useState<any[]>([]);
  const documents = documentsProp ?? documentsState;
  const [loading, setLoading] = useState(true);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [historyField, setHistoryField] = useState<string | null>(null);
  const [history, setHistory] = useState<DossierFieldHistoryItem[]>([]);
  const [userRole, setUserRole] = useState<string>('Reviewer');
  const [editForm, setEditForm] = useState({
    value: '',
    note: '',
    documentId: '',
    pageNumber: '',
    force: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedRef = useRef<{ caseId: string | null }>({ caseId: null });

  const loadData = useCallback(async () => {
    // Skip if documents are provided as prop
    if (documentsProp) {
      setLoading(true);
      try {
        const [fieldsData, userData] = await Promise.all([
          getDossierFields(caseId),
          getMe(),
        ]);
        setFields(fieldsData.fields);
        if (userData?.role) {
          setUserRole(userData.role);
        }
        loadedRef.current.caseId = caseId;
      } catch (e: any) {
        console.error('Failed to load data:', e);
      } finally {
        setLoading(false);
      }
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
    
    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    setLoading(true);
    try {
      const [fieldsData, docsData, userData] = await Promise.all([
        getDossierFields(caseId),
        listDocuments(caseId),
        getMe(),
      ]);
      
      // Check if request was aborted
      if (abortController.signal.aborted) {
        return;
      }
      
      setFields(fieldsData.fields);
      setDocumentsState(docsData);
      if (userData?.role) {
        setUserRole(userData.role);
      }
      loadedRef.current.caseId = caseId;
    } catch (e: any) {
      if (e.name === 'AbortError') {
        return; // Ignore abort errors
      }
      console.error('Failed to load data:', e);
    } finally {
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    }
  }, [caseId, documentsProp]);

  useEffect(() => {
    loadData();
    
    // Cleanup: abort in-flight request on unmount or caseId change
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadData]);

  const handleEdit = (field: DossierFieldItem) => {
    setEditingField(field.field_key);
    setEditForm({
      value: field.field_value || '',
      note: '',
      documentId: field.source_document_id || '',
      pageNumber: field.source_page_number?.toString() || '',
      force: false,
    });
    setError(null);
  };

  const handleSave = async () => {
    if (!editingField) return;

    if (editForm.note.trim().length < 5) {
      setError('Note is required and must be at least 5 characters');
      return;
    }

    const isCritical = CRITICAL_FIELDS.has(editingField);
    const hasEvidence = editForm.documentId && editForm.pageNumber;

    if (isCritical && !hasEvidence && !editForm.force) {
      setError('Evidence is required for critical fields. Select a document and page, or use Force (Admin only)');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const evidence = editForm.documentId && editForm.pageNumber ? {
        document_id: editForm.documentId,
        page_number: parseInt(editForm.pageNumber),
      } : undefined;

      const updated = await patchDossierField(caseId, editingField, {
        value: editForm.value,
        note: editForm.note,
        evidence,
        force: editForm.force,
      });

      // Optimistically update
      setFields(prev => prev.map(f => f.field_key === editingField ? updated : f));
      setEditingField(null);
      setEditForm({ value: '', note: '', documentId: '', pageNumber: '', force: false });
      
      // Show toast (simple alert for now)
      alert('Field updated successfully');
    } catch (e: any) {
      const errorMsg = e.message || 'Failed to update field';
      setError(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleViewHistory = async (fieldKey: string) => {
    setHistoryField(fieldKey);
    try {
      const data = await getDossierFieldHistory(caseId, fieldKey);
      setHistory(data.history);
    } catch (e: any) {
      console.error('Failed to load history:', e);
      setHistory([]);
    }
  };

  const handleEvidenceClick = (docId: string, pageNum: number) => {
    router.push(`/cases/${caseId}?tab=documents&docId=${docId}&page=${pageNum}`);
  };

  const groupedFields: Record<string, DossierFieldItem[]> = {};
  fields.forEach(field => {
    const section = getFieldSection(field.field_key);
    if (!groupedFields[section]) {
      groupedFields[section] = [];
    }
    groupedFields[section].push(field);
  });

  if (loading) {
    return <div className="text-slate-400">Loading dossier fields...</div>;
  }

  return (
    <div className="space-y-6">
      {Object.entries(groupedFields).map(([section, sectionFields]) => (
        <div key={section} className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">{section}</h3>
          <div className="space-y-3">
            {sectionFields.map(field => (
              <div key={field.field_key} className="bg-slate-900 border border-slate-700 rounded p-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium text-cyan-400">{getFieldLabel(field.field_key)}</span>
                      <span className="text-xs text-slate-500">({field.field_key})</span>
                      {CRITICAL_FIELDS.has(field.field_key) && (
                        <Badge variant="destructive" className="text-xs">Critical</Badge>
                      )}
                      {field.last_edited_by && (
                        <Badge variant="outline" className="text-xs">
                          {field.last_edited_by === 'extraction_confirm' ? 'Extraction' : 
                           field.last_edited_by === 'autofill' ? 'Autofill' : 'Manual'}
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-slate-300 mb-2">
                      {field.field_value || <span className="text-slate-500">—</span>}
                    </div>
                    {field.source_document_id && field.source_page_number && (
                      <button
                        onClick={() => handleEvidenceClick(field.source_document_id!, field.source_page_number!)}
                        className="text-xs text-cyan-400 hover:text-cyan-300 underline"
                      >
                        {documents.find(d => d.id === field.source_document_id)?.original_filename || 'Doc'} p.{field.source_page_number}
                      </button>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleEdit(field)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleViewHistory(field.field_key)}>
                      History
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Edit Modal */}
      {editingField && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">
              Edit Field: {getFieldLabel(editingField)}
            </h3>

            {error && (
              <div className="mb-4 p-3 bg-red-900/20 border border-red-700 rounded text-red-300 text-sm">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Value</label>
                <input
                  type="text"
                  value={editForm.value}
                  onChange={(e) => setEditForm({ ...editForm, value: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Note <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={editForm.note}
                  onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                  rows={3}
                  placeholder="Explain why you are editing this field (min 5 characters)"
                />
                {editForm.note.length > 0 && editForm.note.length < 5 && (
                  <p className="text-xs text-red-400 mt-1">Note must be at least 5 characters</p>
                )}
              </div>

              {CRITICAL_FIELDS.has(editingField) && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Evidence <span className="text-red-400">*</span> (or use Force below)
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={editForm.documentId}
                      onChange={(e) => setEditForm({ ...editForm, documentId: e.target.value })}
                      className="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                    >
                      <option value="">Select document</option>
                      {documents.map(doc => (
                        <option key={doc.id} value={doc.id}>{doc.original_filename}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={editForm.pageNumber}
                      onChange={(e) => setEditForm({ ...editForm, pageNumber: e.target.value })}
                      placeholder="Page number"
                      className="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
                      min="1"
                    />
                  </div>
                </div>
              )}

              {CRITICAL_FIELDS.has(editingField) && userRole === 'Admin' && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="force"
                    checked={editForm.force}
                    onChange={(e) => setEditForm({ ...editForm, force: e.target.checked })}
                    disabled={!!(editForm.documentId && editForm.pageNumber)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="force" className="text-sm text-slate-300">
                    Force (no evidence) - Admin only
                  </label>
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setEditingField(null)}>
                  Cancel
                </Button>
                <Button
                  variant="default"
                  onClick={handleSave}
                  disabled={saving || editForm.note.trim().length < 5}
                >
                  {saving ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History Drawer */}
      {historyField && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-slate-100">
                History: {getFieldLabel(historyField)}
              </h3>
              <Button variant="outline" size="sm" onClick={() => setHistoryField(null)}>
                Close
              </Button>
            </div>
            <div className="space-y-3">
              {history.length === 0 ? (
                <p className="text-slate-400">No history available</p>
              ) : (
                history.map((entry) => (
                  <div key={entry.id} className="bg-slate-900 border border-slate-700 rounded p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="text-sm font-medium text-slate-300">{entry.edited_by}</span>
                        <span className="text-xs text-slate-500 ml-2">
                          {new Date(entry.edited_at).toLocaleString()}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-xs">{entry.source_type}</Badge>
                    </div>
                    <div className="text-sm text-slate-400 mb-2">
                      <span className="line-through">{entry.old_value || '—'}</span>
                      {' → '}
                      <span className="text-slate-300">{entry.new_value || '—'}</span>
                    </div>
                    {entry.note && (
                      <p className="text-xs text-slate-500 mb-2">Note: {entry.note}</p>
                    )}
                    {entry.source_document_id && entry.source_page_number && (
                      <button
                        onClick={() => handleEvidenceClick(entry.source_document_id!, entry.source_page_number!)}
                        className="text-xs text-cyan-400 hover:text-cyan-300 underline"
                      >
                        Evidence: Doc p.{entry.source_page_number}
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

