'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { Download } from 'lucide-react';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { useAuth } from '@/src/context/auth-context';
import { formatDateTime, formatINR } from '@/src/lib/format';

export default function MerchantAuditPage() {
  const { session } = useAuth();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'failed' | 'pending'>('all');

  const { data } = useSWR(
    session?.merchantId ? (['merchant-audit', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getAuditLog(merchantId);
    },
  );

  const filtered = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.filter((item) => {
      const matchesStatus = statusFilter === 'all' || item.outcome === statusFilter;
      const searchable = `${item.action} ${item.actorType} ${item.actorId} ${item.entityId}`.toLowerCase();
      const matchesQuery = searchable.includes(query.trim().toLowerCase());
      return matchesStatus && matchesQuery;
    });
  }, [data, query, statusFilter]);

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Audit Trail</p>
            <h1 className="mt-1 text-2xl font-black text-[#002970]">Immutable Activity Logs</h1>
            <p className="mt-1 text-sm text-slate-600">Filter all GST, financing, transfer, and profile actions from one timeline.</p>
          </div>

          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-full border border-[#d1daea] px-4 py-2 text-sm font-semibold text-[#002970]"
          >
            <Download size={16} /> Export CSV
          </button>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_auto]">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search action, actor, entity..."
            className="h-10 w-full rounded-full border border-[#d1daea] px-4 text-sm outline-none focus:border-[#00BAF2]"
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}
            className="h-10 rounded-full border border-[#d1daea] px-3 text-sm"
          >
            <option value="all">All statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </section>

      <section className="paytm-surface p-5">
        <DataTable
          columns={[
            { key: 'timestamp', header: 'Date', render: (value) => formatDateTime(String(value)) },
            {
              key: 'action',
              header: 'Action',
              render: (value) => (
                <span className="font-semibold uppercase tracking-[0.08em] text-[#002970]">{String(value).replace(/_/g, ' ')}</span>
              ),
            },
            {
              key: 'actorType',
              header: 'Actor',
              render: (_value, row) => `${String(row.actorType)} (${String(row.actorId)})`,
            },
            { key: 'entityId', header: 'Entity' },
            {
              key: 'amount',
              header: 'Amount',
              render: (value) => {
                if (value == null) {
                  return '-';
                }
                return formatINR(Number(value));
              },
            },
            {
              key: 'outcome',
              header: 'Status',
              render: (value) => <StatusBadge status={String(value) === 'success' ? 'PAID' : 'OVERDUE'} />,
            },
          ]}
          data={filtered as unknown as Record<string, unknown>[]}
        />
      </section>
    </div>
  );
}
