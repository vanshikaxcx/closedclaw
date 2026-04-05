import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string
  subtitle?: string
  delta?: string
  emphasis?: 'default' | 'brand'
  className?: string
}

export function MetricCard({
  title,
  value,
  subtitle,
  delta,
  emphasis = 'default',
  className,
}: MetricCardProps) {
  return (
    <Card className={cn('rounded-2xl border-[#dbe1ec] p-4 sm:p-5', className)}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p
        className={cn(
          'mt-2 text-2xl font-bold leading-tight text-slate-900 sm:text-[1.75rem]',
          emphasis === 'brand' && 'text-[#083f9f]',
        )}
      >
        {value}
      </p>
      {subtitle ? <p className="mt-1 text-xs text-slate-500">{subtitle}</p> : null}
      {delta ? <p className="mt-3 text-xs font-semibold text-emerald-700">{delta}</p> : null}
    </Card>
  )
}
