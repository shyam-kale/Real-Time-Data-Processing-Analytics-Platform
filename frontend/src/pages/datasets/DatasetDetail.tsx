import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datasetsApi } from '@/services/datasets'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge, DatasetStatusBadge, SeverityBadge } from '@/components/ui/Badge'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { InlineLoader } from '@/components/ui/Spinner'
import { ErrorState } from '@/components/ui/EmptyState'
import { formatNumber, formatBytes, formatRelative, formatDateTime, formatScore, scoreColor } from '@/utils/format'
import { ArrowLeft, RefreshCw, ShieldCheck, Search, BarChart3 } from 'lucide-react'

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>()
  const orgId = useOrg()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: ds, isLoading, error, refetch } = useQuery({
    queryKey: ['dataset', orgId, id],
    queryFn: () => datasetsApi.get(orgId, id!),
    // Poll while processing so the schema updates automatically after profiling
    refetchInterval: (q) => q.state.data?.status === 'processing' ? 2000 : false,
  })

  const { data: reports } = useQuery({
    queryKey: ['dataset-quality', orgId, id],
    queryFn: () => datasetsApi.getQualityReports(orgId, id!),
    enabled: !!id,
  })

  const qualityMut = useMutation({
    mutationFn: () => datasetsApi.triggerQuality(orgId, id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataset-quality', orgId, id] }),
  })

  const profileMut = useMutation({
    mutationFn: () => datasetsApi.profile(orgId, id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataset', orgId, id] }),
  })

  if (isLoading) return <InlineLoader />
  if (error || !ds) return <ErrorState message="Dataset not found" onRetry={refetch} />

  const latestReport = reports?.[0]

  return (
    <div>
      <PageHeader
        title={ds.name}
        subtitle={`${formatNumber(ds.row_count)} rows · ${ds.column_count} columns · ${formatBytes(ds.file_size_bytes)}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={() => navigate('/datasets')}>Back</Button>
            <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} loading={profileMut.isPending} onClick={() => profileMut.mutate()}>Re-profile</Button>
            <Button variant="outline" size="sm" icon={<Search className="w-3.5 h-3.5" />} onClick={() => navigate(`/explorer?dataset=${id}`)}>Explore</Button>
            <Button size="sm" icon={<ShieldCheck className="w-3.5 h-3.5" />} loading={qualityMut.isPending} onClick={() => qualityMut.mutate()}>Run quality check</Button>
          </div>
        }
      />

      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: column schema */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader><CardTitle>Schema ({ds.columns?.length ?? 0} columns)</CardTitle><DatasetStatusBadge status={ds.status} /></CardHeader>
            <Table>
              <Thead>
                <Th>#</Th><Th>Column</Th><Th>Type</Th><Th>Nulls</Th><Th>Unique</Th><Th>Min</Th><Th>Max</Th><Th>Mean</Th>
              </Thead>
              <Tbody>
                {ds.columns?.map(col => (
                  <Tr key={col.id}>
                    <TdMuted>{col.position + 1}</TdMuted>
                    <Td className="font-mono text-xs font-medium">{col.name}</Td>
                    <Td><Badge variant="outline" className="font-mono text-xs">{col.data_type}</Badge></Td>
                    <TdMuted className="tabular">{formatNumber(col.null_count)}</TdMuted>
                    <TdMuted className="tabular">{formatNumber(col.unique_count)}</TdMuted>
                    <TdMuted className="tabular font-mono text-xs">{col.min_value ?? '—'}</TdMuted>
                    <TdMuted className="tabular font-mono text-xs">{col.max_value ?? '—'}</TdMuted>
                    <TdMuted className="tabular">{col.mean_value != null ? col.mean_value.toFixed(2) : '—'}</TdMuted>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Card>
        </div>

        {/* Right: meta + quality */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Details</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              {[
                ['Format', ds.file_format.toUpperCase()],
                ['Rows', formatNumber(ds.row_count)],
                ['Columns', ds.column_count ?? '—'],
                ['File size', formatBytes(ds.file_size_bytes)],
                ['Null cells', formatNumber(ds.null_count)],
                ['Duplicates', formatNumber(ds.duplicate_count)],
                ['Last profiled', formatRelative(ds.last_profiled_at)],
                ['Uploaded', formatDateTime(ds.created_at)],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between">
                  <span className="text-muted-foreground">{k}</span>
                  <span className="font-medium tabular">{String(v)}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {latestReport && (
            <Card>
              <CardHeader><CardTitle>Quality score</CardTitle><span className="text-xs text-muted-foreground">{formatRelative(latestReport.created_at)}</span></CardHeader>
              <CardContent className="space-y-3">
                <div className="text-center py-2">
                  <span className={`text-3xl font-semibold tabular ${scoreColor(latestReport.overall_score)}`}>
                    {latestReport.overall_score.toFixed(1)}%
                  </span>
                </div>
                {[
                  ['Completeness', latestReport.completeness_score],
                  ['Uniqueness',   latestReport.uniqueness_score],
                  ['Validity',     latestReport.validity_score],
                  ['Consistency',  latestReport.consistency_score],
                ].map(([label, score]) => (
                  <div key={String(label)} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">{label}</span>
                      <span className="tabular font-medium">{(score as number).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${score}%` }} />
                    </div>
                  </div>
                ))}

                {latestReport.issues.length > 0 && (
                  <div className="pt-2 space-y-2">
                    <p className="text-xs font-medium text-foreground">{latestReport.issues.length} issues found</p>
                    {latestReport.issues.slice(0, 4).map(issue => (
                      <div key={issue.id} className="flex items-start gap-2">
                        <SeverityBadge severity={issue.severity} />
                        <p className="text-xs text-muted-foreground leading-snug">{issue.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
