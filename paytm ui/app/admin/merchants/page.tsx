'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { adapter } from '@/src/adapters';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { formatDate, formatINR } from '@/src/lib/format';

export default function AdminMerchantsPage() {
  const [query, setQuery] = useState('');
  const [kycFilter, setKycFilter] = useState<'all' | 'verified' | 'pending' | 'rejected'>('all');

  const { data } = useSWR('admin-merchants', () => adapter.getMerchants());

  const filtered = useMemo(() => {
    if (!data) {
      return [];
    }

    return data.filter((merchant) => {
      const matchesKYC = kycFilter === 'all' || merchant.kycStatus === kycFilter;
      const searchBlob = `${merchant.merchantId} ${merchant.name} ${merchant.businessName} ${merchant.gstin}`.toLowerCase();
      const matchesQuery = searchBlob.includes(query.trim().toLowerCase());
      return matchesKYC && matchesQuery;
    });
  }, [data, kycFilter, query]);

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Merchant Management</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Merchant Portfolio</h1>
        <p className="mt-1 text-sm text-slate-600">Search by merchant ID, GSTIN, or business name and jump into detailed controls.</p>

        <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_auto]">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search merchant, GSTIN, business..."
            className="h-10 w-full rounded-full border border-[#d1daea] px-4 text-sm outline-none focus:border-[#00BAF2]"
          />
          <select
            value={kycFilter}
            onChange={(event) => setKycFilter(event.target.value as typeof kycFilter)}
            className="h-10 rounded-full border border-[#d1daea] px-3 text-sm"
          >
            <option value="all">All KYC</option>
            <option value="verified">Verified</option>
            <option value="pending">Pending</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </section>

      <section className="paytm-surface p-5">
        <DataTable
          columns={[
            {
              key: 'merchantId',
              header: 'Merchant ID',
              render: (value, row) => (
                <Link href={`/admin/merchants/${String(row.merchantId)}`} className="font-semibold text-[#002970] hover:underline">
                  {String(value)}
                </Link>
              ),
            },
            { key: 'name', header: 'Owner' },
            { key: 'businessName', header: 'Business' },
            { key: 'gstin', header: 'GSTIN' },
            {
              key: 'kycStatus',
              header: 'KYC',
              render: (value) => {
                const status = String(value);
                if (status === 'verified') {
                  return <StatusBadge status="VERIFIED" />;
                }
                if (status === 'rejected') {
                  return <StatusBadge status="REJECTED" />;
                }
                return <StatusBadge status="PENDING" />;
              },
            },
            {
              key: 'walletBalance',
              header: 'Wallet',
              render: (value) => <span className="font-semibold">{formatINR(Number(value))}</span>,
            },
            { key: 'createdAt', header: 'Created', render: (value) => formatDate(String(value)) },
          ]}
          data={filtered as unknown as Record<string, unknown>[]}
        />
      </section>
    </div>
  );
}
