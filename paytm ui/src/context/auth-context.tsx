'use client';

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { adapter } from '@/src/adapters';
import type { UserRole, UserSession } from '@/src/adapters/types';
import { createPinVerifiedUntil, hashPin, isPinVerificationValid } from '@/src/lib/pin-utils';

const SESSION_KEY = 'arthsetu_session_v2';
const REGISTRATIONS_KEY = 'arthsetu_registered_accounts_v2';
const HARD_CODED_DEMO_MERCHANT_ID = 'seller_a';

export interface AppSession extends UserSession {
  pinHash: string;
  pinVerifiedUntil?: string;
  isDemoMode: boolean;
}

export interface RegisteredAccount {
  userId: string;
  name: string;
  phone: string;
  role: UserRole;
  merchantId?: string;
  pinHash: string;
  token: string;
  expiresAt: string;
  businessName?: string;
  gstin?: string;
  category?: string;
  city?: string;
}

export interface RegisterInput {
  name: string;
  phone: string;
  role: UserRole;
  pinHash: string;
  merchantId?: string;
  businessName?: string;
  gstin?: string;
  category?: string;
  city?: string;
}

interface AuthContextValue {
  session: AppSession | null;
  user: {
    id: string;
    name: string;
    email: string;
    phone: string;
    role: UserRole;
    merchantId?: string;
    isDemo: boolean;
  } | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  isLoading: boolean;
  isDemoMode: boolean;
  pinVerified: boolean;
  loginWithPin: (merchantId: string, pin: string) => Promise<AppSession>;
  loginWithMerchantPin: (merchantId: string, pin: string) => Promise<AppSession>;
  login: (emailOrPhone: string, password: string) => Promise<void>;
  signup: (email: string, phone: string, name: string, password: string) => Promise<void>;
  startDemoMode: () => Promise<AppSession>;
  registerAccount: (input: RegisterInput) => Promise<AppSession>;
  logout: () => void;
  setPinVerifiedForMinutes: (minutes?: number) => void;
  clearPinVerification: () => void;
  verifyPinForSensitiveAction: (pin: string) => Promise<boolean>;
  getRegisteredAccounts: () => RegisteredAccount[];
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function safeParse<T>(raw: string | null): T | null {
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function generateMerchantId(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '_')
      .slice(0, 18) || `merchant_${Math.random().toString(36).slice(2, 8)}`
  );
}

function getInitialSession(): AppSession | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return safeParse<AppSession>(window.localStorage.getItem(SESSION_KEY));
}

function getStoredRegistrations(): RegisteredAccount[] {
  if (typeof window === 'undefined') {
    return [];
  }
  return safeParse<RegisteredAccount[]>(window.localStorage.getItem(REGISTRATIONS_KEY)) ?? [];
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<AppSession | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    const initial = getInitialSession();
    setSession(initial);
    setIsBootstrapping(false);
  }, []);

  const persistSession = (next: AppSession | null) => {
    setSession(next);
    if (typeof window === 'undefined') {
      return;
    }

    if (next) {
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(next));
    } else {
      window.localStorage.removeItem(SESSION_KEY);
    }
  };

  const upsertRegistration = (account: RegisteredAccount) => {
    const all = getStoredRegistrations();
    const filtered = all.filter((entry) => {
      if (entry.merchantId && account.merchantId) {
        return entry.merchantId !== account.merchantId;
      }
      return entry.userId !== account.userId;
    });

    const next = [account, ...filtered];
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(REGISTRATIONS_KEY, JSON.stringify(next));
    }
  };

  const buildSession = (base: UserSession, pinHashValue: string, demoMode: boolean): AppSession => ({
    ...base,
    pinHash: pinHashValue,
    isDemoMode: demoMode,
    pinVerifiedUntil: createPinVerifiedUntil(15),
  });

  const loginWithPin = async (_merchantId: string, pin: string): Promise<AppSession> => {
    const pinHashValue = await hashPin(pin);

    const auth = await adapter.loginWithPin(HARD_CODED_DEMO_MERCHANT_ID, pinHashValue);
    const nextSession = buildSession(
      {
        ...auth.session,
        merchantId: HARD_CODED_DEMO_MERCHANT_ID,
        role: 'merchant',
      },
      pinHashValue,
      true,
    );
    persistSession(nextSession);
    return nextSession;
  };

  const startDemoMode = async (): Promise<AppSession> => {
    const resetSession = await adapter.resetDemo();
    const pinHashValue = await hashPin('1234');
    const nextSession = buildSession(resetSession, pinHashValue, true);
    persistSession(nextSession);
    router.replace('/merchant/dashboard');
    return nextSession;
  };

  const login = async (emailOrPhone: string, password: string): Promise<void> => {
    await loginWithPin(HARD_CODED_DEMO_MERCHANT_ID, password);
  };

  const signup = async (email: string, phone: string, name: string, password: string): Promise<void> => {
    void email;
    void phone;
    void name;
    void password;
    throw new Error('Demo mode only: registration is disabled');
  };

  const registerAccount = async (input: RegisterInput): Promise<AppSession> => {
    void input;
    throw new Error('Demo mode only: registration is disabled');
  };

  const logout = () => {
    persistSession(null);
    router.push('/login');
  };

  const setPinVerifiedForMinutes = (minutes = 15) => {
    if (!session) {
      return;
    }

    persistSession({
      ...session,
      pinVerifiedUntil: createPinVerifiedUntil(minutes),
    });
  };

  const clearPinVerification = () => {
    if (!session) {
      return;
    }

    persistSession({
      ...session,
      pinVerifiedUntil: undefined,
    });
  };

  const verifyPinForSensitiveAction = async (pin: string): Promise<boolean> => {
    if (!session) {
      return false;
    }

    const pinHashValue = await hashPin(pin);
    const ok = pinHashValue === session.pinHash;
    if (ok) {
      setPinVerifiedForMinutes(15);
    }
    return ok;
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user: session
        ? {
            id: session.userId,
            name: session.name,
            email: `${session.merchantId ?? 'user'}@arthsetu.demo`,
            phone: session.phone,
            role: session.role,
            merchantId: session.merchantId,
            isDemo: session.isDemoMode,
          }
        : null,
      isAuthenticated: !!session,
      isBootstrapping,
      isLoading: isBootstrapping,
      isDemoMode: !!session?.isDemoMode,
      pinVerified: isPinVerificationValid(session?.pinVerifiedUntil),
      loginWithPin,
      loginWithMerchantPin: loginWithPin,
      login,
      signup,
      startDemoMode,
      registerAccount,
      logout,
      setPinVerifiedForMinutes,
      clearPinVerification,
      verifyPinForSensitiveAction,
      getRegisteredAccounts: () => [],
    }),
    [isBootstrapping, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
