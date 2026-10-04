import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datasetsApi } from '@/services/datasets'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { SeverityBadge, Badge } from '@/components/ui/Badge'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatRelative, formatNumber, scoreColor, scoreBg } from '@/utils/format'
import { ShieldCheck, RefreshCw } from 'lucide-react'

export default function DataQuality() {
  const orgId = useOrg()
  const qc = useQueryClient()
  const [selectedDataset, setSelectedDataset] = useState('')
  // useState (not useRef) so changing it causes refetchInterval to update
  const [analysing, setAnalysing] = useState(false)

  const { data: datasets } = useQuery({
    queryKey: ['datasets-list', orgId],
    queryFn: () => datasetsApi.list(orgId, 1, 100),
  })

  const { data: reports, isLoading, error, refetch } = useQuery({
    queryKey: ['quality-reports', orgId, selectedDataset],
    queryFn: () => datasetsApi.getQualityReports(orgId, selectedDataset),
    enabled: !!selectedDataset,
    // Poll every 2 s while waiting for the background analysis to finish
    refetchInterval: analysing ? 2000 : false,
    onSuccess: (data: any[]) => {
      // Stop polling once we have at least one report
      if (data && data.length > 0) setAnalysing(false)
    },
  })

  const runMut = useMutation({
    mutationFn: () => datasetsApi.triggerQuality(orgId, selectedDataset),
    onSuccess: () => {
      setAnalysing(true)
      // Immediately clear stale cache so we show the spinner, not old data
      qc.removeQueries({ queryKey: ['quality-reports', orgId, selectedDataset] })
    },
  })

  const latest = reports?.[0]
  const waiting = analysing || runMut.isPending

  return (
    <div>
      <PageHeader
        title="Data Quality"
        subtitle="Analyze completeness, uniqueness, validity, and consistency"
        actions={
          <Button
            size="sm"
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            loading={runMut.isPending}
            disabled={!selectedDataset}
            onClick={() => runMut.mutate()}
          >
            Run analysis
          </Button>
        }
      />

      <div className="p-6 space-y-4">
        {/* Dataset picker */}
        <div className="w-72">
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Dataset</label>
          <select
            value={selectedDataset}
            onChange={e => { setSelectedDataset(e.target.value); setAnalysing(false) }}
            className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">Select a dataset...</option>
            {datasets?.items.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>

        {/* States */}
        {!selectedDataset ? (
          <Card>
            <EmptyState
              icon={<ShieldCheck className="w-10 h-10" />}
              title="Select a dataset"
              description="Choose a dataset above, then click Run analysis"
            />
          </Card>

        ) : isLoading ? (
          <InlineLoader />

        ) : error ? (
          <ErrorState onRetry={refetch} />

        ) : waiting ? (
          <Card>
            <div className="p-14 flex flex-col items-center gap-4">
              <InlineLoader />
              <p className="text-sm text-muted-foreground">
                Running quality analysis on your file… this may take a few seconds
              </p>
            </div>
          </Card>

        ) : !latest ? (
          <Card>
            <EmptyState
              icon={<ShieldCheck className="w-10 h-10" />}
              title="No quality reports yet"
              description="Click Run analysis to analyse completeness, duplicates, outliers and more"
              action={() => runMut.mutate()}
              actionLabel="Run now"
            />
          </Card>

        ) : (
          <>
            {/* Score overview */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <StatCard label="Overall"      value={`${latest.overall_score.toFixed(1)}%`}      className={scoreBg(latest.overall_score)} />
              <StatCard label="Completeness" value={`${latest.completeness_score.toFixed(1)}%`} />
              <StatCard label="Uniqueness"   value={`${latest.uniqueness_score.toFixed(1)}%`}   />
              <StatCard label="Validity"     value={`${latest.validity_score.toFixed(1)}%`}     />
              <StatCard label="Consistency"  value={`${latest.consistency_score.toFixed(1)}%`}  />
            </div>

            {/* Row counts */}
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Total rows"  value={formatNumber(latest.total_rows)}  />
              <StatCard label="Passed rows" value={formatNumber(latest.passed_rows)} />
              <StatCard label="Failed rows" value={formatNumber(latest.failed_rows)} />
            </div>

            {/* Issues table */}
            <Card>
              <CardHeader>
                <CardTitle>Issues ({latest.issues.length})</CardTitle>
                <span className="text-xs text-muted-foreground">Analysed {formatRelative(latest.created_at)}</span>
              </CardHeader>
              {latest.issues.length === 0 ? (
                <CardContent>
                  <p className="text-sm text-emerald-600 font-medium">✓ No issues found — your data looks clean!</p>
                </CardContent>
              ) : (
                <Table>
                  <Thead>
                    <Th>Type</Th><Th>Severity</Th><Th>Column</Th><Th>Description</Th><Th>Affected rows</Th><Th>%</Th>
                  </Thead>
                  <Tbody>
                    {latest.issues.map(issue => (
                      <Tr key={issue.id}>
                        <Td><Badge variant="outline">{issue.issue_type.replace(/_/g, ' ')}</Badge></Td>
                        <Td><SeverityBadge severity={issue.severity} /></Td>
                        <TdMuted className="font-mono text-xs">{issue.column_name ?? '—'}</TdMuted>
                        <Td className="text-xs max-w-xs">
                          <p>{issue.description}</p>
                          {issue.suggestion && (
                            <p className="text-muted-foreground mt-0.5 italic">{issue.suggestion}</p>
                          )}
                        </Td>
                        <TdMuted className="tabular">{formatNumber(issue.affected_rows)}</TdMuted>
                        <TdMuted className="tabular">{issue.affected_percentage.toFixed(1)}%</TdMuted>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
            </Card>

            {/* Report history */}
            {reports && reports.length > 1 && (
              <Card>
                <CardHeader><CardTitle>Report history</CardTitle></CardHeader>
                <Table>
                  <Thead><Th>Date</Th><Th>Score</Th><Th>Issues</Th><Th>Rows</Th></Thead>
                  <Tbody>
                    {reports.map(r => (
                      <Tr key={r.id}>
                        <TdMuted>{formatRelative(r.created_at)}</TdMuted>
                        <Td className={`font-semibold tabular ${scoreColor(r.overall_score)}`}>
                          {r.overall_score.toFixed(1)}%
                        </Td>
                        <TdMuted>{r.issue_count}</TdMuted>
                        <TdMuted className="tabular">{formatNumber(r.total_rows)}</TdMuted>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  )
}
