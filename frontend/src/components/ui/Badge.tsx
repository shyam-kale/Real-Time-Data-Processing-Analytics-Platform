import { cn } from '@/utils/cn'
import type { ReactNode } from 'react'

type Variant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'outline' | 'ghost'

const variants: Record<Variant, string> = {
  default:  'bg-secondary text-secondary-foreground',
  success:  'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/25 dark:text-emerald-400',
  warning:  'bg-amber-50  text-amber-700  dark:bg-amber-900/25  dark:text-amber-400',
  error:    'bg-red-50    text-red-700    dark:bg-red-900/25    dark:text-red-400',
  info:     'bg-blue-50   text-blue-700   dark:bg-blue-900/25   dark:text-blue-400',
  outline:  'border border-border text-foreground bg-transparent',
  ghost:    'text-muted-foreground bg-transparent',
}

export function Badge({
  variant = 'default',
  className,
  children,
  dot,
}: {
  variant?: Variant
  className?: string
  children: ReactNode
  dot?: boolean
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium',
        variants[variant],
        className
      )}
    >
      {dot && (
        <span
          className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', {
            'bg-emerald-500': variant === 'success',
            'bg-amber-500':   variant === 'warning',
            'bg-red-500':     variant === 'error',
            'bg-blue-500':    variant === 'info',
            'bg-foreground':  variant === 'default',
          })}
        />
      )}
      {children}
    </span>
  )
}

// Convenience wrappers for run/dataset statuses
export function RunStatusBadge({ status }: { status: string }) {
  const map: Record<string, Variant> = {
    success: 'success', warning: 'warning', failed: 'error',
    running: 'info', pending: 'ghost', cancelled: 'outline',
  }
  return <Badge variant={map[status] ?? 'default'} dot>{status}</Badge>
}

export function DatasetStatusBadge({ status }: { status: string }) {
  const map: Record<string, Variant> = {
    ready: 'success', processing: 'info', pending: 'ghost', error: 'error',
  }
  return <Badge variant={map[status] ?? 'default'}>{status}</Badge>
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, Variant> = {
    critical: 'error', error: 'error', warning: 'warning', info: 'info',
  }
  return <Badge variant={map[severity] ?? 'default'}>{severity}</Badge>
}
