import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { alertsApi } from '@/services/alerts'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input, Textarea } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Badge, SeverityBadge } from '@/components/ui/Badge'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatRelative } from '@/utils/format'
import { Plus, Bell, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'
import type { AlertConditionType, AlertSeverity } from '@/types'

const CONDITION_LABELS: Record<AlertConditionType, string> = {
  quality_score_below: 'Quality score below threshold',
  missing_values_above: 'Missing values above threshold',
  duplicate_percentage_above: 'Duplicate % above threshold',
  pipeline_failure: 'Pipeline failure',
  processing_duration_above: 'Processing duration above threshold',
  schema_change: 'Schema change detected',
  row_count_change: 'Row count change',
}

export default function Alerts() {
  const orgId = useOrg()
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<{
    name: string; description: string; condition_type: AlertConditionType; threshold: string; severity: AlertSeverity
  }>({ name: '', description: '', condition_type: 'quality_score_below', threshold: '85', severity: 'high' })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['alerts', orgId],
    queryFn: () => alertsApi.list(orgId),
  })

  const createMut = useMutation({
    mutationFn: () => alertsApi.create(orgId, {
      name: form.name, description: form.description,
      condition_type: form.condition_type,
      threshold: form.threshold ? parseFloat(form.threshold) : undefined,
      severity: form.severity,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['alerts', orgId] }); setOpen(false) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => alertsApi.delete(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts', orgId] }),
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      alertsApi.update(orgId, id, { status: status === 'active' ? 'inactive' : 'active' } as any),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts', orgId] }),
  })

  return (
    <div>
      <PageHeader title="Alerts" subtitle="Monitor your data quality and pipeline conditions"
        actions={<Button size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setOpen(true)}>New alert</Button>} />
      <div className="p-6">
        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <Table>
              <Thead><Th>Name</Th><Th>Condition</Th><Th>Threshold</Th><Th>Severity</Th><Th>Status</Th><Th>Last triggered</Th><Th /></Thead>
              <Tbody>
                {data?.items.map(a => (
                  <Tr key={a.id}>
                    <Td className="font-medium">{a.name}</Td>
                    <TdMuted className="max-w-[200px] truncate">{CONDITION_LABELS[a.condition_type]}</TdMuted>
                    <TdMuted className="tabular">{a.threshold ?? '—'}</TdMuted>
                    <Td><SeverityBadge severity={a.severity} /></Td>
                    <Td>
                      <Badge variant={a.status === 'active' ? 'success' : a.status === 'triggered' ? 'warning' : 'ghost'} dot>
                        {a.status}
                      </Badge>
                    </Td>
                    <TdMuted>{formatRelative(a.last_triggered_at)}</TdMuted>
                    <Td className="text-right">
                      <div className="flex items-center gap-1 justify-end">
                        <Button variant="ghost" size="xs"
                          icon={a.status === 'active' ? <ToggleRight className="w-3.5 h-3.5 text-emerald-500" /> : <ToggleLeft className="w-3.5 h-3.5" />}
                          onClick={() => toggleMut.mutate({ id: a.id, status: a.status })} />
                        <Button variant="ghost" size="xs" icon={<Trash2 className="w-3 h-3 text-destructive" />}
                          onClick={() => confirm('Delete alert?') && deleteMut.mutate(a.id)} />
                      </div>
                    </Td>
                  </Tr>
                ))}
                {data?.items.length === 0 && (
                  <Tr><Td colSpan={7}><EmptyState icon={<Bell className="w-10 h-10" />} title="No alerts" description="Create alerts to monitor quality and pipeline conditions" action={() => setOpen(true)} actionLabel="New alert" /></Td></Tr>
                )}
              </Tbody>
            </Table>
          )}
        </Card>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title="New alert" description="Define a condition to monitor">
        <div className="space-y-4">
          <Input label="Alert name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Low quality score" />
          <Textarea label="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Optional description" rows={2} />
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Condition</label>
            <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={form.condition_type} onChange={e => setForm(f => ({ ...f, condition_type: e.target.value as AlertConditionType }))}>
              {Object.entries(CONDITION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <Input label="Threshold" type="number" value={form.threshold} onChange={e => setForm(f => ({ ...f, threshold: e.target.value }))} placeholder="e.g. 85" />
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Severity</label>
            <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={form.severity} onChange={e => setForm(f => ({ ...f, severity: e.target.value as AlertSeverity }))}>
              {['low','medium','high','critical'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} loading={createMut.isPending} disabled={!form.name}>Create alert</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
