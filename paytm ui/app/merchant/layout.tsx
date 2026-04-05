'use client';

import { useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/protected-route';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import { ArthsetuErrorBoundary } from '@/src/components/shared/ArthsetuErrorBoundary';
import { VoiceBotWidget } from '@/src/components/shared/VoiceBotWidget';
import { MerchantHeader } from '@/src/components/layout/MerchantHeader';
import { MerchantSidebar } from '@/src/components/layout/MerchantSidebar';

function titleForPath(pathname: string): string {
  if (pathname === '/merchant/dashboard') {
    return 'Dashboard';
  }
  if (pathname.startsWith('/merchant/cashflow')) {
    return 'CashFlow';
  }
  if (pathname.startsWith('/merchant/gst/overview')) {
    return 'GST Overview';
  }
  if (pathname.startsWith('/merchant/gst/review')) {
    return 'GST Review';
  }
  if (pathname.startsWith('/merchant/gst/history')) {
    return 'GST History';
  }
  if (pathname.startsWith('/merchant/bill-scanner')) {
    return 'Bill Scanner';
  }
  if (pathname.startsWith('/merchant/tax-assistant')) {
    return 'Tax Assistant';
  }
  if (pathname.startsWith('/merchant/trust-score')) {
    return 'TrustScore';
  }
  if (pathname.startsWith('/merchant/invoices')) {
    return 'Invoices';
  }
  if (pathname.startsWith('/merchant/finance/offers')) {
    return 'Finance Offers';
  }
  if (pathname.startsWith('/merchant/wallet')) {
    return 'Wallet';
  }
  if (pathname.startsWith('/merchant/transfers')) {
    return 'Transfers';
  }
  if (pathname.startsWith('/merchant/audit')) {
    return 'Audit Log';
  }
  if (pathname.startsWith('/merchant/notifications')) {
    return 'Notifications';
  }
  if (pathname.startsWith('/merchant/profile')) {
    return 'Profile';
  }
  return 'Merchant Portal';
}

export default function MerchantLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { session, logout, isDemoMode } = useAuth();
  const [unread, setUnread] = useState(0);

  const pageTitle = useMemo(() => titleForPath(pathname), [pathname]);

  useEffect(() => {
    if (!session?.merchantId) {
      return;
    }

    const load = async () => {
      try {
        const notifications = await adapter.getNotifications(session.merchantId as string);
        setUnread(notifications.filter((row) => !row.read).length);
      } catch {
        setUnread(0);
      }
    };

    void load();
  }, [pathname, session?.merchantId]);

  return (
    <ProtectedRoute role="merchant">
      <div className="app-shell-bg min-h-screen pb-16 lg:pb-0">
        <div className="container-paytm flex gap-4 py-3">
          <MerchantSidebar unreadNotifications={unread} onLogout={logout} />

          <section className="min-w-0 flex-1 pb-4">
            <MerchantHeader
              title={pageTitle}
              merchantName={session?.name ?? 'Merchant'}
              unreadCount={unread}
              isDemoMode={isDemoMode}
            />
            {children}

            <ArthsetuErrorBoundary>
              <VoiceBotWidget />
            </ArthsetuErrorBoundary>
          </section>
        </div>
      </div>
    </ProtectedRoute>
  );
}
