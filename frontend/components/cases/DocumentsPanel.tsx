'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { CaseDocumentItem, enqueueOcr, listDocuments, uploadDocument } from '@/lib/api';
import { DocumentViewer } from '@/components/documents/DocumentViewer';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/toast';
import { cn } from '@/lib/utils';

type DocumentsPanelProps = {
  caseId: string;
  documents?: CaseDocumentItem[];
  initialDocumentId?: string | null;
  initialPage?: number | null;
  onDocumentsChange?: (documents: CaseDocumentItem[]) => void;
};

type UploadQueueStatus = 'queued' | 'uploading' | 'done' | 'error';

type UploadQueueItem = {
  id: string;
  file: File;
  status: UploadQueueStatus;
  errorMsg?: string;
};

const ACCEPTED_FILE_TYPES =
  'application/pdf,image/png,image/jpeg,image/jpg,image/tiff,image/tif,application/vnd.openxmlformats-officedocument.wordprocessingml.document';

const IN_PROGRESS_DOCUMENT_STATUSES = new Set([
  'uploaded',
  'queued',
  'preprocessing',
  'ocr_in_progress',
  'extracting',
  'rules_evaluation',
  'processing',
]);

const TERMINAL_DOCUMENT_STATUSES = new Set(['complete', 'completed', 'needs_review', 'failed']);

function normalizeDocumentStatus(status?: string | null): string {
  return (status ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_');
}

function hasInProgressDocuments(documents: CaseDocumentItem[]): boolean {
  return documents.some((document) => {
    const normalizedStatus = normalizeDocumentStatus(document.status);
    if (!normalizedStatus || TERMINAL_DOCUMENT_STATUSES.has(normalizedStatus)) {
      return false;
    }

    return IN_PROGRESS_DOCUMENT_STATUSES.has(normalizedStatus);
  });
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getQueueStatusVariant(status: UploadQueueStatus): 'outline' | 'info' | 'success' | 'error' {
  switch (status) {
    case 'uploading':
      return 'info';
    case 'done':
      return 'success';
    case 'error':
      return 'error';
    default:
      return 'outline';
  }
}

export function DocumentsPanel({
  caseId,
  documents = [],
  initialDocumentId,
  initialPage,
  onDocumentsChange,
}: DocumentsPanelProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [uploading, setUploading] = useState(false);
  const [ocrRunning, setOcrRunning] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [panelError, setPanelError] = useState<string | null>(null);
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | undefined>(initialDocumentId ?? undefined);
  const [selectedPage, setSelectedPage] = useState<number | undefined>(
    typeof initialPage === 'number' && initialPage >= 1 ? initialPage : undefined
  );

  useEffect(() => {
    if (initialDocumentId) {
      setSelectedDocumentId(initialDocumentId);
    }
    if (typeof initialPage === 'number' && initialPage >= 1) {
      setSelectedPage(initialPage);
    }
  }, [initialDocumentId, initialPage]);

  const refreshDocuments = useCallback(async () => {
    const nextDocuments = await listDocuments(caseId);
    const normalizedDocuments = Array.isArray(nextDocuments) ? nextDocuments : [];
    onDocumentsChange?.(normalizedDocuments);
    return normalizedDocuments;
  }, [caseId, onDocumentsChange]);

  const setQueueItemStatus = useCallback(
    (id: string, status: UploadQueueStatus, errorMsg?: string) => {
      setUploadQueue((currentQueue) =>
        currentQueue.map((item) =>
          item.id === id
            ? {
                ...item,
                status,
                errorMsg,
              }
            : item
        )
      );
    },
    []
  );

  const enqueueFiles = useCallback((files: File[]) => {
    if (files.length === 0) {
      return;
    }

    const queuedItems = files.map((file, index) => ({
      id: `upload-${Date.now()}-${index}-${file.name}`,
      file,
      status: 'queued' as const,
    }));

    setPanelError(null);
    setUploadQueue((currentQueue) => [...currentQueue, ...queuedItems]);
  }, []);

  const processUploadQueue = useCallback(async () => {
    if (uploading) {
      return;
    }

    const queuedItems = uploadQueue.filter((item) => item.status === 'queued');
    if (queuedItems.length === 0) {
      return;
    }

    setUploading(true);
    toast({
      title: queuedItems.length > 1 ? 'Uploads started.' : 'Upload started.',
      description: 'Document processing will continue in the background.',
      variant: 'info',
    });

    const knownDocumentIds = new Set(documents.map((document) => document.id));
    let latestSelectedId: string | undefined;
    let successfulUploads = 0;
    let failedUploads = 0;

    try {
      for (const queueItem of queuedItems) {
        setQueueItemStatus(queueItem.id, 'uploading');

        try {
          await uploadDocument(caseId, queueItem.file);
          const nextDocuments = await refreshDocuments();
          const uploadedDocument = nextDocuments.find((document) => document.id && !knownDocumentIds.has(document.id));

          nextDocuments.forEach((document) => {
            if (document.id) {
              knownDocumentIds.add(document.id);
            }
          });

          if (uploadedDocument?.id) {
            latestSelectedId = uploadedDocument.id;
          }

          successfulUploads += 1;
          setQueueItemStatus(queueItem.id, 'done');
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to upload document';
          failedUploads += 1;
          setPanelError(errorMessage);
          setQueueItemStatus(queueItem.id, 'error', errorMessage);
        }
      }

      if (latestSelectedId) {
        setSelectedDocumentId(latestSelectedId);
        setSelectedPage(1);
      }

      if (successfulUploads > 0 && failedUploads === 0) {
        toast({
          title: successfulUploads > 1 ? 'Uploads accepted.' : 'Upload accepted.',
          description: 'The document is now available in the reviewer workspace.',
          variant: 'success',
        });
      } else if (successfulUploads > 0 || failedUploads > 0) {
        toast({
          title: 'Upload batch finished.',
          description: `${successfulUploads} succeeded, ${failedUploads} failed.`,
          variant: failedUploads > 0 ? 'error' : 'success',
        });
      }
    } finally {
      setUploading(false);
    }
  }, [caseId, documents, refreshDocuments, setQueueItemStatus, toast, uploadQueue, uploading]);

  useEffect(() => {
    if (!uploading && uploadQueue.some((item) => item.status === 'queued')) {
      void processUploadQueue();
    }
  }, [processUploadQueue, uploadQueue, uploading]);

  useEffect(() => {
    if (!hasInProgressDocuments(documents)) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    if (pollIntervalRef.current) {
      return;
    }

    pollIntervalRef.current = setInterval(() => {
      void refreshDocuments().catch(() => {
        // Ignore background refresh failures and keep the current UI state.
      });
    }, 5000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [documents, refreshDocuments]);

  const handleBeginOcr = useCallback(async () => {
    const eligible = documents.filter((doc) => {
      const s = normalizeDocumentStatus(doc.status);
      return s === 'uploaded' || s === 'split' || s === 'queued';
    });

    if (eligible.length === 0) {
      toast({
        title: 'No documents ready for OCR.',
        description: 'Upload documents first, or wait for pre-processing to complete.',
        variant: 'info',
      });
      return;
    }

    setOcrRunning(true);
    let succeeded = 0;
    let failed = 0;

    for (const doc of eligible) {
      try {
        await enqueueOcr(doc.id, false);
        succeeded += 1;
      } catch {
        failed += 1;
      }
    }

    setOcrRunning(false);

    if (failed === 0) {
      toast({
        title: 'OCR started.',
        description: `${succeeded} document${succeeded === 1 ? '' : 's'} queued for processing.`,
        variant: 'success',
      });
    } else {
      toast({
        title: 'OCR partially started.',
        description: `${succeeded} queued, ${failed} failed.`,
        variant: 'error',
      });
    }

    void refreshDocuments().catch(() => undefined);
  }, [documents, refreshDocuments, toast]);

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    enqueueFiles(files);
    event.target.value = '';
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    const files = Array.from(event.dataTransfer.files ?? []);
    enqueueFiles(files);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>Documents</CardTitle>
            <p className="mt-1 text-sm text-stone-400">
              Review annexures, inspect OCR page text, and attach evidence from a single workspace.
            </p>
          </div>
          <div className="shrink-0">
            <Button
              variant="outline"
              onClick={() => void handleBeginOcr()}
              disabled={ocrRunning || uploading}
              loading={ocrRunning}
            >
              {ocrRunning ? 'Starting OCR…' : 'Begin OCR'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div
            className={cn(
              'rounded-lg border border-dashed px-4 py-4 transition-colors',
              dragActive
                ? 'border-[rgba(152,161,135,0.44)] bg-[rgba(152,161,135,0.08)]'
                : 'border-[rgba(82,90,99,0.42)] bg-[rgba(18,22,27,0.62)]'
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-medium text-stone-200">Add one or more files</p>
                <p className="mt-1 text-xs text-stone-500">
                  Drag PDFs, PNG/JPG/TIFF images, or DOCX files here, or browse from disk.
                </p>
              </div>
              <div className="relative">
                <Button onClick={() => fileInputRef.current?.click()} disabled={uploading} loading={uploading}>
                  {uploading ? 'Uploading...' : 'Upload Files'}
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_FILE_TYPES}
                  multiple
                  onChange={handleInputChange}
                  className="sr-only"
                  tabIndex={-1}
                />
              </div>
            </div>

            {uploadQueue.length > 0 ? (
              <div className="mt-4 space-y-2 border-t border-[rgba(82,90,99,0.28)] pt-4">
                {uploadQueue.map((queueItem) => (
                  <div
                    key={queueItem.id}
                    className="flex flex-col gap-2 rounded-md border border-[rgba(82,90,99,0.28)] bg-[rgba(14,18,22,0.48)] px-3 py-2 lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-stone-200">{queueItem.file.name}</div>
                      <div className="mt-0.5 text-xs text-stone-500">{formatFileSize(queueItem.file.size)}</div>
                      {queueItem.errorMsg ? (
                        <div className="mt-1 text-xs text-[rgb(219,156,153)]">{queueItem.errorMsg}</div>
                      ) : null}
                    </div>
                    <Badge variant={getQueueStatusVariant(queueItem.status)} className="w-fit text-xs">
                      {queueItem.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </CardContent>
        {panelError ? (
          <CardContent className="pt-0">
            <div className="rounded-lg border border-[rgba(189,90,86,0.36)] bg-[rgba(189,90,86,0.12)] px-4 py-3 text-sm text-[rgb(219,156,153)]">
              {panelError}
            </div>
          </CardContent>
        ) : null}
      </Card>

      <div className="overflow-hidden rounded-lg border border-[rgba(82,90,99,0.4)] bg-[linear-gradient(180deg,rgba(23,28,33,0.96),rgba(17,21,25,0.96))]">
        <DocumentViewer
          caseId={caseId}
          documents={documents}
          initialDocId={selectedDocumentId}
          initialPage={selectedPage}
          onUploadRequest={() => fileInputRef.current?.click()}
          onDocumentDeleted={() => void refreshDocuments()}
        />
      </div>
    </div>
  );
}
