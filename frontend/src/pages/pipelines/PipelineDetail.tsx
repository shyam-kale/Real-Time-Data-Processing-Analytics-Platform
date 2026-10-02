import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pipelinesApi } from '@/services/pipelines'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge, RunStatusBadge } from '@/components/ui/Badge'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { InlineLoader } from '@/components/ui/Spinner'
import { ErrorState, EmptyState } from '@/components/ui/EmptyState'
import { formatRelative, formatDuration, formatNumber } from '@/utils/format'
import { ArrowLeft, Play, Edit, Play as PlayIcon } from 'lucide-react'

export default function PipelineDetail() {
  const { id } = useParams<{ id: string }>()
  const orgId = useOrg()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: pipeline, isLoading, error } = useQuery({
    queryKey: ['pipeline', orgId, id],
    queryFn: () => pipelinesApi.get(orgId, id!),
  })

  const { data: runs } = useQuery({
    queryKey: ['pipeline-runs', orgId, id],
    queryFn: () => pipelinesApi.getRuns(orgId, id!),
    enabled: !!id,
    refetchInterval: 10_000,
  })

  const runMut = useMutation({
    mutationFn: () => pipelinesApi.run(orgId, id!),
    onSuccess: (run) => { qc.invalidateQueries({ queryKey: ['pipeline-runs', orgId, id] }); navigate(`/runs/${run.id}`) },
  })

  if (isLoading) return <InlineLoader />
  if (error || !pipeline) return <ErrorState message="Pipeline not found" />

  return (
    <div>
      <PageHeader
        title={pipeline.name}
        subtitle={pipeline.description ?? `${pipeline.nodes?.length ?? 0} nodes · ${pipeline.edges?.length ?? 0} edges`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={() => navigate('/pipelines')}>Back</Button>
            <Button variant="outline" size="sm" icon={<Edit className="w-3.5 h-3.5" />} onClick={() => navigate(`/pipelines/builder/${id}`)}>Edit</Button>
            <Button size="sm" icon={<Play className="w-3.5 h-3.5" />} loading={runMut.isPending} onClick={() => runMut.mutate()}>Run now</Button>
          </div>
        }
      />
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Nodes"    value={pipeline.nodes?.length ?? 0} />
          <StatCard label="Edges"    value={pipeline.edges?.length ?? 0} />
          <StatCard label="Status"   value={pipeline.status} />
          <StatCard label="Last run" value={pipeline.last_run_status ?? '—'} />
        </div>

        {/* Nodes */}
        <Card>
          <CardHeader><CardTitle>Pipeline nodes</CardTitle></CardHeader>
          <Table>
            <Thead><Th>Label</Th><Th>Type</Th><Th>Config keys</Th></Thead>
            <Tbody>
              {pipeline.nodes?.map(n => (
                <Tr key={n.id}>
                  <Td className="font-medium">{n.label}</Td>
                  <Td><Badge variant="outline" className="capitalize">{n.node_type.replace('_',' ')}</Badge></Td>
                  <TdMuted className="font-mono text-xs">{Object.keys(n.config).join(', ') || '—'}</TdMuted>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Card>

        {/* Runs */}
        <Card>
          <CardHeader><CardTitle>Run history</CardTitle></CardHeader>
          <Table>
            <Thead><Th>Run ID</Th><Th>Status</Th><Th>Input</Th><Th>Output</Th><Th>Duration</Th><Th>When</Th></Thead>
            <Tbody>
              {runs?.items.map(r => (
                <Tr key={r.id} onClick={() => navigate(`/runs/${r.id}`)}>
                  <Td className="font-mono text-xs">{r.id.slice(0,8)}…</Td>
                  <Td><RunStatusBadge status={r.status} /></Td>
                  <TdMuted className="tabular">{formatNumber(r.input_records)}</TdMuted>
                  <TdMuted className="tabular">{formatNumber(r.output_records)}</TdMuted>
                  <TdMuted>{formatDuration(r.duration_seconds)}</TdMuted>
                  <TdMuted>{formatRelative(r.created_at)}</TdMuted>
                </Tr>
              ))}
              {runs?.items.length === 0 && <Tr><Td colSpan={6}><EmptyState title="No runs yet" description="Click Run now to execute this pipeline" /></Td></Tr>}
            </Tbody>
          </Table>
        </Card>
      </div>
    </div>
  )
}
