'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { StatusBadge } from '@/src/components/ui';
import { useToast } from '@/src/context/toast-context';
import { formatDateTime } from '@/src/lib/format';

interface AlertRow {
  merchantId: string;
  merchantName: string;
  notifId: string;
  type: string;
  title: string;
  body: string;
  read: boolean;
  timestamp: string;
}

export default function AdminAlertsPage() {
  const toast = useToast();
  const [tab, setTab] = useState<'all' | 'unread'>('all');

  const { data, mutate } = useSWR('admin-alerts', async () => {
    const merchants = await adapter.getMerchants();
    const rows = await Promise.all(
      merchants.map(async (merchant) => {
        const notifications = await adapter.getNotifications(merchant.merchantId);
        return notifications.map(
          (item) =>
            ({
              merchantId: merchant.merchantId,
              merchantName: merchant.businessName,
              notifId: item.notifId,
              type: item.type,
              title: item.title,
              body: item.body,
              read: item.read,
              timestamp: item.timestamp,
            }) satisfies AlertRow,
        );
      }),
    );

    return rows.flat().sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime());
  });

  const visible = useMemo(() => {
    if (!data) {
      return [];
    }
    if (tab === 'unread') {
      return data.filter((row) => !row.read);
    }
    return data;
  }, [data, tab]);

  const markRead = async (row: AlertRow) => {
    await adapter.markNotificationRead(row.merchantId, row.notifId);
    toast.success('Alert marked as read.');
    await mutate();
  };

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Alerts Console</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Actionable Notifications</h1>

        <div className="mt-4 inline-flex rounded-full border border-[#d1daea] bg-white p-1">
          <button
            type="button"
            onClick={() => setTab('all')}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${tab === 'all' ? 'bg-[#002970] text-white' : 'text-slate-600'}`}
          >
            All ({data?.length ?? 0})
          </button>
          <button
            type="button"
            onClick={() => setTab('unread')}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${tab === 'unread' ? 'bg-[#002970] text-white' : 'text-slate-600'}`}
          >
            Unread ({data?.filter((item) => !item.read).length ?? 0})
          </button>
        </div>
      </section>

      <section className="space-y-3">
        {visible.map((row) => (
          <article key={`${row.merchantId}-${row.notifId}`} className="paytm-surface p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">{row.merchantName}</p>
                <p className="mt-1 text-sm font-bold text-[#002970]">{row.title}</p>
                <p className="mt-1 text-sm text-slate-700">{row.body}</p>
                <p className="mt-2 text-xs text-slate-500">{formatDateTime(row.timestamp)}</p>
              </div>

              <div className="flex items-center gap-2">
                <StatusBadge status={row.read ? 'INACTIVE' : 'ACTIVE'} />
                {!row.read ? (
                  <button
                    type="button"
                    onClick={() => void markRead(row)}
                    className="rounded-full border border-[#d1daea] px-3 py-1 text-xs font-semibold text-[#002970]"
                  >
                    Mark read
                  </button>
                ) : null}
              </div>
            </div>
          </article>
        ))}

        {!visible.length ? (
          <div className="paytm-surface p-8 text-center text-sm text-slate-600">No alerts in this tab.</div>
        ) : null}
      </section>
    </div>
  );
}
