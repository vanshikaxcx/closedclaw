'use client';

import { ProtectedRoute } from '@/components/protected-route';
import { ConsumerNav } from '@/src/components/layout/ConsumerNav';

export default function ConsumerLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute role="consumer">
      <div className="min-h-screen bg-[#f4f8fe] pb-8">
        <ConsumerNav />
        <main className="container-paytm py-6">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
