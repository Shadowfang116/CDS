'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AppShell } from '@/components/app/AppShell';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  const router = useRouter();
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [exports, setExports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadExports(selectedCaseId);
    }
  }, [selectedCaseId]);

  const loadCases = async () => {
    try {
      const data = await listCases();
      setCases(data);
      if (data.length > 0 && !selectedCaseId) {
        setSelectedCaseId(data[0].id);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load cases');
    } finally {
      setLoading(false);
    }
  };

  const loadExports = async (caseId: string) => {
    try {
      const data = await listExports(caseId);
      setExports(data.exports || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load exports');
    }
  };

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
    <AppShell pageTitle="Reports">
      <div className="p-6 space-y-6">
        {error && (
          <div className="bg-red-900/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Case Selection */}
          <div className="lg:col-span-1">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Select Case</h3>
            {loading ? (
              <Skeleton className="h-32 w-full" />
            ) : cases.length === 0 ? (
              <EmptyState message="No cases available" />
            ) : (
              <div className="space-y-2">
                {cases.map((case_) => (
                  <button
                    key={case_.id}
                    onClick={() => setSelectedCaseId(case_.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedCaseId === case_.id
                        ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400'
                        : 'bg-slate-800/50 border-slate-700 text-slate-300 hover:bg-slate-700/50'
                    }`}
                  >
                    <div className="font-medium">{case_.title}</div>
                    <div className="text-xs text-slate-500 mt-1">{case_.status}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Export Generation */}
          <div className="lg:col-span-2 space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-100 mb-4">Generate Reports</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <h4 className="font-medium text-slate-100 mb-2">Bank Pack PDF</h4>
                  <p className="text-sm text-slate-400 mb-4">
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

                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <h4 className="font-medium text-slate-100 mb-2">Discrepancy Letter</h4>
                  <p className="text-sm text-slate-400 mb-4">
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
              <h3 className="text-lg font-semibold text-slate-100 mb-4">Recent Exports</h3>
              {exports.length === 0 ? (
                <EmptyState message="No exports generated yet" />
              ) : (
                <div className="space-y-2">
                  {exports.slice(0, 10).map((exp) => (
                    <div
                      key={exp.id}
                      className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 flex justify-between items-center"
                    >
                      <div>
                        <div className="font-medium text-slate-100">{exp.filename}</div>
                        <div className="text-xs text-slate-500 mt-1">
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
    </AppShell>
  );
}

