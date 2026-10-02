import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { teamApi } from '@/services/team'
import { useOrg } from '@/hooks/useOrg'
import { useAuthStore } from '@/store/auth'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatRelative } from '@/utils/format'
import { UserPlus, Users, Trash2 } from 'lucide-react'
import type { OrgRole } from '@/types'

const ROLE_COLORS: Record<OrgRole, 'error' | 'warning' | 'info' | 'ghost'> = {
  owner: 'error', admin: 'warning', member: 'info', viewer: 'ghost'
}

export default function Team() {
  const orgId = useOrg()
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<OrgRole>('member')

  const { data: members, isLoading, error, refetch } = useQuery({
    queryKey: ['team', orgId],
    queryFn: () => teamApi.list(orgId),
  })

  const inviteMut = useMutation({
    mutationFn: () => teamApi.invite(orgId, email, role),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['team', orgId] }); setOpen(false); setEmail('') },
  })

  const removeMut = useMutation({
    mutationFn: (id: string) => teamApi.remove(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team', orgId] }),
  })

  const roleChangeMut = useMutation({
    mutationFn: ({ id, role }: { id: string; role: OrgRole }) => teamApi.updateRole(orgId, id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team', orgId] }),
  })

  return (
    <div>
      <PageHeader title="Team" subtitle="Manage workspace members and roles"
        actions={<Button size="sm" icon={<UserPlus className="w-3.5 h-3.5" />} onClick={() => setOpen(true)}>Invite member</Button>} />
      <div className="p-6">
        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <Table>
              <Thead><Th>Member</Th><Th>Email</Th><Th>Role</Th><Th>Joined</Th><Th /></Thead>
              <Tbody>
                {members?.map(m => (
                  <Tr key={m.id}>
                    <Td className="font-medium">{m.user_full_name}</Td>
                    <TdMuted>{m.user_email}</TdMuted>
                    <Td>
                      {m.role === 'owner' ? (
                        <Badge variant="error">Owner</Badge>
                      ) : (
                        <select
                          value={m.role}
                          onChange={e => roleChangeMut.mutate({ id: m.id, role: e.target.value as OrgRole })}
                          className="h-6 rounded border border-border bg-background px-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                        >
                          {(['admin','member','viewer'] as OrgRole[]).map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                      )}
                    </Td>
                    <TdMuted>{formatRelative(m.joined_at)}</TdMuted>
                    <Td className="text-right">
                      {m.role !== 'owner' && m.user_id !== user?.id && (
                        <Button variant="ghost" size="xs" icon={<Trash2 className="w-3 h-3 text-destructive" />}
                          onClick={() => confirm('Remove member?') && removeMut.mutate(m.id)} />
                      )}
                    </Td>
                  </Tr>
                ))}
                {members?.length === 0 && (
                  <Tr><Td colSpan={5}><EmptyState icon={<Users className="w-10 h-10" />} title="No members" /></Td></Tr>
                )}
              </Tbody>
            </Table>
          )}
        </Card>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title="Invite member">
        <div className="space-y-4">
          <Input label="Email address" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="colleague@company.com" />
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Role</label>
            <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={role} onChange={e => setRole(e.target.value as OrgRole)}>
              {(['admin','member','viewer'] as OrgRole[]).map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => inviteMut.mutate()} loading={inviteMut.isPending} disabled={!email}>Send invite</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
