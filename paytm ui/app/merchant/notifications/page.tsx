'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { Bell, CheckCheck } from 'lucide-react';
import { adapter } from '@/src/adapters';
import { useAuth } from '@/src/context/auth-context';
import { useToast } from '@/src/context/toast-context';
import { formatDateTime } from '@/src/lib/format';

export default function MerchantNotificationsPage() {
  const { session } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState<'all' | 'unread'>('all');

  const { data, mutate } = useSWR(
    session?.merchantId ? (['merchant-notifications', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getNotifications(merchantId);
    },
  );

  const visible = useMemo(() => {
    if (!data) {
      return [];
    }
    if (tab === 'unread') {
      return data.filter((item) => !item.read);
    }
    return data;
  }, [data, tab]);

  const unreadCount = data?.filter((item) => !item.read).length ?? 0;

  const markAll = async () => {
    if (!session?.merchantId) {
      return;
    }
    await adapter.markAllNotificationsRead(session.merchantId);
    toast.success('All notifications marked as read.');
    await mutate();
  };

  const markOne = async (notifId: string) => {
    if (!session?.merchantId) {
      return;
    }
    await adapter.markNotificationRead(session.merchantId, notifId);
    await mutate();
  };

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Notification Center</p>
            <h1 className="mt-1 text-2xl font-black text-[#002970]">Alerts and Updates</h1>
            <p className="mt-1 text-sm text-slate-600">GST reminders, financing updates, transfer confirmations and risk alerts.</p>
          </div>

          <button
            type="button"
            onClick={() => void markAll()}
            className="inline-flex items-center gap-2 rounded-full border border-[#d1daea] px-4 py-2 text-sm font-semibold text-[#002970]"
          >
            <CheckCheck size={16} /> Mark all read
          </button>
        </div>

        <div className="mt-4 inline-flex rounded-full border border-[#d1daea] bg-white p-1">
          <button
            type="button"
            onClick={() => setTab('all')}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
              tab === 'all' ? 'bg-[#002970] text-white' : 'text-slate-600'
            }`}
          >
            All ({data?.length ?? 0})
          </button>
          <button
            type="button"
            onClick={() => setTab('unread')}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
              tab === 'unread' ? 'bg-[#002970] text-white' : 'text-slate-600'
            }`}
          >
            Unread ({unreadCount})
          </button>
        </div>
      </section>

      <section className="space-y-3">
        {visible.map((notification) => (
          <article
            key={notification.notifId}
            className={`paytm-surface p-4 ${notification.read ? 'border-[#e2e8f5]' : 'border-[#00BAF2]/40 bg-[#f5fbff]'}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-3">
                <span className="mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#002970]/10 text-[#002970]">
                  <Bell size={16} />
                </span>

                <div className="min-w-0">
                  <p className="text-sm font-bold text-[#002970]">{notification.title}</p>
                  <p className="mt-1 text-sm text-slate-700">{notification.body}</p>
                  <p className="mt-2 text-xs text-slate-500">{formatDateTime(notification.timestamp)}</p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                {!notification.read ? (
                  <button
                    type="button"
                    onClick={() => void markOne(notification.notifId)}
                    className="rounded-full border border-[#d1daea] px-3 py-1 text-xs font-semibold text-[#002970]"
                  >
                    Mark read
                  </button>
                ) : null}

                {notification.actionUrl ? (
                  <Link href={notification.actionUrl} className="rounded-full bg-[#002970] px-3 py-1 text-xs font-semibold text-white">
                    Open
                  </Link>
                ) : null}
              </div>
            </div>
          </article>
        ))}

        {!visible.length ? (
          <div className="paytm-surface p-8 text-center text-sm text-slate-600">No notifications in this tab.</div>
        ) : null}
      </section>
    </div>
  );
}
