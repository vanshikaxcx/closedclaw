'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PINPad } from '@/src/components/ui/PINPad';

type Stage = 'mobile' | 'otp' | 'pin' | 'confirm' | 'success';

export default function ForgotPinPage() {
  const [stage, setStage] = useState<Stage>('mobile');
  const [mobile, setMobile] = useState('');
  const [otp, setOtp] = useState('');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-linear-to-br from-[#EFF6FF] via-white to-[#EAF4FF] py-8">
      <div className="container-paytm">
        <div className="mx-auto max-w-xl paytm-surface p-7 sm:p-9">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#00BAF2]">Account Recovery</p>
          <h1 className="mt-3 text-3xl font-black text-[#002970]">Reset UPI PIN</h1>

          {stage === 'mobile' ? (
            <div className="mt-6 space-y-4">
              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Mobile Number</span>
                <Input
                  value={mobile}
                  onChange={(event) => setMobile(event.target.value.replace(/\D/g, '').slice(0, 10))}
                  placeholder="9876543210"
                  className="h-11 rounded-xl border-[#cbd8eb]"
                />
              </label>
              <Button
                onClick={() => {
                  if (!/^[6-9]\d{9}$/.test(mobile)) {
                    setError('Enter a valid Indian mobile number.');
                    return;
                  }
                  setError(null);
                  setStage('otp');
                }}
                className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]"
              >
                Send OTP
              </Button>
            </div>
          ) : null}

          {stage === 'otp' ? (
            <div className="mt-6 space-y-4">
              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Enter OTP</span>
                <Input
                  value={otp}
                  onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                  className="h-11 rounded-xl border-[#cbd8eb]"
                />
              </label>
              <p className="text-xs font-semibold text-[#0a58d8]">Demo OTP: 123456</p>
              <Button
                onClick={() => {
                  if (otp !== '123456') {
                    setError('Invalid OTP. Please use 123456 in demo mode.');
                    return;
                  }
                  setError(null);
                  setStage('pin');
                }}
                className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]"
              >
                Verify OTP
              </Button>
            </div>
          ) : null}

          {stage === 'pin' ? (
            <div className="mt-6 space-y-4">
              <p className="text-sm text-slate-600">Set your new 4-digit PIN.</p>
              <PINPad value={pin} onChange={setPin} />
              <Button
                onClick={() => {
                  if (pin.length !== 4) {
                    setError('PIN must be 4 digits.');
                    return;
                  }
                  setError(null);
                  setStage('confirm');
                }}
                className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]"
              >
                Continue
              </Button>
            </div>
          ) : null}

          {stage === 'confirm' ? (
            <div className="mt-6 space-y-4">
              <p className="text-sm text-slate-600">Confirm your new PIN.</p>
              <PINPad value={confirmPin} onChange={setConfirmPin} />
              <Button
                onClick={() => {
                  if (confirmPin !== pin) {
                    setError('PINs do not match.');
                    setConfirmPin('');
                    return;
                  }
                  setError(null);
                  setStage('success');
                }}
                className="h-11 rounded-full bg-[#002970] px-6 hover:bg-[#0a3f9d]"
              >
                Save New PIN
              </Button>
            </div>
          ) : null}

          {stage === 'success' ? (
            <div className="mt-6 rounded-2xl border border-[#d8e3f7] bg-[#f4f8ff] p-5">
              <p className="text-sm font-semibold text-[#002970]">PIN reset successful.</p>
              <p className="mt-1 text-sm text-slate-600">You can now sign in using your new PIN.</p>
              <Link href="/login" className="mt-4 inline-flex rounded-full bg-[#002970] px-4 py-2 text-sm font-semibold text-white">
                Go to Login
              </Link>
            </div>
          ) : null}

          {error ? <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{error}</p> : null}

          <Link href="/login" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[#0a58d8] hover:text-[#083f9f]">
            <ArrowLeft size={16} />
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
