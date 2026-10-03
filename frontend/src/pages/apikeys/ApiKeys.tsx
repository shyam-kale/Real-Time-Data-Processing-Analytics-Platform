import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiKeysApi } from '@/services/apikeys'
import { useAuthStore } from '@/store/auth'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatRelative, formatDateTime } from '@/utils/format'
import { Plus, Key, Trash2, Copy, CheckCircle, Code2, Zap, Shield } from 'lucide-react'
import type { ApiKeyCreated } from '@/types'

export default function ApiKeys() {
  const orgId = useAuthStore(s => s.orgId) ?? ''
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [created, setCreated] = useState<ApiKeyCreated | null>(null)
  const [copied, setCopied] = useState(false)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['api-keys', orgId],
    queryFn: () => apiKeysApi.list(orgId),
    enabled: !!orgId,
  })

  const createMut = useMutation({
    mutationFn: () => apiKeysApi.create(orgId, name, ['read', 'write']),
    onSuccess: (key) => { qc.invalidateQueries({ queryKey: ['api-keys', orgId] }); setCreated(key); setName('') },
  })

  const revokeMut = useMutation({
    mutationFn: (id: string) => apiKeysApi.revoke(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys', orgId] }),
  })

  const copy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div>
      <PageHeader
        title="API Keys"
        subtitle="Programmatic access to the DataFlow API"
        actions={<Button size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setOpen(true)}>New API key</Button>}
      />

      <div className="p-6 space-y-4">
        {/* What are API keys */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            { icon: Code2, title: 'Programmatic Access', desc: 'Call the DataFlow REST API from your scripts, ETL tools, or CI/CD pipelines without using your password.' },
            { icon: Zap,   title: 'Trigger Pipelines',   desc: 'POST to /pipelines/{id}/run to execute pipelines from external schedulers like cron, Airflow, or GitHub Actions.' },
            { icon: Shield, title: 'Scoped & Revokable', desc: 'Each key has read/write scopes and can be revoked instantly. Never share your login — use API keys instead.' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex gap-3 p-4 bg-muted/40 rounded-lg border border-border">
              <Icon className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">{title}</p>
                <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Usage example */}
        <div className="bg-sidebar rounded-lg p-4 border border-sidebar-border">
          <p className="text-xs font-medium text-sidebar-foreground mb-2">Example usage</p>
          <pre className="text-xs font-mono text-emerald-400 overflow-x-auto">{`# Authenticate with your API key
curl -H "X-API-Key: df_your_key_here" \\
     https://your-api.up.railway.app/api/v1/orgs/{orgId}/datasets

# Trigger a pipeline run
curl -X POST -H "X-API-Key: df_your_key_here" \\
     https://your-api.up.railway.app/api/v1/orgs/{orgId}/pipelines/{id}/run`}</pre>
        </div>

        {/* Newly created key banner */}
        {created && (
          <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
            <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300 mb-2">
              Key created — copy it now, it won't be shown again
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs bg-white dark:bg-black/20 border border-emerald-200 dark:border-emerald-700 rounded px-3 py-2 font-mono break-all">
                {created.raw_key}
              </code>
              <Button variant="outline" size="sm"
                icon={copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                onClick={() => copy(created.raw_key)}>
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setCreated(null)}>Dismiss</Button>
            </div>
          </div>
        )}

        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <Table>
              <Thead>
                <Th>Name</Th><Th>Prefix</Th><Th>Scopes</Th><Th>Status</Th><Th>Last used</Th><Th>Created</Th><Th />
              </Thead>
              <Tbody>
                {data?.map(k => (
                  <Tr key={k.id}>
                    <Td className="font-medium">{k.name}</Td>
                    <Td><code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">{k.key_prefix}…</code></Td>
                    <Td><div className="flex gap-1">{k.scopes.map(s => <Badge key={s} variant="outline" className="text-2xs">{s}</Badge>)}</div></Td>
                    <Td><Badge variant={k.is_active ? 'success' : 'ghost'} dot>{k.is_active ? 'Active' : 'Revoked'}</Badge></Td>
                    <TdMuted>{formatRelative(k.last_used_at)}</TdMuted>
                    <TdMuted>{formatDateTime(k.created_at)}</TdMuted>
                    <Td className="text-right">
                      {k.is_active && (
                        <Button variant="ghost" size="xs" icon={<Trash2 className="w-3 h-3 text-destructive" />}
                          onClick={() => confirm('Revoke this key? This cannot be undone.') && revokeMut.mutate(k.id)} />
                      )}
                    </Td>
                  </Tr>
                ))}
                {data?.length === 0 && (
                  <Tr><Td colSpan={7}>
                    <EmptyState icon={<Key className="w-10 h-10" />} title="No API keys yet"
                      description="Create an API key to access DataFlow programmatically from scripts, pipelines, or external tools"
                      action={() => setOpen(true)} actionLabel="Create first key" />
                  </Td></Tr>
                )}
              </Tbody>
            </Table>
          )}
        </Card>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Create API key" description="Give it a descriptive name so you know where it's used">
        <div className="space-y-4">
          <Input label="Key name" value={name} onChange={e => setName(e.target.value)}
            placeholder="e.g. Production ETL, GitHub Actions, Airflow" autoFocus />
          <p className="text-xs text-muted-foreground">The key will have <strong>read</strong> and <strong>write</strong> scopes. Store it securely — it won't be shown again.</p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} loading={createMut.isPending} disabled={!name}>Create key</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
