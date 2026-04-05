import { cn } from '@/lib/utils'

interface LoadingSkeletonProps {
  lines?: number
  className?: string
}

export function LoadingSkeleton({ lines = 4, className }: LoadingSkeletonProps) {
  return (
    <div className={cn('space-y-3 rounded-2xl border border-[#dbe1ec] bg-white p-5', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={cn(
            'h-4 animate-pulse rounded bg-[#e7ecf5]',
            index % 4 === 0 ? 'w-11/12' : index % 3 === 0 ? 'w-2/3' : 'w-full',
          )}
        />
      ))}
    </div>
  )
}
