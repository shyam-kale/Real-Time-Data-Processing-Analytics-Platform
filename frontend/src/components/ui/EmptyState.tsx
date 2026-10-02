import type { ReactNode } from 'react'
import { Button } from './Button'

export function EmptyState({
  icon,
  title,
  description,
  action,
  actionLabel,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: () => void
  actionLabel?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {icon && <div className="mb-4 text-muted-foreground/40">{icon}</div>}
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground max-w-sm">{description}</p>}
      {action && actionLabel && (
        <Button className="mt-5" size="sm" onClick={action}>{actionLabel}</Button>
      )}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-sm text-destructive font-medium">{message ?? 'Something went wrong'}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>Try again</Button>
      )}
    </div>
  )
}
