import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { activityApi } from '@/services/activity'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatDateTime } from '@/utils/format'
import { Activity as ActivityIcon, Search } from 'lucide-react'

const ACTION_COLOR: Record<string, 'success' | 'info' | 'warning' | 'error' | 'ghost'> = {
  uploaded: 'info', created: 'success', deleted: 'error', updated: 'warning',
  executed: 'info', triggered: 'warning', invited: 'success', removed: 'error',
}

function actionVariant(action: string) {
  for (const [k, v] of Object.entries(ACTION_COLOR)) {
    if (action.includes(k)) return v
  }
  return 'ghost' as const
}

export default function Activity() {
  const orgId = useOrg()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['activity', orgId, page, search],
    queryFn: () => activityApi.list(orgId, page, 50, search || undefined),
    refetchInterval: 30_000,
  })

  return (
    <div>
      <PageHeader title="Activity Log" subtitle="Audit trail of all actions in your workspace" />
      <div className="p-6 space-y-4">
        <div className="max-w-xs">
          <Input placeholder="Filter by action..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
            leading={<Search className="w-3.5 h-3.5" />} />
        </div>
        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <>
              <Table>
                <Thead><Th>Action</Th><Th>Resource</Th><Th>Resource name</Th><Th>User</Th><Th>IP</Th><Th>Time</Th></Thead>
                <Tbody>
                  {data?.items.map(l => (
                    <Tr key={l.id}>
                      <Td><Badge variant={actionVariant(l.action)}>{l.action}</Badge></Td>
                      <TdMuted>{l.resource_type ?? '—'}</TdMuted>
                      <TdMuted className="max-w-[180px] truncate">{l.resource_name ?? '—'}</TdMuted>
                      <TdMuted className="font-mono text-xs">{l.user_id?.slice(0, 8) ?? 'system'}</TdMuted>
                      <TdMuted className="font-mono">{l.ip_address ?? '—'}</TdMuted>
                      <TdMuted>{formatDateTime(l.created_at)}</TdMuted>
                    </Tr>
                  ))}
                  {data?.items.length === 0 && (
                    <Tr><Td colSpan={6}><EmptyState icon={<ActivityIcon className="w-10 h-10" />} title="No activity" description="Actions will appear here as you use the platform" /></Td></Tr>
                  )}
                </Tbody>
              </Table>
              {data && data.total > 0 && (
                <div className="px-3 border-t border-border">
                  <Pagination page={page} totalPages={Math.ceil(data.total / 50)} total={data.total} pageSize={50} onChange={setPage} />
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
