import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { pipelinesApi } from '@/services/pipelines'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge, RunStatusBadge } from '@/components/ui/Badge'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Pagination'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatRelative, formatDuration } from '@/utils/format'
import { Plus, GitBranch, Play, Eye, Trash2 } from 'lucide-react'

export default function Pipelines() {
  const orgId = useOrg()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['pipelines', orgId, page],
    queryFn: () => pipelinesApi.list(orgId, page),
  })

  const runMut = useMutation({
    mutationFn: (id: string) => pipelinesApi.run(orgId, id),
    onSuccess: (run) => navigate(`/runs/${run.id}`),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => pipelinesApi.delete(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines', orgId] }),
  })

  return (
    <div>
      <PageHeader
        title="Pipelines"
        subtitle="Build and execute data processing workflows"
        actions={
          <Button icon={<Plus className="w-3.5 h-3.5" />} size="sm" onClick={() => navigate('/pipelines/builder')}>
            New pipeline
          </Button>
        }
      />

      <div className="p-6">
        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <>
              <Table>
                <Thead>
                  <Th>Name</Th><Th>Status</Th><Th>Last run</Th><Th>Last status</Th><Th>Updated</Th><Th />
                </Thead>
                <Tbody>
                  {data?.items.map(p => (
                    <Tr key={p.id} onClick={() => navigate(`/pipelines/${p.id}`)}>
                      <Td className="font-medium">{p.name}</Td>
                      <Td>
                        <Badge variant={p.status === 'active' ? 'success' : p.status === 'archived' ? 'ghost' : 'outline'}>
                          {p.status}
                        </Badge>
                      </Td>
                      <TdMuted>{formatRelative(p.last_run_at)}</TdMuted>
                      <Td>{p.last_run_status ? <RunStatusBadge status={p.last_run_status} /> : <span className="text-muted-foreground text-xs">—</span>}</Td>
                      <TdMuted>{formatRelative(p.updated_at)}</TdMuted>
                      <Td className="text-right" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center gap-1 justify-end">
                          <Button variant="ghost" size="xs" icon={<Play className="w-3 h-3 text-emerald-500" />} loading={runMut.isPending} onClick={() => runMut.mutate(p.id)} />
                          <Button variant="ghost" size="xs" icon={<Eye className="w-3 h-3" />} onClick={() => navigate(`/pipelines/${p.id}`)} />
                          <Button variant="ghost" size="xs" icon={<Trash2 className="w-3 h-3 text-destructive" />} onClick={() => confirm('Delete?') && deleteMut.mutate(p.id)} />
                        </div>
                      </Td>
                    </Tr>
                  ))}
                  {data?.items.length === 0 && (
                    <Tr><Td colSpan={6}><EmptyState icon={<GitBranch className="w-10 h-10" />} title="No pipelines" description="Build your first data pipeline" action={() => navigate('/pipelines/builder')} actionLabel="New pipeline" /></Td></Tr>
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
