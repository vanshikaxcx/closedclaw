'use client';

import Link from 'next/link';
import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { formatINR } from '@/src/lib/format';

interface MerchantDashboardRow {
  merchantId: string;
  merchantName: string;
  trustScore: number;
  gstFlaggedCount: number;
  overdueInvoices: number;
  walletBalance: number;
}

export default function AdminDashboardPage() {
  const { data } = useSWR('admin-dashboard', async () => {
    const merchants = await adapter.getMerchants();

    const rows = await Promise.all(
      merchants.map(async (merchant) => {
        const [trust, gst, invoices] = await Promise.all([
          adapter.getTrustScore(merchant.merchantId),
          adapter.getGSTDraft(merchant.merchantId),
          adapter.getInvoices(merchant.merchantId),
        ]);

        const row: MerchantDashboardRow = {
          merchantId: merchant.merchantId,
          merchantName: merchant.businessName,
          trustScore: trust.score,
          gstFlaggedCount: gst.summary.flaggedCount,
          overdueInvoices: invoices.filter((invoice) => invoice.status === 'OVERDUE').length,
          walletBalance: merchant.walletBalance,
        };

        return row;
      }),
    );

    return rows;
  });

  const merchants = data ?? [];
  const avgTrust = merchants.length
    ? Math.round(merchants.reduce((sum, merchant) => sum + merchant.trustScore, 0) / merchants.length)
    : 0;
  const totalOverdue = merchants.reduce((sum, merchant) => sum + merchant.overdueInvoices, 0);
  const totalFlagged = merchants.reduce((sum, merchant) => sum + merchant.gstFlaggedCount, 0);

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Admin Control Tower</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Flywheel Operations Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600">Observe compliance, trust, and finance outcomes across merchant portfolio.</p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Merchants</p>
          <p className="mt-1 text-2xl font-black text-[#002970]">{merchants.length}</p>
        </article>
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Average TrustScore</p>
          <p className="mt-1 text-2xl font-black text-[#002970]">{avgTrust}</p>
        </article>
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Overdue Invoices</p>
          <p className="mt-1 text-2xl font-black text-[#002970]">{totalOverdue}</p>
        </article>
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">GST Flagged</p>
          <p className="mt-1 text-2xl font-black text-[#002970]">{totalFlagged}</p>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Portfolio View</h2>
          <div className="mt-3">
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
                { key: 'gstFlaggedCount', header: 'GST Flagged' },
                { key: 'overdueInvoices', header: 'Overdue' },
                {
                  key: 'walletBalance',
                  header: 'Wallet',
                  render: (value) => <span className="font-semibold">{formatINR(Number(value))}</span>,
                },
              ]}
              data={merchants as unknown as Record<string, unknown>[]}
            />
          </div>
        </article>

        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Flywheel Stage Health</h2>
          <div className="mt-3 space-y-2">
            <div className="rounded-xl border border-[#d6deef] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">1. Data Capture</p>
              <p className="mt-1 text-sm font-semibold text-[#002970]">PayBot and wallet transactions</p>
              <div className="mt-2"><StatusBadge status="ACTIVE" /></div>
            </div>
            <div className="rounded-xl border border-[#d6deef] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">2. Compliance</p>
              <p className="mt-1 text-sm font-semibold text-[#002970]">GST classification and filing quality</p>
              <div className="mt-2"><StatusBadge status={totalFlagged > 0 ? 'FLAGGED' : 'ACTIVE'} /></div>
            </div>
            <div className="rounded-xl border border-[#d6deef] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">3. Risk Scoring</p>
              <p className="mt-1 text-sm font-semibold text-[#002970]">Trust score updates from behavior</p>
              <div className="mt-2"><StatusBadge status="ACTIVE" /></div>
            </div>
            <div className="rounded-xl border border-[#d6deef] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">4. Financing</p>
              <p className="mt-1 text-sm font-semibold text-[#002970]">Invoice advances and repayment tracking</p>
              <div className="mt-2"><StatusBadge status={totalOverdue > 0 ? 'FLAGGED' : 'ACTIVE'} /></div>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
