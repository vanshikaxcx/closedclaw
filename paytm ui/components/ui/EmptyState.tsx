import { cn } from '@/lib/utils'

interface EmptyStateProps {
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-dashed border-[#c7d3e7] bg-white p-8 text-center',
        className,
      )}
    >
      <p className="text-lg font-bold text-slate-900">{title}</p>
      {description ? <p className="mt-2 text-sm text-slate-600">{description}</p> : null}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </div>
  )
}
