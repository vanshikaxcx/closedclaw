'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { formatDateTime, formatINR } from '@/src/lib/format';

interface AdminAuditRow {
  merchantId: string;
  merchantName: string;
  timestamp: string;
  action: string;
  actorType: string;
  outcome: 'success' | 'failed' | 'pending';
  amount?: number;
}

export default function AdminAuditPage() {
  const [query, setQuery] = useState('');

  const { data } = useSWR('admin-audit', async () => {
    const merchants = await adapter.getMerchants();
    const rows = await Promise.all(
      merchants.map(async (merchant) => {
        const entries = await adapter.getAuditLog(merchant.merchantId);
        return entries.map(
          (entry) =>
            ({
              merchantId: merchant.merchantId,
              merchantName: merchant.businessName,
              timestamp: entry.timestamp,
              action: entry.action,
              actorType: entry.actorType,
              outcome: entry.outcome,
              amount: entry.amount,
            }) satisfies AdminAuditRow,
        );
      }),
    );

    return rows.flat().sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime());
  });

  const filtered = useMemo(() => {
    if (!data) {
      return [];
    }

    return data.filter((row) => {
      const searchBlob = `${row.merchantId} ${row.merchantName} ${row.action} ${row.actorType}`.toLowerCase();
      return searchBlob.includes(query.trim().toLowerCase());
    });
  }, [data, query]);

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Audit Explorer</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Cross-Merchant Activity Log</h1>

        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search merchant, action, actor..."
          className="mt-4 h-10 w-full rounded-full border border-[#d1daea] px-4 text-sm outline-none focus:border-[#00BAF2]"
        />
      </section>

      <section className="paytm-surface p-5">
        <DataTable
          columns={[
            { key: 'timestamp', header: 'Date', render: (value) => formatDateTime(String(value)) },
            { key: 'merchantName', header: 'Merchant' },
            { key: 'action', header: 'Action', render: (value) => String(value).replace(/_/g, ' ') },
            { key: 'actorType', header: 'Actor' },
            {
              key: 'amount',
              header: 'Amount',
              render: (value) => (value == null ? '-' : formatINR(Number(value))),
            },
            {
              key: 'outcome',
              header: 'Status',
              render: (value) => <StatusBadge status={String(value) === 'success' ? 'ACTIVE' : 'FLAGGED'} />,
            },
          ]}
          data={filtered as unknown as Record<string, unknown>[]}
        />
      </section>
    </div>
  );
}
