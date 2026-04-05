'use client';

import { X } from 'lucide-react';
import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  closeOnBackdrop?: boolean;
  variant?: 'default' | 'pin';
}

const sizeMap = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
} as const;

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  closeOnBackdrop = true,
  variant = 'default',
}: ModalProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, open]);

  if (!open || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div className="absolute inset-0 z-[140] min-h-screen">
      <div
        className="absolute inset-0 bg-slate-900/45"
        onClick={closeOnBackdrop ? onClose : undefined}
        role="presentation"
      />

      <div className="relative flex min-h-screen items-center justify-center px-4 py-10">
        <section
          role="dialog"
          aria-modal="true"
          aria-label={title}
          className={cn(
            'w-full rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-[0_22px_50px_rgba(2,41,112,0.22)]',
            sizeMap[size],
            variant === 'pin' && 'border-[#cdd7ec]',
          )}
        >
          <header className="mb-5 flex items-start justify-between gap-4">
            <h2 className="text-xl font-black text-[#002970]">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
              aria-label="Close modal"
            >
              <X size={16} />
            </button>
          </header>

          <div>{children}</div>
          {footer ? <footer className="mt-6">{footer}</footer> : null}
        </section>
      </div>
    </div>,
    document.body,
  );
}
