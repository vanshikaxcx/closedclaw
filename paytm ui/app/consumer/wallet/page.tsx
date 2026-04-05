'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/src/components/ui/DataTable';
import { formatINR, formatDate } from '@/src/lib/format';

const rows = [
  { id: 'W-1001', date: '2026-04-02', description: 'Wallet Topup', amount: 2000, status: 'success' },
  { id: 'W-1002', date: '2026-04-01', description: 'UPI transfer', amount: -640, status: 'success' },
  { id: 'W-1003', date: '2026-03-31', description: 'Recharge payment', amount: -349, status: 'success' },
  { id: 'W-1004', date: '2026-03-30', description: 'Refund', amount: 179, status: 'success' },
];

export default function ConsumerWalletPage() {
  const [balance] = useState(12840);

  return (
    <div className="space-y-5">
      <section className="paytm-surface p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Paytm Wallet</p>
        <h1 className="mt-2 text-4xl font-black text-[#002970]">{formatINR(balance)}</h1>
        <div className="mt-4 flex gap-2">
          <Button variant="outline" className="rounded-full border-[#002970] text-[#002970]">
            Add Money
          </Button>
          <Button variant="outline" className="rounded-full border-[#002970] text-[#002970]">
            Send Money
          </Button>
        </div>
      </section>

      <section className="paytm-surface p-5">
        <h2 className="text-lg font-black text-[#002970]">Transaction History</h2>
        <div className="mt-3">
          <DataTable
            columns={[
              { key: 'date', header: 'Date', render: (value) => formatDate(String(value)) },
              { key: 'description', header: 'Description' },
              {
                key: 'amount',
                header: 'Amount',
                render: (value) => {
                  const amount = Number(value);
                  return <span className={amount < 0 ? 'text-red-600' : 'text-emerald-700'}>{formatINR(amount)}</span>;
                },
              },
              { key: 'status', header: 'Status' },
            ]}
            data={rows as unknown as Record<string, unknown>[]}
          />
        </div>
      </section>
    </div>
  );
}
