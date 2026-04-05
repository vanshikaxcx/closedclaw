'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Wallet,
  ReceiptText,
  ShieldCheck,
  FileSearch,
  ArrowLeftRight,
  Bell,
  ClipboardList,
  MessageCircle,
  ScanLine,
  TrendingUp,
  Landmark,
  User,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface MerchantSidebarProps {
  unreadNotifications?: number;
  onLogout: () => void;
}

const menu = [
  {
    section: 'Overview',
    items: [{ label: 'Dashboard', href: '/merchant/dashboard', icon: LayoutDashboard }],
  },
  {
    section: 'Finance',
    items: [
      { label: 'CashFlow', href: '/merchant/cashflow', icon: TrendingUp },
      { label: 'GST', href: '/merchant/gst/overview', icon: ReceiptText },
      { label: 'TrustScore', href: '/merchant/trust-score', icon: ShieldCheck },
      { label: 'Invoices', href: '/merchant/invoices', icon: FileSearch },
      { label: 'Finance Offers', href: '/merchant/finance/offers', icon: Landmark },
      { label: 'Bill Scanner', href: '/merchant/bill-scanner', icon: ScanLine },
      { label: 'Tax Assistant', href: '/merchant/tax-assistant', icon: MessageCircle },
    ],
  },
  {
    section: 'Money',
    items: [
      { label: 'Wallet', href: '/merchant/wallet', icon: Wallet },
      { label: 'Transfers', href: '/merchant/transfers', icon: ArrowLeftRight },
    ],
  },
  {
    section: 'Records',
    items: [
      { label: 'Audit Log', href: '/merchant/audit', icon: ClipboardList },
      { label: 'Notifications', href: '/merchant/notifications', icon: Bell },
    ],
  },
];

const mobileItems = [
  { label: 'Home', href: '/merchant/dashboard', icon: LayoutDashboard },
  { label: 'GST', href: '/merchant/gst/review', icon: ReceiptText },
  { label: 'Scan', href: '/merchant/bill-scanner', icon: ScanLine },
  { label: 'Bot', href: '/merchant/tax-assistant', icon: MessageCircle },
  { label: 'Invoices', href: '/merchant/invoices', icon: FileSearch },
  { label: 'Wallet', href: '/merchant/wallet', icon: Wallet },
];

export function MerchantSidebar({ unreadNotifications = 0, onLogout }: MerchantSidebarProps) {
  const pathname = usePathname();

  return (
    <>
      <aside className="paytm-surface sticky top-3 hidden h-[calc(100vh-24px)] w-60 flex-col overflow-y-auto p-4 lg:flex">
        <Link href="/" className="mb-5 flex items-center gap-1 text-2xl font-black tracking-tight">
          <span className="text-[#00BAF2]">pay</span>
          <span className="text-[#002970]">tm</span>
        </Link>

        <div className="flex-1 space-y-5">
          {menu.map((group) => (
            <div key={group.section}>
              <p className="mb-1 px-2 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">{group.section}</p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const Icon = item.icon;
                  const isNotifications = item.href === '/merchant/notifications';

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        'flex items-center justify-between rounded-xl border-l-2 px-2 py-2 text-sm font-semibold transition',
                        active
                          ? 'border-l-[#002970] bg-[#eef5ff] text-[#002970]'
                          : 'border-l-transparent text-slate-700 hover:bg-[#f6f9ff]',
                      )}
                    >
                      <span className="inline-flex items-center gap-2">
                        <Icon size={16} />
                        {item.label}
                      </span>
                      {isNotifications && unreadNotifications > 0 ? (
                        <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#EF4444] px-1.5 text-[10px] font-bold text-white">
                          {unreadNotifications}
                        </span>
                      ) : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 border-t border-[#e2e9f4] pt-3">
          <Link href="/merchant/profile" className="mb-1 flex items-center gap-2 rounded-xl px-2 py-2 text-sm font-semibold text-slate-700 hover:bg-[#f6f9ff]">
            <User size={16} />
            Profile
          </Link>
          <button
            type="button"
            onClick={onLogout}
            className="flex w-full items-center gap-2 rounded-xl px-2 py-2 text-sm font-semibold text-slate-700 hover:bg-red-50 hover:text-red-600"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      <nav className="fixed inset-x-0 bottom-0 z-70 border-t border-[#dbe4f3] bg-white px-2 py-1 lg:hidden">
        <div className="grid grid-cols-6 gap-1">
          {mobileItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex flex-col items-center rounded-lg px-1 py-2 text-[11px] font-semibold',
                  active ? 'bg-[#eef5ff] text-[#002970]' : 'text-slate-600',
                )}
              >
                <Icon size={16} />
                <span className="mt-1">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
