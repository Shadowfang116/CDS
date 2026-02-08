'use client';

import { useState, useEffect, useCallback } from 'react';
import { getCaseControls, CaseControlsResponse } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { SkeletonCard } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';

interface CaseControlsCardProps {
  caseId: string;
  controls: CaseControlsResponse | null; // Passed from parent (single source of truth)
  onViewDocument?: (documentId: string) => void;
}

export function CaseControlsCard({ caseId, controls, onViewDocument }: CaseControlsCardProps) {
  // No longer fetches independently - receives controls as prop from parent
  // This prevents duplicate fetches and ensures single source of truth

  if (!controls) {
    return <SkeletonCard className="h-96" />;
  }

  const riskColor = 
    controls.risk.label === 'Green' ? 'badge-success' :
    controls.risk.label === 'Amber' ? 'badge-warning' : 'badge-error';

  const readinessColor = controls.readiness.ready ? 'badge-success' : 'badge-error';

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Controls & Evidence Checklist</CardTitle>
          <div className="flex gap-2 items-center">
            <Badge variant="default">{controls.regime.regime}</Badge>
            {controls.regime.confidence > 0 && (
              <span className="text-xs text-slate-400">
                {Math.round(controls.regime.confidence * 100)}%
              </span>
            )}
            <Badge variant={controls.risk.label === 'Green' ? 'success' : controls.risk.label === 'Amber' ? 'warning' : 'error'}>
              {controls.risk.label}
            </Badge>
            <Badge variant={controls.readiness.ready ? 'success' : 'error'}>
              {controls.readiness.ready ? 'Ready' : 'Blocked'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Active Playbooks */}
        {controls.playbooks.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-cyan-400 uppercase mb-3">Active Playbooks</h3>
            <div className="space-y-2">
              {controls.playbooks.map((pb) => (
                <div key={pb.id} className="p-3 bg-slate-700 rounded">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{pb.label}</p>
                      <p className="text-xs text-slate-400 mt-1">{pb.id}</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="neutral" size="sm">
                        {pb.rulesets.length} rulesets
                      </Badge>
                      {pb.hard_stops.length > 0 && (
                        <Badge variant="error" size="sm">
                          {pb.hard_stops.length} hard-stops
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <Separator />

        {/* Evidence Checklist */}
        <div>
          <h3 className="text-sm font-semibold text-cyan-400 uppercase mb-3">Evidence Checklist</h3>
          {controls.evidence_checklist.length === 0 ? (
            <p className="text-slate-400 text-sm">No evidence requirements defined.</p>
          ) : (
            <div className="space-y-3">
              {controls.evidence_checklist.map((item) => (
                <div key={item.code} className="p-3 bg-slate-700 rounded">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <p className="font-medium">{item.label}</p>
                      <p className="text-xs text-slate-400 mt-1">Code: {item.code}</p>
                    </div>
                    <Badge variant={item.status === 'Provided' ? 'success' : 'error'}>
                      {item.status}
                    </Badge>
                  </div>

                  {item.status === 'Provided' && item.provided_documents.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-600">
                      <p className="text-xs text-slate-400 mb-2">Provided by:</p>
                      <ul className="space-y-1">
                        {item.provided_documents.map((doc, idx) => (
                          <li key={idx} className="text-sm">
                            <button
                              onClick={() => onViewDocument?.(doc.document_id)}
                              className="text-cyan-400 hover:text-cyan-300 underline"
                            >
                              {doc.filename}
                            </button>
                            {doc.doc_type && (
                              <span className="text-slate-400 ml-2">({doc.doc_type})</span>
                            )}
                            {doc.page_count && (
                              <span className="text-slate-400 ml-1">• {doc.page_count} pages</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {item.status === 'Missing' && (
                    <div className="mt-3 pt-3 border-t border-slate-600">
                      <p className="text-xs text-slate-400 mb-2">Acceptable document types:</p>
                      <div className="flex flex-wrap gap-1">
                        {item.acceptable_doc_types.map((docType) => (
                          <Badge key={docType} variant="neutral" size="sm">
                            {docType}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <Separator />

        {/* Approval Readiness */}
        <div>
          <h3 className="text-sm font-semibold text-cyan-400 uppercase mb-3">Approval Readiness</h3>
          {controls.readiness.ready ? (
            <div className="p-3 bg-green-500/10 border border-green-500/30 rounded">
              <p className="text-sm text-green-400">
                ✓ Ready for approval (no open hard-stops).
              </p>
            </div>
          ) : (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded">
              <p className="text-sm font-medium text-red-400 mb-2">Blocked from approval:</p>
              <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                {controls.readiness.blocked_reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Go to Documents button */}
        <div className="pt-2">
          <Button
            onClick={() => {
              // Navigate to documents tab (this will be handled by parent)
              if (typeof window !== 'undefined') {
                const event = new CustomEvent('navigateToTab', { detail: 'documents' });
                window.dispatchEvent(event);
              }
            }}
            variant="secondary"
            className="w-full"
          >
            Go to Documents
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

