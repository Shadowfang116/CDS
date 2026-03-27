'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
// Label component - create simple one if not available
const Label = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <label className={`text-sm font-medium ${className}`}>{children}</label>
);
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import {
  getPageOcrReview,
  setPageOcrOverride,
  clearPageOcrOverride,
  rerunPageOcr,
  type OcrReviewResponse,
  type OcrRerunRequest,
} from '@/lib/api';

export default function OcrReviewPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useCurrentUser();
  
  const caseId = params.caseId as string;
  const documentId = params.documentId as string;
  const pageNumber = parseInt(params.pageNumber as string);
  
  const [data, setData] = useState<OcrReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [overrideText, setOverrideText] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [savingOverride, setSavingOverride] = useState(false);
  const [clearingOverride, setClearingOverride] = useState(false);
  const [rerunDialogOpen, setRerunDialogOpen] = useState(false);
  const [rerunOptions, setRerunOptions] = useState<OcrRerunRequest>({});
  const [rerunning, setRerunning] = useState(false);
  
  const canEdit = user && ['Admin', 'Approver', 'Reviewer'].includes(user.role);
  
  useEffect(() => {
    loadData();
  }, [caseId, documentId, pageNumber]);
  
  const loadData = async () => {
    try {
      setLoading(true);
      const result = await getPageOcrReview(caseId, documentId, pageNumber);
      setData(result);
      setOverrideText(result.ocr.text);
    } catch (error: any) {
      alert('Error: ' + (error.message || 'Failed to load OCR review data'));
    } finally {
      setLoading(false);
    }
  };
  
  const handleSaveOverride = async () => {
    if (!overrideText.trim()) {
      alert('Error: Override text cannot be empty');
      return;
    }
    
    try {
      setSavingOverride(true);
      await setPageOcrOverride(caseId, documentId, pageNumber, {
        override_text: overrideText,
        reason: overrideReason || undefined,
      });
      alert('Success: Override saved successfully');
      await loadData();
    } catch (error: any) {
      alert('Error: ' + (error.message || 'Failed to save override'));
    } finally {
      setSavingOverride(false);
    }
  };
  
  const handleClearOverride = async () => {
    try {
      setClearingOverride(true);
      await clearPageOcrOverride(caseId, documentId, pageNumber);
      alert('Success: Override cleared successfully');
      await loadData();
    } catch (error: any) {
      alert('Error: ' + (error.message || 'Failed to clear override'));
    } finally {
      setClearingOverride(false);
    }
  };
  
  const handleRerun = async () => {
    try {
      setRerunning(true);
      await rerunPageOcr(caseId, documentId, pageNumber, rerunOptions);
      alert('Queued: OCR rerun queued. Refresh to see updated OCR.');
      setRerunDialogOpen(false);
      // Auto-refresh after a delay
      setTimeout(() => {
        loadData();
      }, 2000);
    } catch (error: any) {
      alert('Error: ' + (error.message || 'Failed to queue OCR rerun'));
    } finally {
      setRerunning(false);
    }
  };
  
  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-red-500">Failed to load OCR review data</div>
      </div>
    );
  }
  
  const domainHints = data.meta?.domain_ur?.hints || [];
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => router.back()}
            className="text-sm text-muted-foreground hover:text-foreground mb-2"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold">OCR Review</h1>
          <p className="text-sm text-muted-foreground">
            Case: {caseId} • Document: {documentId} • Page: {pageNumber}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData}>
            Refresh
          </Button>
          {canEdit && (
            <Dialog open={rerunDialogOpen} onOpenChange={setRerunDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">Re-run OCR</Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Re-run OCR Options</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label>Preprocessing Profile</Label>
                    <select
                      value={rerunOptions.force_profile || ''}
                      onChange={(e) => setRerunOptions({ ...rerunOptions, force_profile: e.target.value as any || undefined })}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="">Use default</option>
                      <option value="basic">Basic</option>
                      <option value="enhanced">Enhanced</option>
                    </select>
                  </div>
                  <div>
                    <Label>Language</Label>
                    <select
                      value={rerunOptions.force_lang || ''}
                      onChange={(e) => setRerunOptions({ ...rerunOptions, force_lang: e.target.value as any || undefined })}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="">Use default</option>
                      <option value="eng">English</option>
                      <option value="urd">Urdu</option>
                      <option value="urd+eng">Urdu + English</option>
                    </select>
                  </div>
                  <div>
                    <Label>Engine Mode</Label>
                    <select
                      value={rerunOptions.engine_mode || ''}
                      onChange={(e) => setRerunOptions({ ...rerunOptions, engine_mode: e.target.value as any || undefined })}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="">Use default</option>
                      <option value="tesseract">Tesseract</option>
                      <option value="ensemble">Ensemble (Tesseract + PaddleOCR)</option>
                    </select>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={rerunOptions.force_detect ?? false}
                      onChange={(e) => setRerunOptions({ ...rerunOptions, force_detect: e.target.checked || undefined })}
                      className="h-4 w-4"
                    />
                    <Label>Force Script Detection</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={rerunOptions.force_layout ?? false}
                      onChange={(e) => setRerunOptions({ ...rerunOptions, force_layout: e.target.checked || undefined })}
                      className="h-4 w-4"
                    />
                    <Label>Force Layout Segmentation</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={rerunOptions.force_pdf_text_layer ?? false}
                      onChange={(e) => setRerunOptions({ ...rerunOptions, force_pdf_text_layer: e.target.checked || undefined })}
                      className="h-4 w-4"
                    />
                    <Label>Force PDF Text Layer</Label>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setRerunDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleRerun} disabled={rerunning}>
                      {rerunning ? 'Queuing...' : 'Queue Rerun'}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>
      
      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Page Image */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Page Image</h2>
          <div className="border rounded-lg overflow-hidden bg-gray-50">
            <img
              src={data.image_url}
              alt={`Page ${pageNumber}`}
              className="w-full h-auto max-h-[600px] object-contain"
            />
          </div>
        </div>
        
        {/* Right: OCR Content */}
        <div className="space-y-4">
          <Tabs defaultValue="text" className="w-full">
            <TabsList>
              <TabsTrigger value="text">Effective Text</TabsTrigger>
              <TabsTrigger value="metadata">Metadata</TabsTrigger>
              {domainHints.length > 0 && (
                <TabsTrigger value="hints">Hints ({domainHints.length})</TabsTrigger>
              )}
            </TabsList>
            
            <TabsContent value="text" className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant={data.ocr.source === 'override' ? 'default' : 'outline'}>
                  {data.ocr.source === 'override' ? 'Override' : 'OCR'}
                </Badge>
                {data.ocr.confidence !== null && (
                  <Badge variant="outline">
                    Confidence: {(data.ocr.confidence * 100).toFixed(1)}%
                  </Badge>
                )}
              </div>
              
              {data.ocr.has_override && data.ocr.override && (
                <div className="text-sm text-muted-foreground">
                  Override by user {data.ocr.override.user_id} on {new Date(data.ocr.override.updated_at || '').toLocaleString()}
                  {data.ocr.override.reason && ` • Reason: ${data.ocr.override.reason}`}
                </div>
              )}
              
              <div>
                <Label>Text</Label>
                <Textarea
                  value={overrideText}
                  onChange={(e) => setOverrideText(e.target.value)}
                  readOnly={!canEdit}
                  className="min-h-[300px] font-mono text-sm"
                />
              </div>
              
              {canEdit && (
                <div className="space-y-2">
                  <div>
                    <Label>Reason (optional)</Label>
                    <Textarea
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="Reason for override..."
                      className="min-h-[60px]"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={handleSaveOverride}
                      disabled={savingOverride}
                    >
                      {savingOverride ? 'Saving...' : 'Save Override'}
                    </Button>
                    {data.ocr.has_override && (
                      <Button
                        variant="outline"
                        onClick={handleClearOverride}
                        disabled={clearingOverride}
                      >
                        {clearingOverride ? 'Clearing...' : 'Clear Override'}
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="metadata">
              <div className="border rounded-lg p-4 bg-gray-50">
                <pre className="text-xs overflow-auto max-h-[500px]">
                  {JSON.stringify(data.meta, null, 2)}
                </pre>
              </div>
            </TabsContent>
            
            {domainHints.length > 0 && (
              <TabsContent value="hints">
                <div className="space-y-2">
                  {domainHints.slice(0, 20).map((hint: any, idx: number) => (
                    <div key={idx} className="border rounded p-2">
                      <div className="font-semibold">{hint.type}</div>
                      <div className="text-sm text-muted-foreground">
                        Value: {hint.value || 'N/A'}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Raw: {hint.raw} • Confidence: {hint.confidence}
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
            )}
          </Tabs>
        </div>
      </div>
    </div>
  );
}
