import { cn } from '@/utils/cn'
import type { ReactNode, HTMLAttributes } from 'react'

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('bg-card border border-border rounded-lg', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn('flex items-center justify-between px-5 py-4 border-b border-border', className)}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children }: { className?: string; children: ReactNode }) {
  return <h3 className={cn('text-sm font-semibold text-foreground', className)}>{children}</h3>
}

export function CardContent({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('px-5 py-4', className)}>{children}</div>
}

export function StatCard({
  label,
  value,
  sub,
  trend,
  className,
}: {
  label: string
  value: string | number
  sub?: string
  trend?: string
  className?: string
}) {
  const positive = trend?.startsWith('+')
  return (
    <Card className={cn('p-5', className)}>
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular text-foreground">{value}</p>
      {(sub || trend) && (
        <p className="mt-1 text-xs text-muted-foreground flex items-center gap-1.5">
          {trend && (
            <span className={positive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500'}>
              {trend}
            </span>
          )}
          {sub}
        </p>
      )}
    </Card>
  )
}
