'use client';

import { useMemo } from 'react';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import type { CreditOffer, Invoice } from '@/src/adapters/types';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { usePINGate } from '@/src/context/pin-context';
import { useToast } from '@/src/context/toast-context';
import { formatINR } from '@/src/lib/format';
import { DEMO_WHATSAPP_PHONE, WHATSAPP_TEMPLATES } from '@/src/lib/whatsapp-templates';

export default function MerchantFinanceOffersPage() {
  const { session } = useAuth();
  const { requirePIN } = usePINGate();
  const toast = useToast();

  const { data: invoices, mutate } = useSWR(
    session?.merchantId ? (['merchant-finance-offers', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getInvoices(merchantId);
    },
  );

  const activeOffers = useMemo(() => {
    if (!invoices) return [];
    return invoices
      .filter((row) => row.status === 'OVERDUE')
      .map((row) => ({
        invoice: row,
        offer: {
          offerId: `AUTO-${row.invoiceId}`,
          invoiceId: row.invoiceId,
          advanceAmount: Math.round(row.amount * 0.85),
          feeRate: 2,
          repaymentTrigger: `Auto-repay when ${row.buyerName} pays invoice`,
          status: 'pending_acceptance',
          generatedAt: new Date().toISOString(),
        } as CreditOffer,
      }));
  }, [invoices]);

  const historyRows: Invoice[] = useMemo(() => (invoices ?? []).filter((row) => row.status === 'FINANCED' || row.status === 'PAID'), [invoices]);

  if (!invoices || !session?.merchantId) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading finance offers...</div>;
  }

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <h2 className="text-lg font-black text-[#002970]">Active Offers</h2>
        {activeOffers.length ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {activeOffers.map(({ invoice, offer }) => (
              <article key={offer.offerId} className="rounded-2xl border border-[#dde6f5] bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2]">Invoice {offer.invoiceId}</p>
                <p className="mt-2 text-3xl font-black text-[#002970]">{formatINR(offer.advanceAmount)}</p>
                <p className="mt-1 text-sm text-slate-600">Fee rate: {offer.feeRate}%</p>
                <p className="text-sm text-slate-600">Repayment trigger: {offer.repaymentTrigger}</p>
                <p className="mt-2 text-xs text-slate-500">Expires in 24h</p>
                <div className="mt-3 flex gap-2">
                  <Button
                    className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
                    onClick={() => {
                      requirePIN({
                        message: `Confirm: Accept ${formatINR(offer.advanceAmount)} advance at ${offer.feeRate}% fee.`,
                        actionLabel: 'Accept Offer',
                        onSuccess: () => {
                          void (async () => {
                            const requested = await adapter.requestCreditOffer(session.merchantId as string, invoice.invoiceId);
                            await adapter.acceptCreditOffer(session.merchantId as string, requested.offerId);
                            toast.success(`Your advance of ${formatINR(requested.advanceAmount)} is being processed. Expected in 4 hours.`);
                            toast.whatsapp(
                              WHATSAPP_TEMPLATES.invoiceAdvanceAccepted({
                                amount: requested.advanceAmount,
                                invoiceId: invoice.invoiceId,
                                buyerName: invoice.buyerName,
                              }),
                              DEMO_WHATSAPP_PHONE,
                            );
                            await mutate();
                          })();
                        },
                      });
                    }}
                  >
                    Accept
                  </Button>
                  <Button variant="outline" className="rounded-full" onClick={() => toast.warning('Offer declined for now.')}>Decline</Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-600">No active offers right now.</p>
        )}
      </section>

      <section className="paytm-surface p-5">
        <h2 className="text-lg font-black text-[#002970]">Offer History</h2>
        <div className="mt-3">
          <DataTable
            columns={[
              { key: 'invoiceId', header: 'Invoice' },
              { key: 'amount', header: 'Invoice Amount', render: (value) => formatINR(Number(value)) },
              { key: 'advanceAmount', header: 'Advance', render: (value) => formatINR(Number(value)) },
              { key: 'feeRate', header: 'Fee Rate', render: (value) => `${value}%` },
              {
                key: 'status',
                header: 'Status',
                render: (value) => <StatusBadge status={String(value) === 'FINANCED' ? 'FINANCED' : 'PAID'} />,
              },
            ]}
            data={historyRows as unknown as Record<string, unknown>[]}
          />
        </div>
      </section>
    </div>
  );
}
