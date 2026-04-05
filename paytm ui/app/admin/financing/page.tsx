'use client';

import Link from 'next/link';
import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { formatINR } from '@/src/lib/format';

interface FinancingRow {
  merchantId: string;
  merchantName: string;
  trustScore: number;
  financedInvoices: number;
  outstandingExposure: number;
  overdueInvoices: number;
  decision: 'active' | 'watchlist';
}

export default function AdminFinancingPage() {
  const { data } = useSWR('admin-financing', async () => {
    const merchants = await adapter.getMerchants();
    const rows = await Promise.all(
      merchants.map(async (merchant) => {
        const [trust, invoices] = await Promise.all([
          adapter.getTrustScore(merchant.merchantId),
          adapter.getInvoices(merchant.merchantId),
        ]);

        const financedInvoices = invoices.filter((invoice) => invoice.status === 'FINANCED').length;
        const overdueInvoices = invoices.filter((invoice) => invoice.status === 'OVERDUE').length;
        const outstandingExposure = invoices
          .filter((invoice) => invoice.status === 'FINANCED' && !invoice.repaid)
          .reduce((sum, invoice) => sum + invoice.advanceAmount, 0);

        const row: FinancingRow = {
          merchantId: merchant.merchantId,
          merchantName: merchant.businessName,
          trustScore: trust.score,
          financedInvoices,
          overdueInvoices,
          outstandingExposure,
          decision: trust.score >= 70 && overdueInvoices < 3 ? 'active' : 'watchlist',
        };
        return row;
      }),
    );

    return rows;
  });

  const totalExposure = (data ?? []).reduce((sum, row) => sum + row.outstandingExposure, 0);

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Financing Monitor</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Invoice Credit Oversight</h1>
        <div className="mt-3 inline-flex rounded-xl border border-[#d1daea] bg-white px-4 py-2 text-sm text-slate-700">
          Total outstanding exposure: <span className="ml-1 font-bold text-[#002970]">{formatINR(totalExposure)}</span>
        </div>
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
            { key: 'trustScore', header: 'TrustScore' },
            { key: 'financedInvoices', header: 'Financed Invoices' },
            { key: 'overdueInvoices', header: 'Overdue' },
            { key: 'outstandingExposure', header: 'Exposure', render: (value) => formatINR(Number(value)) },
            {
              key: 'decision',
              header: 'Decision',
              render: (value) => <StatusBadge status={String(value) === 'active' ? 'ACTIVE' : 'FLAGGED'} />,
            },
          ]}
          data={data as unknown as Record<string, unknown>[]}
        />
      </section>
    </div>
  );
}
