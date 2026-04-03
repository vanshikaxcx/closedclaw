'use client';

import { useAuth } from '@/lib/auth-context';

export default function ConsumerProfilePage() {
  const { session } = useAuth();

  return (
    <div className="paytm-surface p-6">
      <h1 className="text-2xl font-black text-[#002970]">Consumer Profile</h1>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-[#e1e8f5] bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Name</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{session?.name ?? 'Consumer'}</p>
        </div>
        <div className="rounded-xl border border-[#e1e8f5] bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Phone</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{session?.phone ?? '+91XXXXXXXXXX'}</p>
        </div>
      </div>
    </div>
  );
}
