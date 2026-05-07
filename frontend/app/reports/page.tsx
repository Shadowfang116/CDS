'use client';

import { useState, useEffect, useCallback } from 'react';
import { SetPageChrome } from '@/components/layout/set-page-chrome';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import {
  listCases,
  listExports,
  generateBankPack,
  generateDiscrepancyLetter,
  getExportDownloadUrl,
} from '@/lib/api';

export default function ReportsPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [exports, setExports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadExports = useCallback(async (caseId: string) => {
    try {
      const data = await listExports(caseId);
      setExports(data.exports || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load exports');
    }
  }, []);

  const loadCases = useCallback(async () => {
    try {
      const data = await listCases();
      const arr = Array.isArray(data)
        ? data
        : Array.isArray((data as any)?.value)
          ? (data as any).value
          : [];
      setCases(arr);
      if (arr.length > 0 && !selectedCaseId) {
        setSelectedCaseId(arr[0].id);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load cases');
    } finally {
      setLoading(false);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  useEffect(() => {
    if (selectedCaseId) {
      void loadExports(selectedCaseId);
    }
  }, [selectedCaseId, loadExports]);

  const handleGenerate = async (type: 'bank-pack' | 'discrepancy-letter') => {
    if (!selectedCaseId) return;
    
    setGenerating(type);
    setError(null);
    try {
      let result;
      if (type === 'bank-pack') {
        result = await generateBankPack(selectedCaseId);
      } else {
        result = await generateDiscrepancyLetter(selectedCaseId);
      }
      
      // Download the file
      window.open(result.url, '_blank');
      
      // Reload exports
      await loadExports(selectedCaseId);
    } catch (e: any) {
      setError(e.message || 'Failed to generate export');
    } finally {
      setGenerating(null);
    }
  };

  const handleDownload = async (exportId: string) => {
    try {
      const result = await getExportDownloadUrl(exportId);
      window.open(result.url, '_blank');
    } catch (e: any) {
      setError(e.message || 'Failed to download');
    }
  };

  return (
    <>
      <SetPageChrome
        title="Reports"
        breadcrumbs={[{ label: 'Reports' }]}
      />
      <div className="space-y-6" data-dashboard-reveal>
        {error && (
          <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-[rgb(219,156,153)]">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-dashboard-section>
          {/* Case Selection */}
          <div className="lg:col-span-1">
            <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Select Case</div>
            {loading ? (
              <Skeleton className="h-32 w-full" />
            ) : cases.length === 0 ? (
              <EmptyState message="No cases available" />
            ) : (
              <div className="space-y-2">
                {(Array.isArray(cases) ? cases : (Array.isArray((cases as any)?.value) ? (cases as any).value : [])).map((case_: any) => (
                  <button
                    key={case_.id}
                    onClick={() => setSelectedCaseId(case_.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedCaseId === case_.id
                        ? 'border-[rgba(126,133,111,0.4)] bg-[rgba(126,133,111,0.12)] text-stone-100'
                        : 'border-[rgba(82,90,99,0.42)] bg-[rgba(24,28,32,0.88)] text-stone-300 hover:bg-[rgba(34,39,45,0.92)]'
                    }`}
                  >
                    <div className="font-medium">{case_.title}</div>
                    <div className="mt-1 text-xs text-stone-500">{case_.status}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Export Generation */}
          <div className="lg:col-span-2 space-y-6">
            <div>
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Generate Reports</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-4">
                  <h4 className="mb-2 font-medium text-stone-100">Bank Pack PDF</h4>
                  <p className="mb-4 text-sm text-stone-400">
                    Complete case summary with all documents, exceptions, and CPs
                  </p>
                  <Button
                    onClick={() => handleGenerate('bank-pack')}
                    disabled={!selectedCaseId || generating === 'bank-pack'}
                    className="w-full"
                  >
                    {generating === 'bank-pack' ? 'Generating...' : 'Generate Bank Pack'}
                  </Button>
                </div>

                <div className="card p-4">
                  <h4 className="mb-2 font-medium text-stone-100">Discrepancy Letter</h4>
                  <p className="mb-4 text-sm text-stone-400">
                    DOCX letter highlighting exceptions and required actions
                  </p>
                  <Button
                    onClick={() => handleGenerate('discrepancy-letter')}
                    disabled={!selectedCaseId || generating === 'discrepancy-letter'}
                    variant="outline"
                    className="w-full"
                  >
                    {generating === 'discrepancy-letter' ? 'Generating...' : 'Generate Letter'}
                  </Button>
                </div>
              </div>
            </div>

            {/* Export History */}
            <div>
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">Recent Exports</div>
              {exports.length === 0 ? (
                <EmptyState message="No exports generated yet" />
              ) : (
                <div className="space-y-2">
                  {exports.slice(0, 10).map((exp) => (
                    <div
                      key={exp.id}
                      className="card p-3 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-medium text-stone-100">{exp.filename}</div>
                        <div className="mt-1 text-xs text-stone-500">
                          {new Date(exp.created_at).toLocaleString()}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownload(exp.id)}
                      >
                        Download
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}


