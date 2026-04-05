'use client';

import { useMemo } from 'react';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/protected-route';
import { useAuth } from '@/lib/auth-context';
import { AdminSidebar } from '@/src/components/layout/AdminSidebar';

function titleForAdmin(pathname: string): string {
  if (pathname === '/admin/dashboard') return 'Admin Dashboard';
  if (pathname.startsWith('/admin/merchants')) return 'Merchant Management';
  if (pathname.startsWith('/admin/gst/pipeline')) return 'GST Pipeline';
  if (pathname.startsWith('/admin/financing')) return 'Financing Monitor';
  if (pathname.startsWith('/admin/audit')) return 'Audit Explorer';
  if (pathname.startsWith('/admin/system')) return 'System Health';
  if (pathname.startsWith('/admin/alerts')) return 'Alerts';
  return 'Admin Portal';
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { session } = useAuth();

  const title = useMemo(() => titleForAdmin(pathname), [pathname]);

  return (
    <ProtectedRoute role="admin">
      <div className="app-shell-bg min-h-screen">
        <div className="container-paytm flex gap-4 py-3">
          <AdminSidebar />

          <section className="min-w-0 flex-1 pb-4">
            <header className="paytm-surface mb-4 flex items-center justify-between px-5 py-4">
              <h1 className="text-2xl font-black text-[#002970]">{title}</h1>
              <div className="text-right">
                <p className="text-sm font-bold text-slate-800">{session?.name ?? 'Admin'}</p>
                <p className="text-xs text-slate-500">Operations Console</p>
              </div>
            </header>
            {children}
          </section>
        </div>
      </div>
    </ProtectedRoute>
  );
}
