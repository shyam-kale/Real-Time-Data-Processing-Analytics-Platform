import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { analyticsApi } from '@/services/analytics'
import { datasetsApi } from '@/services/datasets'
import { useAuthStore } from '@/store/auth'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  ScatterChart, Scatter, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { BarChart3, Play } from 'lucide-react'
import type { AnalyticsQuery } from '@/types'

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#06b6d4','#84cc16']
const CHART_TYPES = ['bar','line','area','pie','scatter'] as const

export default function Analytics() {
  const orgId = useAuthStore(s => s.orgId) ?? ''
  const [datasetId, setDatasetId] = useState('')
  const [dimension, setDimension] = useState('')
  const [measure, setMeasure] = useState('')
  const [aggregation, setAggregation] = useState('count')
  const [chartType, setChartType] = useState<'bar'|'line'|'area'|'pie'|'scatter'>('bar')

  // Load all datasets
  const { data: datasets } = useQuery({
    queryKey: ['datasets-list', orgId],
    queryFn: () => datasetsApi.list(orgId, 1, 100),
    enabled: !!orgId,
  })

  // Load selected dataset detail to get columns
  const { data: dsDetail } = useQuery({
    queryKey: ['dataset-detail', orgId, datasetId],
    queryFn: () => datasetsApi.get(orgId, datasetId),
    enabled: !!datasetId && !!orgId,
  })

  // Get columns from either dataset columns or schema_snapshot
  const columns: string[] = dsDetail?.columns?.length
    ? dsDetail.columns.map(c => c.name)
    : dsDetail?.schema_snapshot
      ? Object.keys(dsDetail.schema_snapshot as Record<string, string>)
      : []

  const numericColumns: string[] = dsDetail?.columns?.length
    ? dsDetail.columns.filter(c => ['integer','float'].includes(c.data_type)).map(c => c.name)
    : dsDetail?.schema_snapshot
      ? Object.entries(dsDetail.schema_snapshot as Record<string, string>)
          .filter(([,t]) => ['integer','float','number'].includes(t))
          .map(([k]) => k)
      : []

  const runMut = useMutation({
    mutationFn: () => analyticsApi.query(orgId, {
      dataset_id: datasetId,
      dimensions: dimension ? [dimension] : [],
      measures: measure ? [measure] : [],
      aggregation: aggregation as AnalyticsQuery['aggregation'],
      chart_type: chartType,
      limit: 500,
    }),
  })

  const result = runMut.data
  const xKey = dimension
  const yKey = measure || 'count'

  const canRun = !!datasetId && !!dimension

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Build custom charts and queries from your datasets" />

      <div className="p-6 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">

          {/* Query builder */}
          <Card className="lg:col-span-1">
            <CardHeader><CardTitle>Query builder</CardTitle></CardHeader>
            <CardContent className="space-y-4">

              {/* Dataset */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Dataset</label>
                <select
                  className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={datasetId}
                  onChange={e => { setDatasetId(e.target.value); setDimension(''); setMeasure('') }}
                >
                  <option value="">Select dataset...</option>
                  {datasets?.items.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
                {datasets?.items.length === 0 && (
                  <p className="text-xs text-destructive mt-1">No datasets found</p>
                )}
              </div>

              {/* Dimension */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Dimension (X axis)</label>
                <select
                  className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={dimension}
                  onChange={e => setDimension(e.target.value)}
                  disabled={!datasetId}
                >
                  <option value="">Select column...</option>
                  {columns.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                {datasetId && columns.length === 0 && (
                  <p className="text-xs text-amber-500 mt-1">No columns — re-profile this dataset</p>
                )}
              </div>

              {/* Measure */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Measure (Y axis)</label>
                <select
                  className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={measure}
                  onChange={e => setMeasure(e.target.value)}
                  disabled={!datasetId}
                >
                  <option value="">None (count)</option>
                  {numericColumns.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              {/* Aggregation */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Aggregation</label>
                <select
                  className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={aggregation}
                  onChange={e => setAggregation(e.target.value)}
                >
                  {['count','sum','avg','min','max'].map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>

              {/* Chart type */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Chart type</label>
                <div className="flex flex-wrap gap-1">
                  {CHART_TYPES.map(ct => (
                    <button
                      key={ct}
                      onClick={() => setChartType(ct)}
                      className={`px-2 py-1 rounded text-xs border transition-colors ${chartType === ct ? 'bg-primary text-white border-primary' : 'border-border text-muted-foreground hover:border-primary/50'}`}
                    >
                      {ct}
                    </button>
                  ))}
                </div>
              </div>

              <Button
                className="w-full"
                size="sm"
                icon={<Play className="w-3.5 h-3.5" />}
                loading={runMut.isPending}
                disabled={!canRun}
                onClick={() => runMut.mutate()}
              >
                Run query
              </Button>

              {!canRun && datasetId && (
                <p className="text-xs text-muted-foreground text-center">Select a dimension to run</p>
              )}
            </CardContent>
          </Card>

          {/* Chart */}
          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>{result ? `${result.row_count} data points` : 'Chart'}</CardTitle>
              {result && <span className="text-xs text-muted-foreground">{result.query_time_ms}ms</span>}
            </CardHeader>
            <CardContent>
              {runMut.isPending ? <InlineLoader /> :
               runMut.isError ? (
                <div className="flex items-center justify-center h-60 text-sm text-destructive">
                  Query failed — the dataset file may not exist locally. Upload a real file first.
                </div>
               ) :
               !result ? (
                <EmptyState
                  icon={<BarChart3 className="w-10 h-10" />}
                  title="Configure and run a query"
                  description="Select a dataset, dimension, and click Run"
                />
               ) : result.data.length === 0 ? (
                <EmptyState title="No data returned" description="Try different filters or dimensions" />
               ) : (
                <ResponsiveContainer width="100%" height={340}>
                  {chartType === 'bar' ? (
                    <BarChart data={result.data} margin={{ top: 4, right: 4, bottom: 40, left: -10 }}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey={xKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} angle={-30} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                      <Bar dataKey={yKey} fill={COLORS[0]} radius={[3,3,0,0]} />
                    </BarChart>
                  ) : chartType === 'line' ? (
                    <LineChart data={result.data} margin={{ top: 4, right: 4, bottom: 40, left: -10 }}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey={xKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} angle={-30} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                      <Line type="monotone" dataKey={yKey} stroke={COLORS[0]} strokeWidth={2} dot={false} />
                    </LineChart>
                  ) : chartType === 'area' ? (
                    <AreaChart data={result.data} margin={{ top: 4, right: 4, bottom: 40, left: -10 }}>
                      <defs>
                        <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS[0]} stopOpacity={0.15}/>
                          <stop offset="95%" stopColor={COLORS[0]} stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey={xKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} angle={-30} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                      <Area type="monotone" dataKey={yKey} stroke={COLORS[0]} fill="url(#ag)" strokeWidth={1.5} dot={false} />
                    </AreaChart>
                  ) : chartType === 'pie' ? (
                    <PieChart>
                      <Pie data={result.data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={130}
                        label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`} labelLine={false}>
                        {result.data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                    </PieChart>
                  ) : (
                    <ScatterChart margin={{ top: 4, right: 4, bottom: 4, left: -10 }}>
                      <CartesianGrid stroke="hsl(var(--border))" />
                      <XAxis dataKey={xKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                      <YAxis dataKey={yKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                      <Scatter data={result.data} fill={COLORS[0]} />
                    </ScatterChart>
                  )}
                </ResponsiveContainer>
               )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
