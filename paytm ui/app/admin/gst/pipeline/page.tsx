'use client';

import Link from 'next/link';
import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { formatDateTime, formatINR } from '@/src/lib/format';

interface GSTPipelineRow {
  merchantId: string;
  merchantName: string;
  generatedAt: string;
  totalCount: number;
  flaggedCount: number;
  liability: number;
  stage: 'review' | 'ready';
}

export default function AdminGSTPipelinePage() {
  const { data } = useSWR('admin-gst-pipeline', async () => {
    const merchants = await adapter.getMerchants();
    const rows = await Promise.all(
      merchants.map(async (merchant) => {
        const draft = await adapter.getGSTDraft(merchant.merchantId);
        const row: GSTPipelineRow = {
          merchantId: merchant.merchantId,
          merchantName: merchant.businessName,
          generatedAt: draft.generatedAt,
          totalCount: draft.summary.totalCount,
          flaggedCount: draft.summary.flaggedCount,
          liability: draft.summary.netLiability,
          stage: draft.summary.flaggedCount > 0 ? 'review' : 'ready',
        };
        return row;
      }),
    );
    return rows;
  });

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">GST Pipeline</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Merchant Filing Queue</h1>
        <p className="mt-1 text-sm text-slate-600">Operational view of draft generation, flagged rows, and filing readiness.</p>
      </section>

      <section className="paytm-surface p-5">
        <DataTable
          columns={[
            {
              key: 'merchantName',
              header: 'Merchant',
              render: (value, row) => (
                <Link href={`/admin/merchants/${String(row.merchantId)}`} className="font-semibold text-[#002970] hover:underline">
                  {String(value)}
                </Link>
              ),
            },
            { key: 'totalCount', header: 'Transactions' },
            {
              key: 'flaggedCount',
              header: 'Flagged',
              render: (value) => (
                <span className={Number(value) > 0 ? 'font-semibold text-[#b45309]' : 'font-semibold text-emerald-700'}>{String(value)}</span>
              ),
            },
            { key: 'liability', header: 'Net Liability', render: (value) => formatINR(Number(value)) },
            { key: 'generatedAt', header: 'Generated', render: (value) => formatDateTime(String(value)) },
            {
              key: 'stage',
              header: 'Stage',
              render: (value) => <StatusBadge status={String(value) === 'ready' ? 'FILED' : 'FLAGGED'} />,
            },
          ]}
          data={data as unknown as Record<string, unknown>[]}
        />
      </section>
    </div>
  );
}
