import { cn } from '@/lib/utils';

type LoadingVariant = 'text' | 'card' | 'metric' | 'table-row' | 'circle';

interface LoadingSkeletonProps {
  variant?: LoadingVariant;
  count?: number;
  className?: string;
}

function SkeletonPulse({ className }: { className?: string }) {
  return <div className={cn('animate-[pulseOpacity_1.2s_ease-in-out_infinite] rounded bg-[#e8edf5]', className)} />;
}

export function LoadingSkeleton({ variant = 'text', count = 1, className }: LoadingSkeletonProps) {
  const rows = Array.from({ length: count });

  if (variant === 'circle') {
    return (
      <div className={cn('flex gap-3', className)}>
        {rows.map((_, index) => (
          <SkeletonPulse key={index} className="h-12 w-12 rounded-full" />
        ))}
      </div>
    );
  }

  if (variant === 'metric') {
    return (
      <div className={cn('grid gap-3', className)}>
        {rows.map((_, index) => (
          <div key={index} className="paytm-surface p-5">
            <SkeletonPulse className="h-3 w-24" />
            <SkeletonPulse className="mt-3 h-9 w-36" />
            <SkeletonPulse className="mt-2 h-3 w-28" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className={cn('grid gap-4', className)}>
        {rows.map((_, index) => (
          <SkeletonPulse key={index} className="h-36 w-full rounded-2xl" />
        ))}
      </div>
    );
  }

  if (variant === 'table-row') {
    return (
      <div className={cn('space-y-2', className)}>
        {rows.map((_, index) => (
          <div key={index} className="grid grid-cols-6 gap-2">
            <SkeletonPulse className="col-span-2 h-8" />
            <SkeletonPulse className="h-8" />
            <SkeletonPulse className="h-8" />
            <SkeletonPulse className="h-8" />
            <SkeletonPulse className="h-8" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {rows.map((_, index) => (
        <SkeletonPulse key={index} className={index % 2 ? 'h-4 w-5/6' : 'h-4 w-full'} />
      ))}
    </div>
  );
}
