'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Home, Bot, Wallet, History, User } from 'lucide-react';

const items = [
  { href: '/consumer/home', label: 'Home', icon: Home },
  { href: '/consumer/paybot', label: 'PayBot', icon: Bot },
  { href: '/consumer/wallet', label: 'Wallet', icon: Wallet },
  { href: '/consumer/history', label: 'History', icon: History },
  { href: '/consumer/profile', label: 'Profile', icon: User },
];

export function ConsumerNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-[#dbe4f3] bg-white/95 backdrop-blur">
      <div className="container-paytm flex items-center justify-between py-3">
        <Link href="/" className="flex items-center gap-1 text-2xl font-black tracking-tight">
          <span className="text-[#00BAF2]">pay</span>
          <span className="text-[#002970]">tm</span>
        </Link>

        <nav className="flex items-center gap-1">
          {items.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-3 py-2 text-xs font-semibold',
                  active ? 'bg-[#eef5ff] text-[#002970]' : 'text-slate-600 hover:bg-[#f6f9ff]',
                )}
              >
                <Icon size={14} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
