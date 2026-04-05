'use client';

import Link from 'next/link';
import { Wallet2, QrCode, Smartphone, Bot } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { formatINR, formatDateTime } from '@/src/lib/format';

const tx = [
  { id: 'C-1001', name: 'Ramesh General Store', amount: -213, date: new Date().toISOString() },
  { id: 'C-1002', name: 'Metro Recharge', amount: -399, date: new Date(Date.now() - 86400000).toISOString() },
  { id: 'C-1003', name: 'Wallet Topup', amount: 2500, date: new Date(Date.now() - 2 * 86400000).toISOString() },
  { id: 'C-1004', name: 'UPI Transfer', amount: -1200, date: new Date(Date.now() - 3 * 86400000).toISOString() },
  { id: 'C-1005', name: 'Bus Tickets', amount: -680, date: new Date(Date.now() - 4 * 86400000).toISOString() },
];

export default function ConsumerHomePage() {
  const { session } = useAuth();

  return (
    <div className="space-y-5">
      <section className="paytm-surface p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Wallet Snapshot</p>
        <h1 className="mt-2 text-3xl font-black text-[#002970]">{session?.name ?? 'Consumer'}</h1>
        <p className="mt-2 text-sm text-slate-600">Available balance</p>
        <p className="mt-1 text-4xl font-black text-[#002970]">{formatINR(12840)}</p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2">
        {[
          { href: '/consumer/home', label: 'Pay', icon: QrCode },
          { href: '/recharge-bills', label: 'Recharge', icon: Smartphone },
          { href: '/consumer/wallet', label: 'Send Money', icon: Wallet2 },
          { href: '/consumer/paybot', label: 'PayBot', icon: Bot },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.label} href={item.href} className="paytm-surface flex items-center gap-3 p-4 hover:bg-[#f7fbff]">
              <div className="rounded-full bg-[#eef5ff] p-2 text-[#002970]">
                <Icon size={18} />
              </div>
              <span className="text-sm font-semibold text-slate-700">{item.label}</span>
            </Link>
          );
        })}
      </section>

      <section className="paytm-surface p-5">
        <h2 className="text-lg font-black text-[#002970]">Recent Transactions</h2>
        <div className="mt-3 divide-y divide-[#e6ecf6]">
          {tx.map((row) => (
            <div key={row.id} className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#eef5ff] text-xs font-bold text-[#002970]">
                  {row.name.charAt(0)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{row.name}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(row.date)}</p>
                </div>
              </div>
              <p className={`text-sm font-semibold ${row.amount < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                {row.amount < 0 ? '-' : '+'}
                {formatINR(Math.abs(row.amount))}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
