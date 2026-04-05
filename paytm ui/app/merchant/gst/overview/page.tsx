'use client';

import Link from 'next/link';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import { MetricCard, StatusBadge } from '@/src/components/ui';
import { formatINR } from '@/src/lib/format';

const staticTimeline = [
  { quarter: 'Q4 2025', date: '2026-01-20', ref: 'GST-REF-2026-0099', status: 'FILED' },
  { quarter: 'Q3 2025', date: '2025-10-18', ref: 'GST-REF-2025-0831', status: 'FILED' },
  { quarter: 'Q2 2025', date: '2025-07-19', ref: 'GST-REF-2025-0612', status: 'FILED' },
];

export default function MerchantGstOverviewPage() {
  const { session } = useAuth();

  const { data } = useSWR(
    session?.merchantId ? (['gst-overview', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getGSTDraft(merchantId);
    },
  );

  if (!data) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading GST summary...</div>;
  }

  return (
    <div className="space-y-4">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Auto-categorised" value={data.summary.totalCount - data.summary.flaggedCount} />
        <MetricCard label="Flagged" value={data.summary.flaggedCount} sublabel={data.summary.flaggedCount > 0 ? 'Needs review' : 'All clear'} />
        <MetricCard label="Total Taxable" value={formatINR(data.summary.totalTaxable)} />
        <MetricCard label="Net Tax Liability" value={formatINR(data.summary.netLiability)} />
      </section>

      <section className="paytm-surface p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-black text-[#002970]">Current Filing Status</h2>
          <StatusBadge status={data.summary.flaggedCount > 0 ? 'FLAGGED' : 'FILED'} />
        </div>

        <p className="mt-2 text-sm text-slate-600">
          Quarter {data.quarter} {data.year} currently has {data.summary.flaggedCount} flagged transactions.
        </p>

        <Link href="/merchant/gst/review" className="mt-4 inline-flex rounded-full bg-[#002970] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a3f9d]">
          Review Current Quarter
        </Link>
      </section>

      <section className="paytm-surface p-5">
        <h3 className="text-lg font-black text-[#002970]">Filing Timeline</h3>
        <div className="mt-3 space-y-3">
          {staticTimeline.map((entry) => (
            <div key={entry.ref} className="rounded-xl border border-[#e4eaf6] bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-800">{entry.quarter}</p>
                <StatusBadge status={entry.status as 'FILED'} />
              </div>
              <p className="mt-1 text-xs text-slate-500">Reference: {entry.ref}</p>
              <p className="text-xs text-slate-500">Filed on: {entry.date}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
