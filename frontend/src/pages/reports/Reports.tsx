import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reportsApi } from '@/services/reports'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input, Textarea } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatRelative } from '@/utils/format'
import { Plus, FileText, Trash2, Edit2 } from 'lucide-react'

export default function Reports() {
  const orgId = useOrg()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['reports', orgId, page],
    queryFn: () => reportsApi.list(orgId, page),
  })

  const createMut = useMutation({
    mutationFn: () => reportsApi.create(orgId, { name: form.name, description: form.description, config: {} }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['reports', orgId] }); setOpen(false); setForm({ name: '', description: '' }) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => reportsApi.delete(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports', orgId] }),
  })

  return (
    <div>
      <PageHeader title="Reports" subtitle="Save and share analytical reports"
        actions={<Button size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setOpen(true)}>New report</Button>} />
      <div className="p-6">
        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <>
              <Table>
                <Thead><Th>Name</Th><Th>Description</Th><Th>Visibility</Th><Th>Updated</Th><Th /></Thead>
                <Tbody>
                  {data?.items.map(r => (
                    <Tr key={r.id}>
                      <Td className="font-medium">{r.name}</Td>
                      <TdMuted className="max-w-xs truncate">{r.description ?? '—'}</TdMuted>
                      <Td><Badge variant={r.is_public ? 'info' : 'ghost'}>{r.is_public ? 'Public' : 'Private'}</Badge></Td>
                      <TdMuted>{formatRelative(r.updated_at)}</TdMuted>
                      <Td className="text-right">
                        <Button variant="ghost" size="xs" icon={<Trash2 className="w-3 h-3 text-destructive" />}
                          onClick={() => confirm('Delete report?') && deleteMut.mutate(r.id)} />
                      </Td>
                    </Tr>
                  ))}
                  {data?.items.length === 0 && (
                    <Tr><Td colSpan={5}><EmptyState icon={<FileText className="w-10 h-10" />} title="No reports" description="Create your first report" action={() => setOpen(true)} actionLabel="New report" /></Td></Tr>
                  )}
                </Tbody>
              </Table>
              {data && data.total > 20 && (
                <div className="px-3 border-t border-border">
                  <Pagination page={page} totalPages={Math.ceil(data.total / 20)} total={data.total} pageSize={20} onChange={setPage} />
                </div>
              )}
            </>
          )}
        </Card>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title="New report">
        <div className="space-y-4">
          <Input label="Report name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Monthly Sales Summary" required />
          <Textarea label="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Optional description..." />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} loading={createMut.isPending} disabled={!form.name}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
