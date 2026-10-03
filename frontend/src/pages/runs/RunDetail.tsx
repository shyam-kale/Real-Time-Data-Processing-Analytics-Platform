import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { runsApi } from '@/services/pipelines'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { RunStatusBadge } from '@/components/ui/Badge'
import { InlineLoader } from '@/components/ui/Spinner'
import { ErrorState } from '@/components/ui/EmptyState'
import { formatNumber, formatDuration, formatDateTime } from '@/utils/format'
import { ArrowLeft } from 'lucide-react'
import type { LogEntry } from '@/types'

const WS_BASE = (() => {
  if (import.meta.env.VITE_WS_BASE_URL) return import.meta.env.VITE_WS_BASE_URL as string
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
})()

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const orgId = useOrg()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)

  const { data: run, isLoading, error, refetch } = useQuery({
    queryKey: ['run', orgId, id],
    queryFn: () => runsApi.get(orgId, id!),
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'running' || status === 'pending' ? 3000 : false
    },
  })

  // WebSocket for live updates
  useEffect(() => {
    if (!id) return
    const ws = new WebSocket(`${WS_BASE}/ws/pipeline_run:${id}`)
    wsRef.current = ws
    ws.onmessage = () => qc.invalidateQueries({ queryKey: ['run', orgId, id] })
    ws.onopen = () => {
      const ping = setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000)
      ws.onclose = () => clearInterval(ping)
    }
    return () => ws.close()
  }, [id, orgId, qc])

  if (isLoading) return <InlineLoader />
  if (error || !run) return <ErrorState message="Run not found" onRetry={refetch} />

  const isLive = run.status === 'running' || run.status === 'pending'

  return (
    <div>
      <PageHeader
        title={`Run ${run.id.slice(0, 8)}…`}
        subtitle={`Pipeline run · ${formatDateTime(run.created_at)}`}
        actions={
          <div className="flex items-center gap-2">
            {isLive && <span className="flex items-center gap-1.5 text-xs text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />Live</span>}
            <RunStatusBadge status={run.status} />
            <Button variant="outline" size="sm" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={() => navigate('/runs')}>Back</Button>
          </div>
        }
      />

      <div className="p-6 space-y-4">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Input records"  value={formatNumber(run.input_records)} />
          <StatCard label="Output records" value={formatNumber(run.output_records)} />
          <StatCard label="Failed records" value={formatNumber(run.failed_records)} />
          <StatCard label="Duration"       value={formatDuration(run.duration_seconds)} />
        </div>

        {/* Progress */}
        {isLive && (
          <Card>
            <CardContent>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full animate-pulse" style={{ width: '60%' }} />
                </div>
                <span className="text-sm text-muted-foreground capitalize">{run.current_stage ?? 'processing…'}</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {run.error_message && (
          <Card>
            <CardHeader><CardTitle>Error</CardTitle></CardHeader>
            <CardContent>
              <pre className="text-xs text-destructive font-mono whitespace-pre-wrap">{run.error_message}</pre>
            </CardContent>
          </Card>
        )}

        {/* Logs */}
        {run.logs && run.logs.length > 0 && (
          <Card>
            <CardHeader><CardTitle>Execution log</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="font-mono text-xs bg-sidebar rounded-b-lg overflow-auto max-h-80 p-4 space-y-0.5">
                {(run.logs as LogEntry[]).map((log, i) => (
                  <div key={i} className={`flex gap-3 ${log.level === 'error' ? 'text-red-400' : log.level === 'warning' ? 'text-amber-400' : 'text-sidebar-foreground'}`}>
                    <span className="text-muted-foreground/50 w-16 flex-shrink-0">{log.stage}</span>
                    <span>{log.message}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Timestamps */}
        <Card>
          <CardHeader><CardTitle>Timing</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {[
              ['Created',   run.created_at],
              ['Started',   run.started_at],
              ['Completed', run.completed_at],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between">
                <span className="text-muted-foreground">{k}</span>
                <span className="font-medium tabular">{formatDateTime(v as string)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
