'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import type { CreditOffer, Invoice, InvoiceStatus } from '@/src/adapters/types';
import { CreditOfferModal } from '@/src/components/shared/CreditOfferModal';
import { DataTable, MetricCard, StatusBadge } from '@/src/components/ui';
import { useToast } from '@/src/context/toast-context';
import { formatINR } from '@/src/lib/format';
import { DEMO_WHATSAPP_PHONE, WHATSAPP_TEMPLATES } from '@/src/lib/whatsapp-templates';

const filters: Array<'ALL' | InvoiceStatus> = ['ALL', 'PENDING', 'PAID', 'OVERDUE', 'FINANCED'];

export default function MerchantInvoicesPage() {
  const { session } = useAuth();
  const toast = useToast();

  const [activeFilter, setActiveFilter] = useState<'ALL' | InvoiceStatus>('ALL');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedOffer, setSelectedOffer] = useState<CreditOffer | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data, mutate } = useSWR(
    session?.merchantId ? (['merchant-invoices', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getInvoices(merchantId);
    },
  );

  if (!data || !session?.merchantId) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading invoices...</div>;
  }

  const filtered = data.filter((row) => (activeFilter === 'ALL' ? true : row.status === activeFilter));
  const tableRows = filtered as Array<Invoice & Record<string, unknown>>;
  const totalOutstanding = data.filter((row) => row.status === 'OVERDUE' || row.status === 'PENDING').reduce((sum, row) => sum + row.amount, 0);
  const overdueAmount = data.filter((row) => row.status === 'OVERDUE').reduce((sum, row) => sum + row.amount, 0);
  const financedAmount = data.filter((row) => row.status === 'FINANCED').reduce((sum, row) => sum + row.advanceAmount, 0);

  const openOffer = async (invoice: Invoice) => {
    const offer = await adapter.requestCreditOffer(session.merchantId as string, invoice.invoiceId);
    setSelectedInvoice(invoice);
    setSelectedOffer(offer);
    setModalOpen(true);
  };

  return (
    <div className="space-y-4">
      <section className="grid gap-3 sm:grid-cols-3">
        <MetricCard label="Total Outstanding" value={formatINR(totalOutstanding)} />
        <MetricCard label="Overdue Amount" value={formatINR(overdueAmount)} />
        <MetricCard label="Financed Amount" value={formatINR(financedAmount)} />
      </section>

      <section className="paytm-surface p-4">
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setActiveFilter(filter)}
              className={`rounded-full px-4 py-2 text-xs font-semibold ${activeFilter === filter ? 'bg-[#002970] text-white' : 'border border-[#d1daea] text-slate-600'}`}
            >
              {filter}
            </button>
          ))}
        </div>

        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'invoiceId', header: 'Invoice', render: (value, row) => <Link href={`/merchant/invoices/${row.invoiceId}`} className="font-semibold text-[#0a58d8]">{String(value)}</Link> },
              { key: 'buyerName', header: 'Buyer Name' },
              { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
              { key: 'dueDate', header: 'Due Date' },
              {
                key: 'status',
                header: 'Status',
                render: (value) => <StatusBadge status={String(value) as any} />,
              },
              {
                key: 'overdueDays',
                header: 'Overdue Days',
                render: (value) => <span className={Number(value) > 0 ? 'text-red-600 font-semibold' : ''}>{String(value)}</span>,
              },
              {
                key: 'action',
                header: 'Action',
                render: (_value, row) => {
                  if (row.status === 'OVERDUE') {
                    return (
                      <Button variant="outline" onClick={() => void openOffer(row)} className="rounded-full border-[#002970] text-[#002970]">
                        Get Advance
                      </Button>
                    );
                  }
                  if (row.status === 'PENDING') {
                    return (
                      <Button
                        variant="outline"
                        onClick={() => toast.success(`Reminder sent for ${row.invoiceId}`)}
                        className="rounded-full"
                      >
                        Send Reminder
                      </Button>
                    );
                  }
                  if (row.status === 'FINANCED') {
                    return (
                      <Link href={`/merchant/invoices/${row.invoiceId}`} className="text-sm font-semibold text-[#0a58d8]">
                        View Terms
                      </Link>
                    );
                  }
                  return null;
                },
              },
            ]}
            data={tableRows}
          />
        </div>
      </section>

      <CreditOfferModal
        open={modalOpen}
        offer={selectedOffer}
        invoice={selectedInvoice}
        onClose={() => setModalOpen(false)}
        onDecline={async () => {
          setModalOpen(false);
          toast.warning('Offer declined.');
        }}
        onAccept={async () => {
          if (!selectedOffer) return;
          await adapter.acceptCreditOffer(session.merchantId as string, selectedOffer.offerId);
          toast.whatsapp(
            WHATSAPP_TEMPLATES.invoiceAdvanceAccepted({
              amount: selectedOffer.advanceAmount,
              invoiceId: selectedOffer.invoiceId,
              buyerName: selectedInvoice?.buyerName ?? 'Buyer',
            }),
            DEMO_WHATSAPP_PHONE,
          );
          setModalOpen(false);
          await mutate();
        }}
      />
    </div>
  );
}
