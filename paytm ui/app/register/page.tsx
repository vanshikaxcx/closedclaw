'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { CheckCircle2, ChevronDown, Shield, Store, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth-context';
import { useToast } from '@/src/context/toast-context';
import { PINPad } from '@/src/components/ui/PINPad';
import { hashPin } from '@/src/lib/pin-utils';
import type { UserRole } from '@/src/adapters/types';

type Step = 1 | 2 | 3 | 4;

const ADMIN_INVITE_CODE = 'ARTHSETU-ADMIN-2026';

export default function RegisterPage() {
  const router = useRouter();
  const { registerAccount, isDemoMode } = useAuth();
  const toast = useToast();

  const [step, setStep] = useState<Step>(1);

  const [mobile, setMobile] = useState('');
  const [fullName, setFullName] = useState('');
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpTimer, setOtpTimer] = useState(30);

  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [pinStage, setPinStage] = useState<'set' | 'confirm'>('set');

  const [role, setRole] = useState<UserRole>('consumer');
  const [adminCode, setAdminCode] = useState('');

  const [gstin, setGstin] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [category, setCategory] = useState('Grocery');
  const [city, setCity] = useState('Gurgaon');
  const [showWhy, setShowWhy] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const showDemoOtpHint = useMemo(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return isDemoMode || window.location.hostname === 'localhost';
  }, [isDemoMode]);

  const validIndianMobile = (value: string) => /^[6-9]\d{9}$/.test(value.trim());
  const validGSTIN = (value: string) => /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$/.test(value.trim().toUpperCase());

  const sendOtp = () => {
    if (!validIndianMobile(mobile) || fullName.trim().length < 2) {
      setError('Enter a valid 10-digit mobile number and full name.');
      return;
    }

    setError(null);
    setOtpSent(true);
    setOtp('');
    setOtpTimer(30);

    const timer = window.setInterval(() => {
      setOtpTimer((current) => {
        if (current <= 1) {
          window.clearInterval(timer);
          return 0;
        }
        return current - 1;
      });
    }, 1000);
  };

  const verifyOtp = () => {
    if (otp !== '123456') {
      setError('Invalid OTP. For demo use 123456.');
      return;
    }
    setError(null);
    setStep(2);
  };

  const proceedPin = () => {
    if (pin.length !== 4) {
      setError('Set a 4-digit PIN.');
      return;
    }
    setError(null);
    setPinStage('confirm');
  };

  const confirmPin = () => {
    if (pinConfirm.length !== 4) {
      setError('Confirm your 4-digit PIN.');
      return;
    }
    if (pin !== pinConfirm) {
      setError('PINs do not match. Try again.');
      setPinConfirm('');
      return;
    }
    setError(null);
    setStep(3);
  };

  const proceedRole = () => {
    if (role === 'admin' && adminCode.trim() !== ADMIN_INVITE_CODE) {
      setError('Invalid admin invite code.');
      return;
    }

    setError(null);
    if (role === 'merchant') {
      setStep(4);
      return;
    }

    void completeRegistration();
  };

  const completeRegistration = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const pinHash = await hashPin(pin);
      const normalizedGstin = gstin.trim().toUpperCase();

      const session = await registerAccount({
        name: fullName.trim(),
        phone: `+91${mobile.trim()}`,
        role,
        pinHash,
        merchantId: role === 'merchant' ? fullName.trim().toLowerCase().replace(/\s+/g, '_') : undefined,
        businessName: role === 'merchant' ? businessName.trim() : undefined,
        gstin: role === 'merchant' ? normalizedGstin : undefined,
        category: role === 'merchant' ? category : undefined,
        city: role === 'merchant' ? city.trim() : undefined,
      });

      toast.success('Registration complete.');

      if (session.role === 'merchant') {
        router.replace('/merchant/dashboard');
        return;
      }
      if (session.role === 'admin') {
        router.replace('/admin/dashboard');
        return;
      }
      router.replace('/home');
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGstinChange = (value: string) => {
    const normalized = value.toUpperCase();
    setGstin(normalized);
    if (normalized === '07AABCU9603R1ZP') {
      setBusinessName('Ramesh General Store');
      setCategory('Grocery');
      setCity('Gurgaon');
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-[#EFF6FF] via-white to-[#EAF4FF] py-8">
      <div className="container-paytm">
        <div className="mx-auto max-w-2xl paytm-surface p-7 sm:p-10">
          <Link href="/" className="inline-flex items-center gap-1 text-3xl font-black tracking-tight">
            <span className="text-[#00BAF2]">pay</span>
            <span className="text-[#002970]">tm</span>
          </Link>

          <div className="mt-6 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[#00BAF2]">
            <span>Step {step}</span>
            <span className="h-px flex-1 bg-[#d6e2f6]" />
            <span>Registration</span>
          </div>

          {step === 1 ? (
            <section className="mt-5 space-y-4">
              <h1 className="text-3xl font-black text-[#002970]">Create your account</h1>
              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Mobile Number</span>
                <Input
                  value={mobile}
                  onChange={(event) => setMobile(event.target.value.replace(/\D/g, '').slice(0, 10))}
                  placeholder="9876543210"
                  className="h-11 rounded-xl border-[#cbd8eb]"
                />
              </label>

              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Full Name</span>
                <Input
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Ramesh Kumar"
                  className="h-11 rounded-xl border-[#cbd8eb]"
                />
              </label>

              {!otpSent ? (
                <Button onClick={sendOtp} className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]">
                  Send OTP
                </Button>
              ) : (
                <>
                  <label className="block text-sm">
                    <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Enter 6-digit OTP</span>
                    <Input
                      value={otp}
                      onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="123456"
                      className="h-11 rounded-xl border-[#cbd8eb]"
                    />
                  </label>
                  {showDemoOtpHint ? <p className="text-xs font-semibold text-[#0a58d8]">Demo: use 123456</p> : null}
                  <div className="flex items-center gap-3">
                    <Button onClick={verifyOtp} className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]">
                      Verify OTP
                    </Button>
                    <button
                      type="button"
                      disabled={otpTimer > 0}
                      onClick={sendOtp}
                      className="text-sm font-semibold text-[#0a58d8] disabled:opacity-50"
                    >
                      {otpTimer > 0 ? `Resend in ${otpTimer}s` : 'Resend OTP'}
                    </button>
                  </div>
                </>
              )}
            </section>
          ) : null}

          {step === 2 ? (
            <section className="mt-5 space-y-4">
              <h1 className="text-3xl font-black text-[#002970]">Set your UPI PIN</h1>
              <p className="text-sm text-slate-600">This PIN protects your payments and sensitive actions.</p>
              <PINPad value={pinStage === 'set' ? pin : pinConfirm} onChange={pinStage === 'set' ? setPin : setPinConfirm} />
              <div className="flex gap-2">
                {pinStage === 'set' ? (
                  <Button onClick={proceedPin} className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]">
                    Continue
                  </Button>
                ) : (
                  <Button onClick={confirmPin} className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]">
                    Confirm PIN
                  </Button>
                )}
              </div>
            </section>
          ) : null}

          {step === 3 ? (
            <section className="mt-5 space-y-4">
              <h1 className="text-3xl font-black text-[#002970]">Choose your account type</h1>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { role: 'consumer', title: 'Consumer', subtitle: 'Pay, recharge, send money.', icon: User },
                  { role: 'merchant', title: 'Merchant', subtitle: 'Manage your business, GST, and finances.', icon: Store },
                  { role: 'admin', title: 'Business Admin', subtitle: 'By invitation only', icon: Shield },
                ].map((card) => {
                  const Icon = card.icon;
                  const selected = role === (card.role as UserRole);

                  return (
                    <button
                      key={card.role}
                      type="button"
                      onClick={() => setRole(card.role as UserRole)}
                      className={`relative rounded-2xl border p-4 text-left transition ${selected ? 'border-[#002970] bg-[#eef5ff]' : 'border-[#d8e0ef] bg-white'}`}
                    >
                      {selected ? <CheckCircle2 className="absolute right-3 top-3 text-[#0a58d8]" size={16} /> : null}
                      <Icon size={18} className="text-[#002970]" />
                      <p className="mt-3 font-bold text-[#002970]">{card.title}</p>
                      <p className="mt-1 text-xs text-slate-600">{card.subtitle}</p>
                    </button>
                  );
                })}
              </div>

              {role === 'admin' ? (
                <label className="block text-sm">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Admin Invite Code</span>
                  <Input
                    value={adminCode}
                    onChange={(event) => setAdminCode(event.target.value)}
                    placeholder="ARTHSETU-ADMIN-2026"
                    className="h-11 rounded-xl border-[#cbd8eb]"
                  />
                </label>
              ) : null}

              <Button onClick={proceedRole} className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]" disabled={isSubmitting}>
                Continue
              </Button>
            </section>
          ) : null}

          {step === 4 ? (
            <section className="mt-5 space-y-4">
              <h1 className="text-3xl font-black text-[#002970]">Tell us about your business</h1>
              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">GSTIN</span>
                <Input
                  value={gstin}
                  onChange={(event) => handleGstinChange(event.target.value)}
                  placeholder="07AABCU9603R1ZP"
                  maxLength={15}
                  className="h-11 rounded-xl border-[#cbd8eb]"
                />
              </label>

              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Business Name</span>
                <Input
                  value={businessName}
                  onChange={(event) => setBusinessName(event.target.value)}
                  placeholder="Ramesh General Store"
                  className="h-11 rounded-xl border-[#cbd8eb]"
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Category</span>
                  <select
                    value={category}
                    onChange={(event) => setCategory(event.target.value)}
                    className="h-11 w-full rounded-xl border border-[#cbd8eb] bg-white px-3"
                  >
                    {['Grocery', 'Electronics', 'Pharmacy', 'Clothing', 'Food & Beverage', 'Telecom', 'Other'].map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">City</span>
                  <Input
                    value={city}
                    onChange={(event) => setCity(event.target.value)}
                    placeholder="Gurgaon"
                    className="h-11 rounded-xl border-[#cbd8eb]"
                  />
                </label>
              </div>

              <div className="rounded-xl border border-[#d8e3f7] bg-[#f4f8ff]">
                <button
                  type="button"
                  onClick={() => setShowWhy((prev) => !prev)}
                  className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-[#002970]"
                >
                  Why do we need this?
                  <ChevronDown size={16} className={showWhy ? 'rotate-180 transition' : 'transition'} />
                </button>
                {showWhy ? (
                  <p className="px-4 pb-4 text-xs text-slate-600">
                    GST details let ArthSetu pre-fill compliance drafts, evaluate trustworthiness from filing behavior, and unlock
                    invoice finance with minimal manual data entry.
                  </p>
                ) : null}
              </div>

              <Button
                onClick={() => {
                  if (!validGSTIN(gstin)) {
                    setError('Enter a valid 15-character GSTIN');
                    return;
                  }
                  if (!businessName.trim() || !city.trim()) {
                    setError('Business name and city are required.');
                    return;
                  }
                  void completeRegistration();
                }}
                disabled={isSubmitting}
                className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]"
              >
                {isSubmitting ? 'Completing...' : 'Complete Registration'}
              </Button>
            </section>
          ) : null}

          {error ? <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{error}</p> : null}

          <div className="mt-6 text-sm text-slate-600">
            Already registered?{' '}
            <Link href="/login" className="font-semibold text-[#0a58d8] hover:text-[#083f9f]">
              Go to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
