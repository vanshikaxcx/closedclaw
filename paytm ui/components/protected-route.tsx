'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import type { UserRole } from '@/src/adapters/types';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { usePINGate } from '@/src/context/pin-context';

interface ProtectedRouteProps {
  children: React.ReactNode;
  role?: UserRole;
  pinSensitive?: boolean;
  pinMessage?: string;
}

export function ProtectedRoute({ children, role, pinSensitive = false, pinMessage }: ProtectedRouteProps) {
  const { session, isAuthenticated, isBootstrapping, pinVerified } = useAuth();
  const { requirePIN } = usePINGate();
  const router = useRouter();
  const pathname = usePathname();
  const [pinPrompted, setPinPrompted] = useState(false);

  useEffect(() => {
    if (!isBootstrapping && !isAuthenticated) {
      const nextTarget = pathname || '/';
      router.replace(`/login?next=${encodeURIComponent(nextTarget)}`);
      return;
    }

    if (!isBootstrapping && role && session && session.role !== role) {
      router.replace('/unauthorized');
    }
  }, [isAuthenticated, isBootstrapping, pathname, role, router, session]);

  useEffect(() => {
    if (!isAuthenticated || isBootstrapping || !pinSensitive || pinVerified) {
      setPinPrompted(false);
      return;
    }

    if (pinPrompted) {
      return;
    }

    setPinPrompted(true);
    requirePIN({
      message: pinMessage ?? 'Confirm with your UPI PIN',
      actionLabel: 'Verify PIN',
      onSuccess: () => {
        setPinPrompted(false);
      },
    });
  }, [isAuthenticated, isBootstrapping, pinMessage, pinPrompted, pinSensitive, pinVerified, requirePIN]);

  if (isBootstrapping) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12">
        <LoadingSkeleton lines={9} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (role && session?.role !== role) {
    return null;
  }

  if (pinSensitive && !pinVerified) {
    return (
      <div className="relative">
        <div className="pointer-events-none select-none opacity-40">{children}</div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="rounded-2xl border border-[#d8e0ef] bg-white/95 px-5 py-4 text-center shadow-sm backdrop-blur-sm">
            <p className="text-sm font-semibold text-[#002970]">PIN verification required</p>
            <p className="mt-1 text-xs text-slate-600">Complete PIN challenge to continue this action.</p>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
