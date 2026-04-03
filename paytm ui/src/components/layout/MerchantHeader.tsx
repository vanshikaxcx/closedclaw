'use client';

import Link from 'next/link';
import { Bell } from 'lucide-react';
import { initials } from '@/src/lib/format';

interface MerchantHeaderProps {
  title: string;
  merchantName: string;
  unreadCount?: number;
  isDemoMode?: boolean;
}

export function MerchantHeader({ title, merchantName, unreadCount = 0, isDemoMode = false }: MerchantHeaderProps) {
  return (
    <header className="paytm-surface mb-4 flex items-center justify-between px-5 py-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-black text-[#002970]">{title}</h1>
        {isDemoMode ? (
          <span className="rounded-full bg-[#F59E0B]/20 px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-[#a16207]">
            Demo Mode
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <Link href="/merchant/notifications" className="relative rounded-full border border-[#d1daea] p-2 text-slate-700 hover:bg-[#f3f7ff]">
          <Bell size={17} />
          {unreadCount > 0 ? (
            <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#EF4444] px-1 text-[10px] font-bold text-white">
              {unreadCount}
            </span>
          ) : null}
        </Link>

        <div className="text-right">
          <p className="text-sm font-bold text-slate-800">{merchantName}</p>
          <p className="text-xs text-slate-500">Merchant Portal</p>
        </div>

        <div className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#002970] text-sm font-bold text-white">
          {initials(merchantName)}
        </div>
      </div>
    </header>
  );
}
