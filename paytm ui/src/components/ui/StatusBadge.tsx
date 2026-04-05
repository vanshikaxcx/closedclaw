import { cn } from '@/lib/utils';

export type BadgeStatus =
  | 'PAID'
  | 'PENDING'
  | 'OVERDUE'
  | 'FINANCED'
  | 'FILED'
  | 'ACTIVE'
  | 'INACTIVE'
  | 'FLAGGED'
  | 'NEEDS_REVIEW'
  | 'VERIFIED'
  | 'REJECTED';

interface StatusBadgeProps {
  status: BadgeStatus;
  size?: 'sm' | 'md';
  className?: string;
}

const statusMap: Record<BadgeStatus, string> = {
  PAID: 'bg-[#22C55E]/15 text-[#166534]',
  PENDING: 'bg-[#3B82F6]/15 text-[#1d4ed8]',
  OVERDUE: 'bg-[#EF4444]/15 text-[#b91c1c]',
  FINANCED: 'bg-violet-100 text-violet-700',
  FILED: 'bg-[#22C55E]/15 text-[#166534]',
  ACTIVE: 'bg-[#22C55E]/15 text-[#166534]',
  INACTIVE: 'bg-slate-100 text-slate-600',
  FLAGGED: 'bg-[#F59E0B]/15 text-[#a16207]',
  NEEDS_REVIEW: 'bg-[#F59E0B]/15 text-[#a16207]',
  VERIFIED: 'bg-[#22C55E]/15 text-[#166534]',
  REJECTED: 'bg-[#EF4444]/15 text-[#b91c1c]',
};

const sizeMap = {
  sm: 'px-2.5 py-1 text-[12px]',
  md: 'px-3.5 py-1.5 text-[14px]',
} as const;

export function StatusBadge({ status, size = 'sm', className }: StatusBadgeProps) {
  const label = status === 'NEEDS_REVIEW' ? 'Needs Review' : status;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-bold uppercase tracking-wide',
        statusMap[status],
        sizeMap[size],
        className,
      )}
    >
      {label}
    </span>
  );
}
