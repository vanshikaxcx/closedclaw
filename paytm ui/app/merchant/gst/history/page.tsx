'use client';

import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/src/components/ui';

const filings = [
  {
    quarter: 'Q1 2026',
    filingDate: '2026-04-03',
    referenceId: 'GST-REF-2026-0103',
    transactionCount: 847,
    netLiability: 185430,
    status: 'FILED',
  },
  {
    quarter: 'Q4 2025',
    filingDate: '2026-01-20',
    referenceId: 'GST-REF-2026-0099',
    transactionCount: 812,
    netLiability: 172980,
    status: 'FILED',
  },
  {
    quarter: 'Q3 2025',
    filingDate: '2025-10-18',
    referenceId: 'GST-REF-2025-0831',
    transactionCount: 779,
    netLiability: 163440,
    status: 'FILED',
  },
];

export default function MerchantGstHistoryPage() {
  return (
    <section className="space-y-3">
      {filings.map((entry) => (
        <article key={entry.referenceId} className="paytm-surface p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-black text-[#002970]">{entry.quarter}</h3>
            <StatusBadge status={entry.status as 'FILED'} />
          </div>
          <p className="mt-2 text-sm text-slate-600">Reference: {entry.referenceId}</p>
          <p className="text-sm text-slate-600">Filing date: {entry.filingDate}</p>
          <p className="text-sm text-slate-600">Transaction count: {entry.transactionCount}</p>
          <p className="text-sm text-slate-600">Net liability: Rs. {entry.netLiability.toLocaleString('en-IN')}</p>
          <Button variant="outline" className="mt-3 rounded-full">
            Export
          </Button>
        </article>
      ))}
    </section>
  );
}
