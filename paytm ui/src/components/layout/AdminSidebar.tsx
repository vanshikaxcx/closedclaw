'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Users, Workflow, Landmark, ClipboardList, Server, BellRing } from 'lucide-react';

const items = [
  { href: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/merchants', label: 'Merchants', icon: Users },
  { href: '/admin/gst/pipeline', label: 'GST Pipeline', icon: Workflow },
  { href: '/admin/financing', label: 'Financing', icon: Landmark },
  { href: '/admin/audit', label: 'Audit', icon: ClipboardList },
  { href: '/admin/system', label: 'System', icon: Server },
  { href: '/admin/alerts', label: 'Alerts', icon: BellRing },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="paytm-surface sticky top-3 hidden h-[calc(100vh-24px)] w-[240px] p-4 lg:block">
      <Link href="/" className="mb-6 flex items-center gap-1 text-2xl font-black tracking-tight">
        <span className="text-[#00BAF2]">pay</span>
        <span className="text-[#002970]">tm</span>
      </Link>

      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2 rounded-xl border-l-2 px-3 py-2 text-sm font-semibold transition',
                active ? 'border-l-[#002970] bg-[#eef5ff] text-[#002970]' : 'border-l-transparent text-slate-700 hover:bg-[#f6f9ff]',
              )}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
