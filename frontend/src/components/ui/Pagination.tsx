import { Button } from './Button'
import { ChevronLeft, ChevronRight } from 'lucide-react'

export function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onChange,
}: {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onChange: (p: number) => void
}) {
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <div className="flex items-center justify-between px-1 py-3 text-sm text-muted-foreground">
      <span>{total > 0 ? `${from}–${to} of ${total.toLocaleString()}` : '0 results'}</span>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="xs"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          icon={<ChevronLeft className="w-3.5 h-3.5" />}
        />
        <span className="px-2 text-xs tabular">
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="xs"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          icon={<ChevronRight className="w-3.5 h-3.5" />}
        />
      </div>
    </div>
  )
}
