'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useParams } from 'next/navigation';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { useToast } from '@/src/context/toast-context';
import { formatDate, formatDateTime, formatINR } from '@/src/lib/format';

export default function AdminMerchantDetailPage() {
  const params = useParams<{ merchantId: string }>();
  const merchantId = String(params.merchantId ?? '');
  const toast = useToast();

  const { data } = useSWR(
    merchantId ? (['admin-merchant-detail', merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const id = key[1];
      const [profile, trust, gst, invoices, audit, notifications] = await Promise.all([
        adapter.getMerchantProfile(id),
        adapter.getTrustScore(id),
        adapter.getGSTDraft(id),
        adapter.getInvoices(id),
        adapter.getAuditLog(id),
        adapter.getNotifications(id),
      ]);
      return { profile, trust, gst, invoices, audit, notifications };
    },
  );

  const overdueInvoices = useMemo(
    () => data?.invoices.filter((row) => row.status === 'OVERDUE').length ?? 0,
    [data],
  );

  if (!data) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading merchant profile...</div>;
  }

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link href="/admin/merchants" className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2] hover:underline">
              Back to Merchant List
            </Link>
            <h1 className="mt-2 text-2xl font-black text-[#002970]">{data.profile.businessName}</h1>
            <p className="text-sm text-slate-600">
              {data.profile.name} • {data.profile.merchantId} • GSTIN {data.profile.gstin}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="rounded-full border-[#d1daea]"
              onClick={() => toast.warning('KYC recheck queued in audit log (demo placeholder).')}
            >
              Request KYC Recheck
            </Button>
            <Button
              variant="outline"
              className="rounded-full border-[#d1daea]"
              onClick={() => toast.warning('Funding freeze action is sandbox-only in demo mode.')}
            >
              Freeze Financing
            </Button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-[#d7dfef] bg-white p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Wallet</p>
            <p className="mt-1 text-xl font-black text-[#002970]">{formatINR(data.profile.walletBalance)}</p>
          </div>
          <div className="rounded-2xl border border-[#d7dfef] bg-white p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">TrustScore</p>
            <p className="mt-1 text-xl font-black text-[#002970]">{data.trust.score}</p>
          </div>
          <div className="rounded-2xl border border-[#d7dfef] bg-white p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">GST Flagged Rows</p>
            <p className="mt-1 text-xl font-black text-[#002970]">{data.gst.summary.flaggedCount}</p>
          </div>
          <div className="rounded-2xl border border-[#d7dfef] bg-white p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Overdue Invoices</p>
            <p className="mt-1 text-xl font-black text-[#002970]">{overdueInvoices}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Invoice Ledger</h2>
          <div className="mt-3">
            <DataTable
              columns={[
                { key: 'invoiceId', header: 'Invoice' },
                { key: 'buyerName', header: 'Buyer' },
                { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
                { key: 'dueDate', header: 'Due Date', render: (value) => formatDate(String(value)) },
                {
                  key: 'status',
                  header: 'Status',
                  render: (value) => <StatusBadge status={String(value) as 'PAID' | 'PENDING' | 'OVERDUE' | 'FINANCED'} />,
                },
              ]}
              data={data.invoices as unknown as Record<string, unknown>[]}
            />
          </div>
        </article>

        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Recent Alerts</h2>
          <div className="mt-3 space-y-2">
            {data.notifications.slice(0, 5).map((notification) => (
              <div key={notification.notifId} className="rounded-xl border border-[#d7dfef] bg-white p-3">
                <p className="text-sm font-bold text-[#002970]">{notification.title}</p>
                <p className="mt-1 text-xs text-slate-600">{notification.body}</p>
                <p className="mt-2 text-[11px] text-slate-500">{formatDateTime(notification.timestamp)}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="paytm-surface p-5">
        <h2 className="text-lg font-black text-[#002970]">Recent Audit Entries</h2>
        <div className="mt-3">
          <DataTable
            columns={[
              { key: 'timestamp', header: 'Date', render: (value) => formatDateTime(String(value)) },
              { key: 'action', header: 'Action', render: (value) => String(value).replace(/_/g, ' ') },
              { key: 'actorType', header: 'Actor' },
              {
                key: 'outcome',
                header: 'Outcome',
                render: (value) => <StatusBadge status={String(value) === 'success' ? 'ACTIVE' : 'OVERDUE'} />,
              },
            ]}
            data={data.audit.slice(0, 8) as unknown as Record<string, unknown>[]}
          />
        </div>
      </section>
    </div>
  );
}
