'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { formatDateTime, formatINR } from '@/src/lib/format';

export default function MerchantWalletPage() {
  const { session } = useAuth();
  const [dateRange, setDateRange] = useState('30d');

  const { data } = useSWR(
    session?.merchantId ? (['merchant-wallet', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      const [wallet, audit] = await Promise.all([adapter.getWalletBalance(merchantId), adapter.getAuditLog(merchantId)]);
      return { wallet, audit };
    },
  );

  const transferRows = useMemo(
    () =>
      data?.audit
        .filter((row) => row.action.includes('transfer'))
        .map((row) => ({
          date: row.timestamp,
          description: row.action.replace(/_/g, ' '),
          amount: Number(row.amount ?? 0),
          status: row.outcome,
        })) ?? [],
    [data],
  );

  if (!data) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading wallet...</div>;
  }

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Paytm Wallet</p>
        <h1 className="mt-2 text-5xl font-black text-[#002970]">{formatINR(data.wallet.balance)}</h1>
        <p className="mt-1 text-sm text-slate-600">Last updated {formatDateTime(data.wallet.lastUpdated)}</p>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full border-[#002970] text-[#002970]">
            Add Money
          </Button>
          <Button variant="outline" className="rounded-full border-[#002970] text-[#002970]">
            Withdraw to Bank
          </Button>
          <Link href="/merchant/transfers" className="inline-flex rounded-full bg-[#002970] px-4 py-2 text-sm font-semibold text-white">
            Transfer Money
          </Link>
        </div>
      </section>

      <section className="paytm-surface p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-black text-[#002970]">Transaction History</h2>
          <select
            value={dateRange}
            onChange={(event) => setDateRange(event.target.value)}
            className="rounded-full border border-[#d1daea] px-3 py-1 text-xs"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>

        <div className="mt-3">
          <DataTable
            columns={[
              { key: 'date', header: 'Date', render: (value) => formatDateTime(String(value)) },
              { key: 'description', header: 'Description' },
              {
                key: 'amount',
                header: 'Amount',
                render: (value) => {
                  const amount = Number(value);
                  return <span className={amount < 0 ? 'text-red-600' : 'text-emerald-700'}>{formatINR(amount)}</span>;
                },
              },
              {
                key: 'status',
                header: 'Status',
                render: (value) => <StatusBadge status={String(value) === 'success' ? 'PAID' : 'OVERDUE'} />,
              },
            ]}
            data={transferRows as unknown as Record<string, unknown>[]}
          />
        </div>
      </section>
    </div>
  );
}
