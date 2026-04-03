'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth-context';
import { useToast } from '@/src/context/toast-context';
import { PINPad } from '@/src/components/ui/PINPad';

const LOADING_MESSAGES = [
  'Connecting to ArthSetu...',
  "Loading Ramesh's store data...",
  'Seeding 180 days of transaction history...',
  'Ready.',
];

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#EFF6FF] px-4 py-10">
          <div className="container-paytm">
            <div className="paytm-surface p-8 text-sm text-slate-500">Loading sign in...</div>
          </div>
        </div>
      }
    >
      <LoginScreen />
    </Suspense>
  );
}

function LoginScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loginWithMerchantPin, startDemoMode, session } = useAuth();
  const toast = useToast();

  const merchantId = 'seller_a';
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoMessage, setDemoMessage] = useState(LOADING_MESSAGES[0]);

  const demoTriggerRef = useRef(false);

  const nextRoute = useMemo(() => {
    const next = searchParams.get('next');
    if (next && next.startsWith('/')) {
      return next;
    }
    return '/merchant/dashboard';
  }, [searchParams]);

  useEffect(() => {
    if (!session) {
      return;
    }
    router.replace(nextRoute || (session.role === 'admin' ? '/admin/dashboard' : '/merchant/dashboard'));
  }, [nextRoute, router, session]);

  const runDemoBootSequence = async () => {
    setError(null);
    setIsSubmitting(true);
    setDemoProgress(0);
    setDemoMessage(LOADING_MESSAGES[0]);

    const started = Date.now();
    const timer = window.setInterval(() => {
      const elapsed = Date.now() - started;
      const ratio = Math.min(1, elapsed / 2000);
      setDemoProgress(Math.round(ratio * 100));
      const messageIndex = Math.min(LOADING_MESSAGES.length - 1, Math.floor(ratio * LOADING_MESSAGES.length));
      setDemoMessage(LOADING_MESSAGES[messageIndex]);
    }, 120);

    try {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await startDemoMode();
      toast.success('Demo ready. Welcome to Ramesh General Store.');
      router.replace('/merchant/dashboard?tour=demo');
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to initialize demo mode');
    } finally {
      window.clearInterval(timer);
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (searchParams.get('demo') !== 'true' || demoTriggerRef.current || session) {
      return;
    }

    demoTriggerRef.current = true;
    void runDemoBootSequence();
  }, [searchParams, session]);

  const handleLogin = async () => {
    setError(null);

    if (pin.length !== 4) {
      setError('Please enter a 4-digit PIN');
      return;
    }

    setIsSubmitting(true);
    try {
      const authSession = await loginWithMerchantPin(merchantId.trim(), pin);
      toast.success(`Signed in as ${authSession.name}`);
      router.replace(nextRoute || (authSession.role === 'admin' ? '/admin/dashboard' : '/merchant/dashboard'));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to login');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-[#EFF6FF] via-white to-[#EAF4FF] py-8">
      <div className="container-paytm grid gap-7 lg:grid-cols-[1fr_0.95fr]">
        <section className="paytm-surface p-7 sm:p-10">
          <Link href="/" className="inline-flex items-center gap-1 text-3xl font-black tracking-tight">
            <span className="text-[#00BAF2]">pay</span>
            <span className="text-[#002970]">tm</span>
          </Link>

          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-[#00BAF2]">Merchant Access</p>
          <h1 className="mt-3 text-3xl font-black text-[#002970] sm:text-4xl">Login with Merchant ID and UPI PIN</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Access GST filing, TrustScore, invoices, wallet operations, and admin monitoring flows.
          </p>

          <div className="mt-7 space-y-4">
            <label className="block text-sm">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Merchant ID</span>
              <Input
                value={merchantId}
                readOnly
                placeholder="seller_a"
                className="h-11 rounded-xl border-[#cbd8eb] bg-white"
              />
            </label>

            <div>
              <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">UPI PIN</span>
              <PINPad value={pin} onChange={setPin} disabled={isSubmitting} />
            </div>

            {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{error}</p> : null}

            <Button
              type="button"
              onClick={() => void handleLogin()}
              disabled={isSubmitting}
              className="h-11 w-full rounded-full bg-[#002970] text-white hover:bg-[#0a3f9d]"
            >
              Login
            </Button>

            <div className="relative py-2 text-center text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              <span className="bg-white px-2">or</span>
              <div className="absolute inset-x-0 top-1/2 -z-10 h-px bg-[#d7e0ee]" />
            </div>

            <Button
              type="button"
              variant="outline"
              onClick={() => void runDemoBootSequence()}
              disabled={isSubmitting}
              className="h-11 w-full rounded-full border-[#002970] text-[#002970] hover:bg-[#edf5ff]"
            >
              Try Demo as Ramesh (Merchant)
            </Button>

            {isSubmitting ? (
              <div className="rounded-xl border border-[#d9e5f8] bg-[#f5f9ff] p-3">
                <p className="text-xs font-semibold text-[#002970]">{demoMessage}</p>
                <div className="mt-2 h-2 rounded-full bg-[#d7e4fb]">
                  <div className="h-2 rounded-full bg-[#00BAF2] transition-all" style={{ width: `${demoProgress}%` }} />
                </div>
              </div>
            ) : null}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
            <Link href="/forgot-pin" className="text-sm font-semibold text-[#0a58d8] hover:text-[#083f9f]">
              Forgot PIN?
            </Link>
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Demo merchant mode active</p>
          </div>
        </section>

        <section className="rounded-3xl bg-[#002970] p-7 text-white sm:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">Judge Flow</p>
          <h2 className="mt-3 text-2xl font-black sm:text-3xl">Demo storyline in under 5 minutes</h2>
          <ol className="mt-6 space-y-3 text-sm text-white/90">
            <li>1. Open /login?demo=true for one-click auto setup.</li>
            <li>2. Review 847 GST transactions with 3 flagged records.</li>
            <li>3. File GST and watch TrustScore move from 74 to 78.</li>
            <li>4. Accept invoice offer for INV-044 and inspect disbursal toast.</li>
            <li>5. Verify entire chain in merchant audit trail.</li>
          </ol>

          <div className="mt-7 rounded-2xl bg-white/10 p-4 text-sm">
            <p className="font-semibold">Credentials</p>
            <p className="mt-1 text-white/85">Merchant: seller_a / 1234</p>
          </div>

          <Link href="/merchant/dashboard" className="mt-6 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-bold text-[#002970]">
            Open Merchant Dashboard
            <ArrowRight size={16} />
          </Link>
        </section>
      </div>
    </div>
  );
}
