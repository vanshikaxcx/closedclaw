import { cn } from '@/lib/utils'

interface CommonHeaderProps {
  title: string
  subtitle?: string
  icon?: string
  children?: React.ReactNode
  className?: string
}

export function CommonHeader({
  title,
  subtitle,
  icon,
  children,
  className,
}: CommonHeaderProps) {
  return (
    <section className={cn('paytm-surface p-5 sm:p-6', className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{icon ? `${icon} Module` : 'Module'}</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900 sm:text-3xl">{title}</h1>
          {subtitle ? <p className="mt-2 text-sm text-slate-600">{subtitle}</p> : null}
        </div>
        {children ? <div>{children}</div> : null}
      </div>
    </section>
  )
}
