'use client';

import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { StatusBadge } from '@/src/components/ui';

export default function AdminSystemPage() {
  const { data } = useSWR('admin-system', async () => {
    const merchants = await adapter.getMerchants();
    const audits = await Promise.all(merchants.map((merchant) => adapter.getAuditLog(merchant.merchantId)));
    const notifications = await Promise.all(merchants.map((merchant) => adapter.getNotifications(merchant.merchantId)));

    return {
      merchants: merchants.length,
      auditEvents24h: audits.flat().filter((entry) => Date.now() - new Date(entry.timestamp).getTime() < 24 * 60 * 60 * 1000).length,
      unreadAlerts: notifications.flat().filter((item) => !item.read).length,
      adapterMode: process.env.NEXT_PUBLIC_ADAPTER_MODE ?? 'mock',
    };
  });

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">System Health</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Runtime and Adapter Status</h1>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Adapter Mode</p>
          <p className="mt-1 text-xl font-black text-[#002970]">{data?.adapterMode ?? 'mock'}</p>
          <div className="mt-2">
            <StatusBadge status="ACTIVE" />
          </div>
        </article>

        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Active Merchants</p>
          <p className="mt-1 text-xl font-black text-[#002970]">{data?.merchants ?? '-'}</p>
          <div className="mt-2">
            <StatusBadge status="ACTIVE" />
          </div>
        </article>

        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Audit Events (24h)</p>
          <p className="mt-1 text-xl font-black text-[#002970]">{data?.auditEvents24h ?? '-'}</p>
          <div className="mt-2">
            <StatusBadge status="ACTIVE" />
          </div>
        </article>

        <article className="paytm-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Unread Alerts</p>
          <p className="mt-1 text-xl font-black text-[#002970]">{data?.unreadAlerts ?? '-'}</p>
          <div className="mt-2">
            <StatusBadge status={(data?.unreadAlerts ?? 0) > 5 ? 'FLAGGED' : 'ACTIVE'} />
          </div>
        </article>
      </section>

      <section className="paytm-surface p-5 text-sm text-slate-700">
        <p className="font-semibold text-[#002970]">Live integration checklist</p>
        <ul className="mt-2 list-disc pl-5 space-y-1">
          <li>Switch NEXT_PUBLIC_ADAPTER_MODE from mock to live.</li>
          <li>Implement API endpoints in src/adapters/live.ts.</li>
          <li>Map merchant-scoped auth token in adapter request headers.</li>
          <li>Enable webhook flow for WhatsApp delivery receipts.</li>
        </ul>
      </section>
    </div>
  );
}
