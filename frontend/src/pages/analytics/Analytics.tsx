import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { analyticsApi } from '@/services/analytics'
import { datasetsApi } from '@/services/datasets'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  ScatterChart, Scatter, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { BarChart3, Play } from 'lucide-react'
import type { AnalyticsQuery } from '@/types'

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#06b6d4','#84cc16']
const CHART_TYPES = ['bar','line','area','pie','scatter'] as const

export default function Analytics() {
  const orgId = useOrg()
  const [query, setQuery] = useState<Partial<AnalyticsQuery>>({ aggregation: 'count', chart_type: 'bar', limit: 500 })
  const [dimension, setDimension] = useState('')
  const [measure, setMeasure] = useState('')

  const { data: datasets } = useQuery({
    queryKey: ['datasets-list', orgId],
    queryFn: () => datasetsApi.list(orgId, 1, 100),
  })

  const { data: dsDetail } = useQuery({
    queryKey: ['dataset', orgId, query.dataset_id],
    queryFn: () => datasetsApi.get(orgId, query.dataset_id!),
    enabled: !!query.dataset_id,
  })

  const runMut = useMutation({
    mutationFn: () => analyticsApi.query(orgId, {
      dataset_id: query.dataset_id!,
      dimensions: query.dimensions ?? [],
      measures: query.measures ?? [],
      aggregation: query.aggregation ?? 'count',
      chart_type: query.chart_type ?? 'bar',
      filters: query.filters,
      date_column: query.date_column,
      date_from: query.date_from,
      date_to: query.date_to,
      limit: query.limit ?? 500,
    }),
  })

  const result = runMut.data
  const chartType = query.chart_type ?? 'bar'
  const xKey = (query.dimensions ?? [])[0]
  const yKey = (query.measures ?? [])[0] ?? 'count'

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
                <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={query.dataset_id ?? ''} onChange={e => setQuery(q => ({ ...q, dataset_id: e.target.value, dimensions: [], measures: [] }))}>
                  <option value="">Select…</option>
                  {datasets?.items.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>

              {/* Dimension */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Dimension (X axis)</label>
                <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={dimension} onChange={e => { setDimension(e.target.value); setQuery(q => ({ ...q, dimensions: e.target.value ? [e.target.value] : [] })) }}>
                  <option value="">None</option>
                  {dsDetail?.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                </select>
              </div>

              {/* Measure */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Measure (Y axis)</label>
                <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={measure} onChange={e => { setMeasure(e.target.value); setQuery(q => ({ ...q, measures: e.target.value ? [e.target.value] : [] })) }}>
                  <option value="">None (count)</option>
                  {dsDetail?.columns.filter(c => ['integer','float'].includes(c.data_type)).map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                </select>
              </div>

              {/* Aggregation */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Aggregation</label>
                <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={query.aggregation} onChange={e => setQuery(q => ({ ...q, aggregation: e.target.value as any }))}>
                  {['count','sum','avg','min','max'].map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>

              {/* Chart type */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">Chart type</label>
                <div className="flex flex-wrap gap-1">
                  {CHART_TYPES.map(ct => (
                    <button key={ct} onClick={() => setQuery(q => ({ ...q, chart_type: ct as any }))}
                      className={`px-2 py-1 rounded text-xs border transition-colors ${query.chart_type === ct ? 'bg-primary text-white border-primary' : 'border-border text-muted-foreground hover:border-primary/50'}`}>
                      {ct}
                    </button>
                  ))}
                </div>
              </div>

              <Button className="w-full" size="sm" icon={<Play className="w-3.5 h-3.5" />} loading={runMut.isPending}
                disabled={!query.dataset_id || !dimension} onClick={() => runMut.mutate()}>
                Run query
              </Button>
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
               !result ? <EmptyState icon={<BarChart3 className="w-10 h-10" />} title="Configure and run a query" description="Select a dataset, dimension, and click Run" /> :
               result.data.length === 0 ? <EmptyState title="No data returned" description="Try different filters or dimensions" /> : (
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
                      <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={COLORS[0]} stopOpacity={0.15}/><stop offset="95%" stopColor={COLORS[0]} stopOpacity={0}/></linearGradient></defs>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey={xKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} angle={-30} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 6 }} />
                      <Area type="monotone" dataKey={yKey} stroke={COLORS[0]} fill="url(#ag)" strokeWidth={1.5} dot={false} />
                    </AreaChart>
                  ) : chartType === 'pie' ? (
                    <PieChart>
                      <Pie data={result.data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={130} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`} labelLine={false}>
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
