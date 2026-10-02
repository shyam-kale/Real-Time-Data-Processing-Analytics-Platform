import { useQuery } from '@tanstack/react-query'
import { overviewApi } from '@/services/overview'
import { useAuthStore } from '@/store/auth'
import { PageHeader } from '@/components/layout/AppLayout'
import { StatCard, Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { RunStatusBadge } from '@/components/ui/Badge'
import { InlineLoader } from '@/components/ui/Spinner'
import { ErrorState, EmptyState } from '@/components/ui/EmptyState'
import { formatNumber, formatDuration, formatRelative } from '@/utils/format'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { LayoutDashboard } from 'lucide-react'

export default function Overview() {
  const orgId = useAuthStore(s => s.orgId)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['overview', orgId],
    queryFn: () => overviewApi.get(orgId!),
    enabled: !!orgId,
    refetchInterval: 30_000,
  })

  if (!orgId) return (
    <EmptyState
      icon={<LayoutDashboard className="w-10 h-10" />}
      title="No organization selected"
      description="Please log in again to select your workspace"
    />
  )

  if (isLoading) return <InlineLoader />
  if (error) return <ErrorState message="Failed to load overview" onRetry={refetch} />

  const d = data!

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle="Your data workspace"
        actions={
          <span className="text-xs text-muted-foreground border border-border rounded px-2.5 py-1 bg-card">
            {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        }
      />
      <div className="p-6 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Records"  value={formatNumber(d.total_records)}   sub="across all datasets" trend="+12.5%" />
          <StatCard label="Quality Score"  value={d.quality_score != null ? `${d.quality_score.toFixed(1)}%` : '—'} sub="avg across datasets" />
          <StatCard label="Pipelines"      value={d.total_pipelines} sub={`${d.active_pipelines} active`} />
          <StatCard label="Datasets"       value={d.total_datasets}  sub="ingested" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Processing activity chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Processing activity</CardTitle>
              <span className="text-xs text-muted-foreground">Last 30 days</span>
            </CardHeader>
            <CardContent className="pt-2">
              {d.processing_activity.length === 0 ? (
                <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">No pipeline runs yet</div>
              ) : (
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={d.processing_activity} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="hsl(221,83%,53%)" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="hsl(221,83%,53%)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                    <Area type="monotone" dataKey="records" stroke="hsl(221,83%,53%)" fill="url(#grad)" strokeWidth={1.5} dot={false} name="Records" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Recent activity */}
          <Card>
            <CardHeader><CardTitle>Recent activity</CardTitle></CardHeader>
            <div className="divide-y divide-border">
              {d.recent_activity.slice(0, 6).map((a: any) => (
                <div key={a.id} className="px-4 py-2.5">
                  <p className="text-xs font-medium text-foreground">{a.action.replace('.', ' ')}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {a.resource_name && <span className="text-foreground">{a.resource_name} · </span>}
                    {formatRelative(a.created_at)}
                  </p>
                </div>
              ))}
              {d.recent_activity.length === 0 && <p className="px-4 py-4 text-xs text-muted-foreground">No activity yet</p>}
            </div>
          </Card>
        </div>

        {/* Recent runs */}
        <Card>
          <CardHeader><CardTitle>Recent pipeline runs</CardTitle></CardHeader>
          <Table>
            <Thead>
              <Th>Pipeline</Th><Th>Input</Th><Th>Output</Th><Th>Duration</Th><Th>Status</Th><Th>When</Th>
            </Thead>
            <Tbody>
              {d.recent_runs.map((r: any) => (
                <Tr key={r.id}>
                  <Td className="font-medium">{r.pipeline_name}</Td>
                  <TdMuted>{formatNumber(r.input_records)}</TdMuted>
                  <TdMuted>{formatNumber(r.output_records)}</TdMuted>
                  <TdMuted>{formatDuration(r.duration_seconds)}</TdMuted>
                  <Td><RunStatusBadge status={r.status} /></Td>
                  <TdMuted>{formatRelative(r.created_at)}</TdMuted>
                </Tr>
              ))}
              {d.recent_runs.length === 0 && (
                <Tr><Td colSpan={6} className="text-center text-muted-foreground py-8 text-sm">No runs yet</Td></Tr>
              )}
            </Tbody>
          </Table>
        </Card>
      </div>
    </div>
  )
}
