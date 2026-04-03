'use client';

import { useMemo } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Line } from 'recharts';
import { Button } from '@/components/ui/button';
import type { CashflowProjection, DailyRevenue } from '@/src/adapters/types';
import { formatINRCompactLakh } from '@/src/lib/format';

type WindowSize = 30 | 60 | 90;

interface CashflowChartProps {
  history: DailyRevenue[];
  projection: CashflowProjection;
  windowDays: WindowSize;
  onWindowChange: (window: WindowSize) => void;
  stockAlertMessage?: string;
  onDismissAlert?: () => void;
}

export function CashflowChart({
  history,
  projection,
  windowDays,
  onWindowChange,
  stockAlertMessage,
  onDismissAlert,
}: CashflowChartProps) {
  const chartData = useMemo(() => {
    const base = history.slice(-windowDays).map((row) => ({
      ...row,
      historical: row.amount,
      projected: null as number | null,
      projectionStart: null as number | null,
      projectionEnd: null as number | null,
    }));

    const last = base[base.length - 1]?.amount ?? 0;
    const target =
      windowDays === 30 ? projection.p30.amount / 30 : windowDays === 60 ? projection.p60.amount / 60 : projection.p90.amount / 90;

    const projectedCount = Math.max(8, Math.floor(windowDays / 6));

    const projected = Array.from({ length: projectedCount }).map((_, index) => {
      const factor = 1 + (index + 1) / (projectedCount * 15);
      const value = Math.round((target + last) / 2 * factor);
      const lower = value * 0.9;
      const upper = value * 1.1;

      return {
        date: `P${index + 1}`,
        amount: value,
        transactionCount: 0,
        isProjected: true,
        lowerBound: lower,
        upperBound: upper,
        historical: null as number | null,
        projected: value,
        projectionStart: lower,
        projectionEnd: upper,
      };
    });

    return [...base, ...projected];
  }, [history, projection, windowDays]);

  return (
    <article className="paytm-surface p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-lg font-black text-[#002970]">Cashflow Trend</h3>
        <div className="inline-flex rounded-full border border-[#d1daea] p-1">
          {[30, 60, 90].map((window) => (
            <button
              key={window}
              type="button"
              className={`rounded-full px-3 py-1 text-xs font-bold ${windowDays === window ? 'bg-[#002970] text-white' : 'text-slate-600'}`}
              onClick={() => onWindowChange(window as WindowSize)}
            >
              {window}D
            </button>
          ))}
        </div>
      </div>

      {stockAlertMessage ? (
        <div className="mb-4 flex items-center justify-between rounded-xl border border-[#F59E0B]/30 bg-[#F59E0B]/10 px-3 py-2 text-sm text-[#8a5a02]">
          <p>{stockAlertMessage}</p>
          {onDismissAlert ? (
            <Button size="sm" variant="outline" onClick={onDismissAlert}>
              Dismiss
            </Button>
          ) : null}
        </div>
      ) : null}

      <div className="h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ left: 8, right: 8, top: 16, bottom: 6 }}>
            <CartesianGrid strokeDasharray="4 4" stroke="#e5edf8" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(value) => formatINRCompactLakh(Number(value))} width={78} />
            <Tooltip formatter={(value: number) => formatINRCompactLakh(value)} labelStyle={{ color: '#0f172a' }} />

            <Area type="monotone" dataKey="projectionEnd" stroke="none" fill="#dbeafe" fillOpacity={0.4} />
            <Area type="monotone" dataKey="projectionStart" stroke="none" fill="#ffffff" fillOpacity={1} />

            <Area type="monotone" dataKey="historical" stroke="#00BAF2" fill="#00BAF2" fillOpacity={0.22} strokeWidth={2} />
            <Line type="monotone" dataKey="projected" stroke="#002970" strokeDasharray="6 5" dot={false} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}
