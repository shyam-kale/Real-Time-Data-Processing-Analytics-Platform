import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { runsApi } from '@/services/pipelines'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { RunStatusBadge } from '@/components/ui/Badge'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Pagination'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatNumber, formatDuration, formatRelative } from '@/utils/format'
import { Play } from 'lucide-react'

export default function Runs() {
  const orgId = useOrg()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['runs', orgId, page],
    queryFn: () => runsApi.list(orgId, page),
    refetchInterval: 10_000,
  })

  return (
    <div>
      <PageHeader title="Pipeline Runs" subtitle="Execution history across all pipelines" />
      <div className="p-6">
        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <>
              <Table>
                <Thead>
                  <Th>Run ID</Th><Th>Status</Th><Th>Stage</Th><Th>Input</Th><Th>Output</Th><Th>Failed</Th><Th>Duration</Th><Th>Started</Th>
                </Thead>
                <Tbody>
                  {data?.items.map(r => (
                    <Tr key={r.id} onClick={() => navigate(`/runs/${r.id}`)}>
                      <Td className="font-mono text-xs">{r.id.slice(0, 8)}…</Td>
                      <Td><RunStatusBadge status={r.status} /></Td>
                      <TdMuted>{r.current_stage ?? '—'}</TdMuted>
                      <TdMuted className="tabular">{formatNumber(r.input_records)}</TdMuted>
                      <TdMuted className="tabular">{formatNumber(r.output_records)}</TdMuted>
                      <TdMuted className="tabular text-red-500">{r.failed_records ? formatNumber(r.failed_records) : '—'}</TdMuted>
                      <TdMuted>{formatDuration(r.duration_seconds)}</TdMuted>
                      <TdMuted>{formatRelative(r.created_at)}</TdMuted>
                    </Tr>
                  ))}
                  {data?.items.length === 0 && (
                    <Tr><Td colSpan={8}><EmptyState icon={<Play className="w-10 h-10" />} title="No runs yet" description="Execute a pipeline to see runs here" /></Td></Tr>
                  )}
                </Tbody>
              </Table>
              {data && data.total > 0 && (
                <div className="px-3 border-t border-border">
                  <Pagination page={page} totalPages={Math.ceil(data.total / 20)} total={data.total} pageSize={20} onChange={setPage} />
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
