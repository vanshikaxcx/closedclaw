'use client';

import { useEffect, useMemo, useState } from 'react';
import { Delete } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/src/context/auth-context';
import { Modal } from '@/src/components/ui/Modal';

interface PINModalProps {
  open: boolean;
  onSuccess: () => void;
  onCancel: () => void;
  message?: string;
  actionLabel?: string;
}

const KEYPAD = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'backspace'];

export function PINModal({
  open,
  onSuccess,
  onCancel,
  message = 'Enter your UPI PIN to continue',
  actionLabel = 'Confirm',
}: PINModalProps) {
  const { verifyPinForSensitiveAction } = useAuth();

  const [pin, setPin] = useState('');
  const [attemptsLeft, setAttemptsLeft] = useState(3);
  const [lockUntil, setLockUntil] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isShaking, setIsShaking] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const isLocked = useMemo(() => {
    if (!lockUntil) {
      return false;
    }
    return lockUntil > Date.now();
  }, [lockUntil]);

  useEffect(() => {
    if (!open) {
      setPin('');
      setError(null);
      return;
    }

    if (!lockUntil) {
      return;
    }

    const timer = window.setInterval(() => {
      const remaining = Math.max(0, Math.ceil((lockUntil - Date.now()) / 1000));
      setCountdown(remaining);
      if (remaining <= 0) {
        setLockUntil(null);
        setAttemptsLeft(3);
        setError(null);
      }
    }, 250);

    return () => window.clearInterval(timer);
  }, [lockUntil, open]);

  useEffect(() => {
    if (pin.length === 4 && !isVerifying && !isLocked) {
      void handleVerify();
    }
  }, [isLocked, isVerifying, pin]);

  const handleVerify = async () => {
    if (isLocked || pin.length !== 4) {
      return;
    }

    setIsVerifying(true);
    const ok = await verifyPinForSensitiveAction(pin);

    if (ok) {
      setPin('');
      setError(null);
      setAttemptsLeft(3);
      onSuccess();
      setIsVerifying(false);
      return;
    }

    const remaining = attemptsLeft - 1;
    setAttemptsLeft(remaining);
    setIsShaking(true);
    window.setTimeout(() => setIsShaking(false), 260);

    if (remaining <= 0) {
      const until = Date.now() + 30 * 1000;
      setLockUntil(until);
      setCountdown(30);
      setError('Incorrect PIN. Locked for 30 seconds.');
    } else {
      setError(`Incorrect PIN. ${remaining} attempts remaining`);
    }

    setPin('');
    setIsVerifying(false);
  };

  const pressKey = (key: string) => {
    if (isLocked || isVerifying) {
      return;
    }

    if (key === 'backspace') {
      setPin((current) => current.slice(0, -1));
      return;
    }

    if (!key) {
      return;
    }

    if (pin.length < 4) {
      setPin((current) => `${current}${key}`);
    }
  };

  return (
    <Modal open={open} onClose={onCancel} title="Confirm with your UPI PIN" variant="pin" size="sm" closeOnBackdrop={false}>
      <p className="text-sm text-slate-600">{message}</p>

      <div className="mt-5">
        <div className={`mx-auto flex max-w-[220px] justify-between ${isShaking ? 'animate-[pinShake_240ms_ease-in-out]' : ''}`}>
          {Array.from({ length: 4 }).map((_, index) => {
            const filled = index < pin.length;
            return (
              <span
                key={index}
                className={`h-4 w-4 rounded-full border-2 ${filled ? 'border-[#002970] bg-[#002970]' : 'border-slate-300 bg-white'}`}
              />
            );
          })}
        </div>
      </div>

      {error ? <p className="mt-3 text-center text-xs font-semibold text-[#EF4444]">{error}</p> : null}
      {isLocked ? <p className="mt-2 text-center text-xs text-[#F59E0B]">Try again in {countdown}s</p> : null}

      <div className="mt-5 grid grid-cols-3 gap-2">
        {KEYPAD.map((key, index) => (
          <button
            key={`${key}-${index}`}
            type="button"
            onClick={() => pressKey(key)}
            className="h-11 rounded-xl border border-[#d6deef] bg-white text-base font-semibold text-[#002970] transition hover:bg-[#f4f8ff] disabled:opacity-60"
            disabled={isLocked || isVerifying || key === ''}
          >
            {key === 'backspace' ? <Delete size={18} className="mx-auto" /> : key}
          </button>
        ))}
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel} className="rounded-full">
          Cancel
        </Button>
        <Button onClick={() => void handleVerify()} disabled={pin.length !== 4 || isLocked || isVerifying} className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]">
          {actionLabel}
        </Button>
      </div>
    </Modal>
  );
}
