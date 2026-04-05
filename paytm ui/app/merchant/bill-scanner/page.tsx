'use client';

import { useMemo, useRef, useState } from 'react';
import { FileUp, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import type { OCRStructuredResult } from '@/src/adapters/types';
import { DataTable, EmptyState, LoadingSkeleton, useAppToast } from '@/src/components/ui';
import { ArthsetuErrorBoundary } from '@/src/components/shared/ArthsetuErrorBoundary';
import { formatINR } from '@/src/lib/format';

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const SUPPORTED_TYPES = new Set(['image/jpeg', 'image/png', 'application/pdf']);
const LIVE_API_NOTICE = 'Live API feature — works in all modes';

interface OCRItemRow extends Record<string, unknown> {
  id: string;
  description: string;
  quantity: string;
  amount: number;
}

function toFileSizeLabel(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function toTimestampForFilename(): string {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(href);
}

function BillScannerContent() {
  const { session, isDemoMode } = useAuth();
  const { showToast } = useAppToast();

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [structuredResult, setStructuredResult] = useState<OCRStructuredResult | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);

  const rows = useMemo<OCRItemRow[]>(() => {
    if (!structuredResult) {
      return [];
    }

    return structuredResult.items.map((item, index) => ({
      id: `ocr_item_${index}`,
      description: item.description,
      quantity: item.quantity == null ? '-' : String(item.quantity),
      amount: item.amount,
    }));
  }, [structuredResult]);

  const ensureFileIsValid = (file: File): boolean => {
    if (!SUPPORTED_TYPES.has(file.type)) {
      showToast({ title: 'Unsupported format', description: 'Upload JPEG, PNG, or PDF only.', variant: 'error' });
      return false;
    }

    if (file.size > MAX_FILE_BYTES) {
      showToast({ title: 'File too large', description: 'Maximum supported file size is 10MB.', variant: 'error' });
      return false;
    }

    return true;
  };

  const selectFile = (file: File | null) => {
    if (!file) {
      return;
    }

    if (!ensureFileIsValid(file)) {
      return;
    }

    setSelectedFile(file);
    setStructuredResult(null);
  };

  const onDrop: React.DragEventHandler<HTMLLabelElement> = (event) => {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files?.[0] ?? null;
    selectFile(file);
  };

  const scanBill = async () => {
    if (!selectedFile) {
      showToast({ title: 'Select a file first', variant: 'warning' });
      return;
    }

    if (!adapter.scanBill) {
      showToast({ title: 'OCR endpoint unavailable', variant: 'error' });
      return;
    }

    if (isDemoMode) {
      showToast({ title: LIVE_API_NOTICE, variant: 'warning' });
    }

    setIsScanning(true);
    try {
      const payload = await adapter.scanBill(selectedFile);
      setStructuredResult(payload);
      showToast({ title: 'Bill scanned successfully', variant: 'success' });
    } catch (error) {
      showToast({
        title: 'Bill scan failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsScanning(false);
    }
  };

  const saveResult = async () => {
    if (!session?.merchantId || !structuredResult) {
      return;
    }

    if (!adapter.saveOcrResult) {
      showToast({ title: 'Save endpoint unavailable', variant: 'error' });
      return;
    }

    if (isDemoMode) {
      showToast({ title: LIVE_API_NOTICE, variant: 'warning' });
    }

    setIsSaving(true);
    try {
      await adapter.saveOcrResult(session.merchantId, structuredResult);
      showToast({ title: 'Saved to transactions', variant: 'success' });
    } catch (error) {
      showToast({
        title: 'Unable to save result',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4 pb-16">
      <section className="paytm-surface p-5">
        <h2 className="text-lg font-black text-[#002970]">Bill Scanner</h2>
        <p className="mt-1 text-sm text-slate-600">Upload bill image or PDF, extract details, and push it into your transaction pipeline.</p>

        <label
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          className={`mt-4 block cursor-pointer rounded-2xl border-2 border-dashed p-5 transition ${
            isDragging ? 'border-[#0a58d8] bg-[#eff5ff]' : 'border-[#cfd9ea] bg-[#f9fbff]'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept="image/*,application/pdf"
            capture="environment"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              selectFile(file);
            }}
          />

          <div className="flex flex-col items-center justify-center gap-2 text-center">
            <FileUp size={28} className="text-[#0a58d8]" />
            <p className="text-sm font-semibold text-slate-700">Drag and drop bill here, or tap to upload</p>
            <p className="text-xs text-slate-500">JPEG, PNG, PDF only. Max 10MB.</p>
          </div>
        </label>

        {selectedFile ? (
          <div className="mt-3 rounded-xl border border-[#d8e2f1] bg-white px-3 py-2 text-sm text-slate-700">
            <p className="font-semibold">Selected: {selectedFile.name}</p>
            <p className="text-xs text-slate-500">{toFileSizeLabel(selectedFile.size)}</p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]" onClick={() => void scanBill()} disabled={!selectedFile || isScanning}>
            {isScanning ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Extracting...
              </span>
            ) : (
              'Scan Bill'
            )}
          </Button>

          <Button variant="outline" className="rounded-full" onClick={() => inputRef.current?.click()}>
            Choose File
          </Button>
        </div>
      </section>

      {isScanning ? (
        <section className="paytm-surface p-5">
          <LoadingSkeleton variant="table-row" count={4} />
        </section>
      ) : null}

      {structuredResult ? (
        <section className="space-y-4">
          <article className="paytm-surface p-5">
            <h3 className="text-base font-black text-[#002970]">Extracted Summary</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-[#e1e8f5] bg-white p-3">
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Vendor Name</p>
                <p className="mt-1 text-sm font-semibold text-slate-800">{structuredResult.vendorName || '-'}</p>
              </div>
              <div className="rounded-xl border border-[#e1e8f5] bg-white p-3">
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Vendor GSTIN</p>
                <p className="mt-1 text-sm font-semibold text-slate-800">{structuredResult.vendorGstin || '-'}</p>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-[#e1e8f5] bg-white p-3">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Grand Total</p>
              <p className="mt-1 text-xl font-black text-[#002970]">{formatINR(structuredResult.grandTotal)}</p>
            </div>
          </article>

          <article className="paytm-surface p-5">
            <h3 className="text-base font-black text-[#002970]">Line Items</h3>
            <div className="mt-3">
              <DataTable
                columns={[
                  { key: 'description', header: 'Description' },
                  { key: 'quantity', header: 'Quantity' },
                  { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
                ]}
                data={rows}
                rowKey={(row) => row.id}
                emptyState={<EmptyState icon="invoice" title="No line items extracted" description="Try scanning a clearer image for better extraction." />}
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <Button className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]" onClick={() => void saveResult()} disabled={isSaving}>
                {isSaving ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin" />
                    Saving...
                  </span>
                ) : (
                  'Save to Transactions'
                )}
              </Button>

              <Button
                variant="outline"
                className="rounded-full"
                onClick={() => downloadJson(`ocr_result_${toTimestampForFilename()}.json`, structuredResult)}
              >
                Download JSON
              </Button>
            </div>
          </article>
        </section>
      ) : null}
    </div>
  );
}

export default function MerchantBillScannerPage() {
  return (
    <ArthsetuErrorBoundary>
      <BillScannerContent />
    </ArthsetuErrorBoundary>
  );
}
