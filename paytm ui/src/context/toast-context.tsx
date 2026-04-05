'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, MessageCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type ToastVariant = 'success' | 'error' | 'warning' | 'whatsapp';

type ToastPhase = 'enter' | 'show' | 'exit';

interface ToastItem {
  id: string;
  variant: ToastVariant;
  message: string;
  phone?: string;
  durationMs: number;
  phase: ToastPhase;
}

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  whatsapp: (message: string, phone: string) => void;
}

interface GlobalToastEventDetail {
  variant?: ToastVariant;
  message?: string;
  phone?: string;
}

interface ToastContextValue {
  toast: ToastApi;
}

const MAX_VISIBLE = 4;
const EXIT_MS = 220;

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

function toastStyles(variant: ToastVariant): string {
  if (variant === 'success') {
    return 'border-[#22C55E]/30 bg-white text-slate-900';
  }
  if (variant === 'error') {
    return 'border-[#EF4444]/30 bg-white text-slate-900';
  }
  if (variant === 'warning') {
    return 'border-[#F59E0B]/30 bg-white text-slate-900';
  }
  return 'border-[#22C55E]/30 bg-white text-slate-900';
}

function ToastIcon({ variant }: { variant: ToastVariant }) {
  if (variant === 'success') {
    return <CheckCircle2 size={18} className="text-[#22C55E]" />;
  }
  if (variant === 'error') {
    return <XCircle size={18} className="text-[#EF4444]" />;
  }
  if (variant === 'warning') {
    return <AlertTriangle size={18} className="text-[#F59E0B]" />;
  }
  return <MessageCircle size={18} className="text-[#22C55E]" />;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timeoutMap = useRef<Record<string, number>>({});

  const removeToast = useCallback((id: string) => {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, phase: 'exit' } : item)),
    );

    window.setTimeout(() => {
      setItems((current) => current.filter((item) => item.id !== id));
    }, EXIT_MS);
  }, []);

  const enqueue = useCallback(
    (variant: ToastVariant, message: string, phone?: string, durationMs = 5000) => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      const next: ToastItem = {
        id,
        variant,
        message,
        phone,
        durationMs,
        phase: 'enter',
      };

      setItems((current) => {
        const visible = [...current, next];
        if (visible.length > MAX_VISIBLE) {
          const [oldest, ...rest] = visible;
          if (oldest) {
            window.setTimeout(() => removeToast(oldest.id), 0);
          }
          return rest;
        }
        return visible;
      });

      window.requestAnimationFrame(() => {
        setItems((current) =>
          current.map((item) => (item.id === id ? { ...item, phase: 'show' } : item)),
        );
      });

      timeoutMap.current[id] = window.setTimeout(() => removeToast(id), durationMs);
    },
    [removeToast],
  );

  const toast = useMemo<ToastApi>(
    () => ({
      success: (message: string) => enqueue('success', message),
      error: (message: string) => enqueue('error', message),
      warning: (message: string) => enqueue('warning', message),
      whatsapp: (message: string, phone: string) => enqueue('whatsapp', message, phone, 8000),
    }),
    [enqueue],
  );

  useEffect(() => {
    const onGlobalToast = (event: Event) => {
      const custom = event as CustomEvent<GlobalToastEventDetail>;
      const message = custom.detail?.message;
      if (!message) {
        return;
      }

      const variant = custom.detail?.variant ?? 'error';
      if (variant === 'warning') {
        enqueue('warning', message, custom.detail?.phone);
        return;
      }
      if (variant === 'whatsapp') {
        enqueue('whatsapp', message, custom.detail?.phone, 8000);
        return;
      }
      if (variant === 'success') {
        enqueue('success', message, custom.detail?.phone);
        return;
      }

      enqueue('error', message, custom.detail?.phone);
    };

    window.addEventListener('arthsetu:toast', onGlobalToast);
    return () => {
      window.removeEventListener('arthsetu:toast', onGlobalToast);
    };
  }, [enqueue]);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      <div className="pointer-events-none fixed right-4 top-4 z-[120] flex w-[min(380px,92vw)] flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              'pointer-events-auto rounded-2xl border px-3 py-3 shadow-[0_10px_24px_rgba(2,41,112,0.16)] transition-all duration-200',
              toastStyles(item.variant),
              item.phase === 'show' ? 'translate-x-0 opacity-100' : 'translate-x-8 opacity-0',
            )}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5">
                <ToastIcon variant={item.variant} />
              </div>

              <div className="min-w-0 flex-1">
                {item.variant === 'whatsapp' && item.phone ? (
                  <div className="mb-1 inline-flex items-center gap-1 rounded-full bg-[#22C55E]/15 px-2 py-0.5 text-[11px] font-semibold text-[#166534]">
                    <MessageCircle size={12} />
                    {item.phone}
                  </div>
                ) : null}
                <p className="text-sm font-semibold leading-snug text-slate-800">{item.message}</p>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (timeoutMap.current[item.id]) {
                    window.clearTimeout(timeoutMap.current[item.id]);
                  }
                  removeToast(item.id);
                }}
                className="rounded p-1 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                aria-label="Close toast"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used inside ToastProvider');
  }
  return context.toast;
}
