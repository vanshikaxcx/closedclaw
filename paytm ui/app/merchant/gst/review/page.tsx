'use client';

import { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import type {
  GSTDashboard,
  GSTDraft,
  GSTR1Draft,
  GSTR3BSummary,
  GSTReviewQueueItem,
  ResolveReviewItemPayload,
} from '@/src/adapters/types';
import { DataTable, EmptyState, LoadingSkeleton, Modal, StatusBadge, useAppToast } from '@/src/components/ui';
import { usePINGate } from '@/src/context/pin-context';
import { useToast } from '@/src/context/toast-context';
import { formatINR } from '@/src/lib/format';
import { DEMO_WHATSAPP_PHONE, WHATSAPP_TEMPLATES } from '@/src/lib/whatsapp-templates';

const GST_RATES = [0, 0.05, 0.12, 0.18, 0.28] as const;

interface ReviewTableRow extends Record<string, unknown> {
  queueId: string;
  txId: string;
  description: string;
  amount: number;
  currentHSN: string;
  currentGSTRate: number;
  status: 'needs_review' | 'ready';
}

interface SummaryRow extends Record<string, unknown> {
  metric: string;
  value: string;
}

interface GstFilingData {
  dashboard: GSTDashboard;
  transactionCount: number;
  reviewQueue: GSTReviewQueueItem[];
}

function draftToDashboard(draft: GSTDraft): GSTDashboard {
  return {
    merchantId: draft.merchantId,
    summary: {
      totalTransactions: draft.summary.totalCount,
      flaggedTransactions: draft.summary.flaggedCount,
      totalTaxable: draft.summary.totalTaxable,
      totalCGST: draft.summary.totalCGST,
      totalSGST: draft.summary.totalSGST,
      netLiability: draft.summary.netLiability,
      lastGeneratedAt: draft.generatedAt,
    },
    gstr1Generated: false,
    gstr3bGenerated: false,
  };
}

function draftToQueue(draft: GSTDraft): GSTReviewQueueItem[] {
  return draft.transactions
    .filter((row) => row.reviewFlag)
    .map((row) => ({
      queueId: `${draft.merchantId}:${row.txId}`,
      merchantId: draft.merchantId,
      txId: row.txId,
      description: row.description,
      amount: row.amount,
      currentHSN: row.hsnCode,
      currentGSTRate: row.gstRate,
      gstCategory: row.category,
      reviewFlag: true,
      status: 'needs_review',
    }));
}

function toDateStamp() {
  return new Date().toISOString().slice(0, 10);
}

function downloadJsonBlob(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(href);
}

export default function MerchantGstReviewPage() {
  const { session } = useAuth();
  const { requirePIN } = usePINGate();
  const toast = useToast();
  const { showToast } = useAppToast();

  const [page, setPage] = useState(1);
  const [reviewEdits, setReviewEdits] = useState<Record<string, { hsnCode: string; gstRate: number }>>({});
  const [savingQueueId, setSavingQueueId] = useState<string | null>(null);
  const [isGeneratingGSTR1, setIsGeneratingGSTR1] = useState(false);
  const [isGeneratingGSTR3B, setIsGeneratingGSTR3B] = useState(false);
  const [generatedThisSession, setGeneratedThisSession] = useState({ gstr1: false, gstr3b: false });
  const [gstr1Draft, setGstr1Draft] = useState<GSTR1Draft | null>(null);
  const [gstr3bSummary, setGstr3bSummary] = useState<GSTR3BSummary | null>(null);
  const [resultOpen, setResultOpen] = useState(false);
  const [resultRef, setResultRef] = useState('');

  const { data, isLoading, mutate } = useSWR<GstFilingData>(
    session?.merchantId ? (['gst-review-live', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      if (adapter.getDashboard && adapter.getTransactions && adapter.getReviewQueue) {
        const [dashboard, transactions, reviewQueue] = await Promise.all([
          adapter.getDashboard(merchantId),
          adapter.getTransactions(merchantId),
          adapter.getReviewQueue(merchantId),
        ]);

        return {
          dashboard,
          transactionCount: transactions.length,
          reviewQueue,
        };
      }

      const draft = await adapter.getGSTDraft(merchantId);
      return {
        dashboard: draftToDashboard(draft),
        transactionCount: draft.transactions.length,
        reviewQueue: draftToQueue(draft),
      };
    },
    {
      refreshInterval: 30000,
      revalidateOnFocus: false,
    },
  );

  const pageSize = 20;

  const reviewRows = useMemo<ReviewTableRow[]>(() => {
    if (!data) {
      return [];
    }

    return data.reviewQueue.map((row) => ({
      queueId: row.queueId,
      txId: row.txId,
      description: row.description,
      amount: row.amount,
      currentHSN: row.currentHSN,
      currentGSTRate: row.currentGSTRate,
      status: row.status,
    }));
  }, [data]);

  const pagedRows = useMemo(() => {
    if (!reviewRows.length) {
      return [];
    }

    const start = (page - 1) * pageSize;
    return reviewRows.slice(start, start + pageSize);
  }, [page, reviewRows]);

  useEffect(() => {
    if (!data) {
      return;
    }

    setReviewEdits((current) => {
      const next = { ...current };
      for (const row of data.reviewQueue) {
        if (!next[row.queueId]) {
          next[row.queueId] = {
            hsnCode: row.currentHSN,
            gstRate: row.currentGSTRate,
          };
        }
      }
      return next;
    });
  }, [data]);

  if (!session?.merchantId) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Merchant session missing.</div>;
  }

  if (isLoading && !data) {
    return (
      <div className="space-y-4">
        <LoadingSkeleton variant="metric" count={4} />
        <LoadingSkeleton variant="table-row" count={8} />
      </div>
    );
  }

  if (!data) {
    return (
      <EmptyState
        icon="gst"
        title="GST data unavailable"
        description="Unable to load GST dashboard right now. Please refresh and try again."
      />
    );
  }

  const merchantId = session.merchantId;
  const canFileNow = generatedThisSession.gstr1 && generatedThisSession.gstr3b;

  const updateEdit = (queueId: string, patch: Partial<{ hsnCode: string; gstRate: number }>) => {
    setReviewEdits((current) => ({
      ...current,
      [queueId]: {
        hsnCode: patch.hsnCode ?? current[queueId]?.hsnCode ?? '',
        gstRate: patch.gstRate ?? current[queueId]?.gstRate ?? 0,
      },
    }));
  };

  const saveReviewItem = async (row: ReviewTableRow) => {
    if (!row.queueId) {
      return;
    }

    const edit = reviewEdits[row.queueId] ?? {
      hsnCode: row.currentHSN,
      gstRate: row.currentGSTRate,
    };

    const payload: ResolveReviewItemPayload = {
      hsnCode: edit.hsnCode,
      gstRate: Number(edit.gstRate),
      status: 'resolved',
    };

    setSavingQueueId(row.queueId);
    try {
      if (adapter.resolveReviewItem) {
        await adapter.resolveReviewItem(row.queueId, payload);
      } else {
        await adapter.updateGSTTransaction(merchantId, {
          txId: row.txId,
          hsnCode: payload.hsnCode,
          gstRate: payload.gstRate,
        });
      }

      showToast({ title: 'Review item updated', variant: 'success' });
      await mutate();
    } catch (error) {
      showToast({
        title: 'Failed to update review item',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setSavingQueueId(null);
    }
  };

  const generateGSTR1 = async () => {
    setIsGeneratingGSTR1(true);
    try {
      if (!adapter.generateGSTR1 || !adapter.getGSTR1Draft) {
        throw new Error('GSTR-1 live endpoints are unavailable in current adapter mode');
      }

      await adapter.generateGSTR1(merchantId);
      const draft = await adapter.getGSTR1Draft(merchantId);
      setGstr1Draft(draft);
      setGeneratedThisSession((current) => ({ ...current, gstr1: true }));
      showToast({ title: 'GSTR-1 draft generated', variant: 'success' });
      await mutate();
    } catch (error) {
      showToast({
        title: 'GSTR-1 generation failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsGeneratingGSTR1(false);
    }
  };

  const generateGSTR3B = async () => {
    setIsGeneratingGSTR3B(true);
    try {
      if (!adapter.generateGSTR3B || !adapter.getGSTR3BSummary) {
        throw new Error('GSTR-3B live endpoints are unavailable in current adapter mode');
      }

      await adapter.generateGSTR3B(merchantId);
      const summary = await adapter.getGSTR3BSummary(merchantId);
      setGstr3bSummary(summary);
      setGeneratedThisSession((current) => ({ ...current, gstr3b: true }));
      showToast({ title: 'GSTR-3B summary generated', variant: 'success' });
      await mutate();
    } catch (error) {
      showToast({
        title: 'GSTR-3B generation failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsGeneratingGSTR3B(false);
    }
  };

  const fileWithPin = () => {
    if (!canFileNow) {
      return;
    }

    requirePIN({
      message: 'Enter PIN to file your GST return.',
      actionLabel: 'File GST',
      onSuccess: () => {
        void (async () => {
          const result = await adapter.fileGST(merchantId);
          setResultRef(result.refId);
          setResultOpen(true);
          const message = WHATSAPP_TEMPLATES.gstFiled({
            refId: result.refId,
            date: new Date(result.filedAt).toLocaleDateString('en-IN'),
            amount: data.dashboard.summary.netLiability,
          });
          toast.whatsapp(message, DEMO_WHATSAPP_PHONE);
          await mutate();
        })();
      },
    });
  };

  return (
    <div className="space-y-4">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Transactions</p>
          <p className="mt-2 text-2xl font-black text-[#002970]">{data.dashboard.summary.totalTransactions}</p>
        </article>
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Needs Review</p>
          <p className="mt-2 text-2xl font-black text-[#002970]">{data.dashboard.summary.flaggedTransactions}</p>
        </article>
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Total Taxable</p>
          <p className="mt-2 text-2xl font-black text-[#002970]">{formatINR(data.dashboard.summary.totalTaxable)}</p>
        </article>
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Net Liability</p>
          <p className="mt-2 text-2xl font-black text-[#002970]">{formatINR(data.dashboard.summary.netLiability)}</p>
        </article>
      </section>

      <section className="paytm-surface p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-black text-[#002970]">GST Review Queue</h2>
            <p className="text-sm text-slate-600">Review flagged transactions and update HSN/GST before generating drafts.</p>
          </div>
          <p className="text-xs font-semibold text-slate-500">Total transactions loaded: {data.transactionCount}</p>
        </div>

        <DataTable
          columns={[
            { key: 'txId', header: 'Transaction ID' },
            { key: 'description', header: 'Description' },
            { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
            {
              key: 'currentHSN',
              header: 'Current HSN',
              render: (_value, row) => (
                <input
                  value={reviewEdits[row.queueId]?.hsnCode ?? row.currentHSN}
                  onChange={(event) => updateEdit(row.queueId, { hsnCode: event.target.value })}
                  className="h-9 w-[130px] rounded-lg border border-[#cfd9ea] px-2 text-sm"
                />
              ),
            },
            {
              key: 'currentGSTRate',
              header: 'Current GST Rate',
              render: (_value, row) => (
                <select
                  value={reviewEdits[row.queueId]?.gstRate ?? row.currentGSTRate}
                  onChange={(event) => updateEdit(row.queueId, { gstRate: Number(event.target.value) })}
                  className="h-9 w-[120px] rounded-lg border border-[#cfd9ea] px-2 text-sm"
                >
                  {GST_RATES.map((rate) => (
                    <option key={rate} value={rate}>
                      {Math.round(rate * 100)}%
                    </option>
                  ))}
                </select>
              ),
            },
            {
              key: 'status',
              header: 'Status',
              render: (_value, row) => (
                <div className="flex flex-col items-start gap-2">
                  <StatusBadge status={row.status === 'needs_review' ? 'NEEDS_REVIEW' : 'ACTIVE'} />
                  <Button
                    size="sm"
                    className="h-8 rounded-full bg-[#002970] px-3 text-xs hover:bg-[#0a3f9d]"
                    disabled={savingQueueId === row.queueId}
                    onClick={() => void saveReviewItem(row)}
                  >
                    {savingQueueId === row.queueId ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 size={14} className="animate-spin" />
                        Saving...
                      </span>
                    ) : (
                      'Save'
                    )}
                  </Button>
                </div>
              ),
            },
          ]}
          data={pagedRows}
          rowKey={(row) => row.queueId}
          pagination={{
            page,
            pageSize,
            total: reviewRows.length,
            onPageChange: setPage,
          }}
          emptyState={
            <EmptyState
              icon="gst"
              title="No transactions need review"
              description="All transactions are review-complete for this cycle."
            />
          }
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="paytm-surface p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-black text-[#002970]">GSTR-1 Draft</h3>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => void generateGSTR1()}
                disabled={isGeneratingGSTR1}
                className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
              >
                {isGeneratingGSTR1 ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 size={15} className="animate-spin" />
                    Generating...
                  </span>
                ) : (
                  'Generate GSTR-1 Draft'
                )}
              </Button>
              {gstr1Draft ? (
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() =>
                    downloadJsonBlob(
                      `GSTR1_draft_${merchantId}_${toDateStamp()}.json`,
                      gstr1Draft,
                    )
                  }
                >
                  Download JSON
                </Button>
              ) : null}
            </div>
          </div>

          {gstr1Draft ? (
            <div className="mt-4 space-y-4">
              <article>
                <p className="mb-2 text-sm font-semibold text-slate-800">Table 4 (B2B)</p>
                <DataTable
                  columns={[
                    { key: 'txId', header: 'TX ID' },
                    { key: 'description', header: 'Description' },
                    { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
                    { key: 'gstRate', header: 'GST Rate', render: (value) => `${Math.round(Number(value) * 100)}%` },
                  ]}
                  data={gstr1Draft.table4 as unknown as Record<string, unknown>[]}
                  rowKey={(row, index) => `${row.txId}-${index}`}
                />
              </article>

              <article>
                <p className="mb-2 text-sm font-semibold text-slate-800">Table 5 (B2C)</p>
                <DataTable
                  columns={[
                    { key: 'txId', header: 'TX ID' },
                    { key: 'description', header: 'Description' },
                    { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
                    { key: 'gstRate', header: 'GST Rate', render: (value) => `${Math.round(Number(value) * 100)}%` },
                  ]}
                  data={gstr1Draft.table5 as unknown as Record<string, unknown>[]}
                  rowKey={(row, index) => `${row.txId}-${index}`}
                />
              </article>

              <article>
                <p className="mb-2 text-sm font-semibold text-slate-800">Table 7 (Exempt)</p>
                <DataTable
                  columns={[
                    { key: 'txId', header: 'TX ID' },
                    { key: 'description', header: 'Description' },
                    { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
                    { key: 'gstRate', header: 'GST Rate', render: (value) => `${Math.round(Number(value) * 100)}%` },
                  ]}
                  data={gstr1Draft.table7 as unknown as Record<string, unknown>[]}
                  rowKey={(row, index) => `${row.txId}-${index}`}
                />
              </article>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">Generate draft to preview Table 4, Table 5, and Table 7.</p>
          )}
        </article>

        <article className="paytm-surface p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-black text-[#002970]">GSTR-3B Summary</h3>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => void generateGSTR3B()}
                disabled={isGeneratingGSTR3B}
                className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
              >
                {isGeneratingGSTR3B ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 size={15} className="animate-spin" />
                    Generating...
                  </span>
                ) : (
                  'Generate GSTR-3B Summary'
                )}
              </Button>
              {gstr3bSummary ? (
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() =>
                    downloadJsonBlob(
                      `GSTR3B_summary_${merchantId}_${toDateStamp()}.json`,
                      gstr3bSummary,
                    )
                  }
                >
                  Download JSON
                </Button>
              ) : null}
            </div>
          </div>

          {gstr3bSummary ? (
            <div className="mt-4">
              <DataTable
                columns={[
                  { key: 'metric', header: 'Metric' },
                  { key: 'value', header: 'Value' },
                ]}
                data={[
                  { metric: 'Taxable Value', value: formatINR(gstr3bSummary.taxableValue) },
                  { metric: 'Exempt Value', value: formatINR(gstr3bSummary.exemptValue) },
                  { metric: 'Total CGST', value: formatINR(gstr3bSummary.totalCGST) },
                  { metric: 'Total SGST', value: formatINR(gstr3bSummary.totalSGST) },
                  { metric: 'ITC Available', value: formatINR(gstr3bSummary.itcAvailable) },
                  { metric: 'Net Payable', value: formatINR(gstr3bSummary.netPayable) },
                ] as SummaryRow[]}
                rowKey={(row, index) => `${row.metric}-${index}`}
              />
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">Generate summary to review liabilities and ITC.</p>
          )}
        </article>
      </section>

      <section className="sticky bottom-16 z-30 rounded-2xl border border-[#d7e0f0] bg-white/95 p-3 shadow-sm backdrop-blur lg:bottom-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs font-semibold text-slate-500">
            File Now is enabled only after generating both GSTR-1 and GSTR-3B in this session.
          </p>
          <Button
            onClick={fileWithPin}
            disabled={!canFileNow}
            className="rounded-full bg-[#002970] hover:bg-[#0a3f9d] disabled:opacity-40"
          >
            File Now
          </Button>
        </div>
      </section>

      <Modal open={resultOpen} onClose={() => setResultOpen(false)} title="GST Filing Complete">
        <p className="text-sm text-slate-700">Reference ID: {resultRef}</p>
        <p className="mt-1 text-sm text-slate-700">WhatsApp confirmation sent to +91XXXXXX.</p>
        <Button className="mt-4 rounded-full bg-[#002970] hover:bg-[#0a3f9d]" onClick={() => setResultOpen(false)}>
          Done
        </Button>
      </Modal>
    </div>
  );
}
