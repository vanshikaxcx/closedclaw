'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import { DataTable, EmptyState, MetricCard } from '@/src/components/ui';
import { CashflowChart } from '@/src/components/shared/CashflowChart';
import { useToast } from '@/src/context/toast-context';
import { formatINR, formatINRCompactLakh } from '@/src/lib/format';
import { DEMO_WHATSAPP_PHONE, WHATSAPP_TEMPLATES } from '@/src/lib/whatsapp-templates';

export default function MerchantCashflowPage() {
  const { session } = useAuth();
  const toast = useToast();
  const [windowDays, setWindowDays] = useState<30 | 60 | 90>(30);

  const { data, isLoading } = useSWR(
    session?.merchantId ? (['cashflow-page', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getCashflow(merchantId);
    },
    { refreshInterval: 30000, revalidateOnFocus: false },
  );

  if (isLoading) {
    return <div className="paytm-surface p-6 text-sm text-slate-600">Loading cashflow module...</div>;
  }

  if (!data || !session?.merchantId) {
    return <EmptyState icon="generic" title="Cashflow unavailable" description="Unable to load projection data." />;
  }

  const p30Range = `${formatINR(Math.round(data.projection.p30.amount * 0.9))} - ${formatINR(Math.round(data.projection.p30.amount * 1.1))}`;
  const p60Range = `${formatINR(Math.round(data.projection.p60.amount * 0.86))} - ${formatINR(Math.round(data.projection.p60.amount * 1.14))}`;
  const p90Range = `${formatINR(Math.round(data.projection.p90.amount * 0.82))} - ${formatINR(Math.round(data.projection.p90.amount * 1.18))}`;

  const stockAlertAmount = Math.round(data.projection.p30.amount / 4);
  const alertMessage = `Projected inflow for next 7 days: ${formatINR(stockAlertAmount)}. You are clear to reorder stock.`;

  return (
    <div className="space-y-4">
      <section className="grid gap-3 sm:grid-cols-3">
        <MetricCard label="p30 Projection" value={formatINRCompactLakh(data.projection.p30.amount)} sublabel={`${p30Range} (${data.projection.p30.confidence}% confidence)`} />
        <MetricCard label="p60 Projection" value={formatINRCompactLakh(data.projection.p60.amount)} sublabel={`${p60Range} (${data.projection.p60.confidence}% confidence)`} />
        <MetricCard label="p90 Projection" value={formatINRCompactLakh(data.projection.p90.amount)} sublabel={`${p90Range} (${data.projection.p90.confidence}% confidence)`} />
      </section>

      <CashflowChart history={data.history} projection={data.projection} windowDays={windowDays} onWindowChange={setWindowDays} />

      <section className="paytm-surface p-5">
        <h3 className="text-lg font-black text-[#002970]">Daily Revenue Table</h3>
        <div className="mt-3">
          <DataTable
            columns={[
              { key: 'date', header: 'Date' },
              { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
              { key: 'transactionCount', header: 'Transactions' },
              {
                key: 'range',
                header: 'Range',
                render: (_value, row) => `${formatINR(Number(row.lowerBound))} - ${formatINR(Number(row.upperBound))}`,
              },
            ]}
            data={data.history.slice(-windowDays).reverse() as unknown as Record<string, unknown>[]}
          />
        </div>
      </section>

      <section className="paytm-surface p-5">
        <h3 className="text-lg font-black text-[#002970]">Seasonal Campaign Planner</h3>
        <p className="mt-2 text-sm text-slate-600">{alertMessage}</p>
        <Button
          className="mt-3 rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
          onClick={async () => {
            const message = WHATSAPP_TEMPLATES.stockReorderAlert({ amount: stockAlertAmount });
            await adapter.sendWhatsappAlert({
              merchantId: session.merchantId as string,
              phone: DEMO_WHATSAPP_PHONE,
              message,
            });
            toast.whatsapp(message, DEMO_WHATSAPP_PHONE);
          }}
        >
          Send WhatsApp Alert
        </Button>
      </section>
    </div>
  );
}
