'use client';

import { useMemo } from 'react';
import { useParams } from 'next/navigation';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import { StatusBadge } from '@/src/components/ui';
import { formatDate, formatINR } from '@/src/lib/format';

export default function MerchantInvoiceDetailPage() {
  const params = useParams<{ invoiceId: string }>();
  const { session } = useAuth();

  const { data } = useSWR(
    session?.merchantId ? (['merchant-invoice-detail', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getInvoices(merchantId);
    },
  );

  const invoice = useMemo(() => data?.find((row) => row.invoiceId === params.invoiceId), [data, params.invoiceId]);

  if (!invoice) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Invoice not found.</div>;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <section className="paytm-surface p-5">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-black text-[#002970]">Invoice {invoice.invoiceId}</h1>
          <StatusBadge status={invoice.status as any} />
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <p className="text-sm text-slate-700">Buyer: {invoice.buyerName}</p>
          <p className="text-sm text-slate-700">Buyer GSTIN: {invoice.buyerGstin}</p>
          <p className="text-sm text-slate-700">Amount: {formatINR(invoice.amount)}</p>
          <p className="text-sm text-slate-700">Due Date: {formatDate(invoice.dueDate)}</p>
          <p className="text-sm text-slate-700">Overdue Days: {invoice.overdueDays}</p>
          <p className="text-sm text-slate-700">Created: {formatDate(invoice.createdAt)}</p>
        </div>
      </section>

      <aside className="space-y-4">
        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Timeline</h2>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p>Created</p>
            <p>Due: {formatDate(invoice.dueDate)}</p>
            {invoice.overdueDays > 0 ? <p>Overdue since {invoice.overdueDays} days</p> : null}
            {invoice.status === 'FINANCED' ? <p>Financed with advance {formatINR(invoice.advanceAmount)}</p> : null}
          </div>
        </article>

        {invoice.status === 'FINANCED' ? (
          <article className="paytm-surface p-5">
            <h3 className="text-lg font-black text-[#002970]">Offer Terms</h3>
            <p className="mt-2 text-sm text-slate-700">Disbursed amount: {formatINR(invoice.advanceAmount)}</p>
            <p className="text-sm text-slate-700">Fee: {invoice.feeRate}%</p>
            <p className="text-sm text-slate-700">Estimated repayment: {formatINR(invoice.advanceAmount + (invoice.advanceAmount * invoice.feeRate) / 100)}</p>
          </article>
        ) : (
          <article className="paytm-surface p-5">
            <h3 className="text-lg font-black text-[#002970]">Offer Actions</h3>
            <p className="mt-2 text-sm text-slate-600">Use Finance Offers page to request and accept advances.</p>
            <Button className="mt-3 rounded-full bg-[#002970] hover:bg-[#0a3f9d]">Open Offers</Button>
          </article>
        )}
      </aside>
    </div>
  );
}
