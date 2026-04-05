import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  prefix?: string;
  suffix?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  sublabel?: string;
  onClick?: () => void;
  className?: string;
}

export function MetricCard({
  label,
  value,
  prefix,
  suffix,
  trend,
  trendValue,
  sublabel,
  onClick,
  className,
}: MetricCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'paytm-surface w-full p-6 text-left',
        onClick ? 'transition hover:bg-[#f8fbff]' : 'cursor-default',
        className,
      )}
      disabled={!onClick}
    >
      <p className="text-[13px] font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="mt-3 text-[28px] font-black leading-none text-[#002970]">
        {prefix}
        {value}
        {suffix}
      </p>

      {trend ? (
        <div
          className={cn(
            'mt-3 inline-flex items-center gap-1 text-xs font-semibold',
            trend === 'up' && 'text-[#22C55E]',
            trend === 'down' && 'text-[#EF4444]',
            trend === 'neutral' && 'text-slate-500',
          )}
        >
          {trend === 'up' ? <ArrowUpRight size={14} /> : null}
          {trend === 'down' ? <ArrowDownRight size={14} /> : null}
          {trend === 'neutral' ? <Minus size={14} /> : null}
          <span>{trendValue ?? 'No change'}</span>
        </div>
      ) : null}

      {sublabel ? <p className="mt-2 text-sm text-slate-600">{sublabel}</p> : null}
    </button>
  );
}
