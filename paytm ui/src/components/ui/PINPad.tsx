'use client';

import { Delete } from 'lucide-react';

interface PINPadProps {
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
  length?: number;
}

const KEYPAD = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'backspace'];

export function PINPad({ value, onChange, disabled = false, length = 4 }: PINPadProps) {
  const press = (key: string) => {
    if (disabled) {
      return;
    }
    if (!key) {
      return;
    }
    if (key === 'backspace') {
      onChange(value.slice(0, -1));
      return;
    }
    if (value.length < length) {
      onChange(`${value}${key}`);
    }
  };

  return (
    <div>
      <div className="mx-auto flex max-w-[220px] justify-between">
        {Array.from({ length }).map((_, index) => {
          const filled = index < value.length;
          return (
            <span
              key={index}
              className={`h-4 w-4 rounded-full border-2 ${filled ? 'border-[#002970] bg-[#002970]' : 'border-slate-300 bg-white'}`}
            />
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        {KEYPAD.map((key, index) => (
          <button
            key={`${key}-${index}`}
            type="button"
            onClick={() => press(key)}
            disabled={disabled || key === ''}
            className="h-11 rounded-xl border border-[#d6deef] bg-white text-base font-semibold text-[#002970] transition hover:bg-[#f4f8ff] disabled:opacity-50"
          >
            {key === 'backspace' ? <Delete size={18} className="mx-auto" /> : key}
          </button>
        ))}
      </div>
    </div>
  );
}
