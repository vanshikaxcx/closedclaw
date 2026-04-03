'use client';

import { useMemo, useState } from 'react';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/src/components/ui/DataTable';
import { formatDate, formatINR } from '@/src/lib/format';

const historyRows = Array.from({ length: 18 }).map((_, index) => ({
  id: `H-${1000 + index}`,
  merchant: ['Ramesh General Store', 'Metro Recharge', 'UPI Transfer', 'Bus Booking'][index % 4],
  amount: index % 3 === 0 ? 650 + index * 11 : -(240 + index * 19),
  date: new Date(Date.now() - index * 86400000).toISOString(),
}));

export default function ConsumerHistoryPage() {
  const [query, setQuery] = useState('');

  const filtered = useMemo(
    () => historyRows.filter((row) => row.merchant.toLowerCase().includes(query.toLowerCase()) || row.id.toLowerCase().includes(query.toLowerCase())),
    [query],
  );

  return (
    <section className="paytm-surface p-5">
      <h1 className="text-2xl font-black text-[#002970]">Transaction History</h1>
      <div className="mt-3 max-w-sm">
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by merchant or Tx ID" className="h-11 rounded-xl border-[#cbd8eb]" />
      </div>

      <div className="mt-4">
        <DataTable
          columns={[
            { key: 'id', header: 'Tx ID' },
            { key: 'merchant', header: 'Merchant' },
            { key: 'date', header: 'Date', render: (value) => formatDate(String(value)) },
            {
              key: 'amount',
              header: 'Amount',
              render: (value) => {
                const amount = Number(value);
                return <span className={amount < 0 ? 'text-red-600' : 'text-emerald-700'}>{formatINR(amount)}</span>;
              },
            },
          ]}
          data={filtered as unknown as Record<string, unknown>[]}
        />
      </div>
    </section>
  );
}
