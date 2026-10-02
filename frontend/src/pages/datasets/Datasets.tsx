import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { datasetsApi } from '@/services/datasets'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td, TdMuted } from '@/components/ui/Table'
import { DatasetStatusBadge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { formatBytes, formatNumber, formatRelative } from '@/utils/format'
import { Upload, Database, Search, Trash2, Eye, RefreshCw } from 'lucide-react'

export default function Datasets() {
  const orgId = useOrg()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadName, setUploadName] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['datasets', orgId, page, search],
    queryFn: () => datasetsApi.list(orgId, page, 20, search || undefined),
  })

  const uploadMut = useMutation({
    mutationFn: () => {
      const form = new FormData()
      form.append('file', uploadFile!)
      form.append('name', uploadName)
      return datasetsApi.upload(orgId, form)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['datasets', orgId] }); setUploadOpen(false); setUploadFile(null); setUploadName('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => datasetsApi.delete(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets', orgId] }),
  })

  const profileMut = useMutation({
    mutationFn: (id: string) => datasetsApi.profile(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets', orgId] }),
  })

  return (
    <div>
      <PageHeader
        title="Datasets"
        subtitle="Manage your ingested data sources"
        actions={
          <Button icon={<Upload className="w-3.5 h-3.5" />} size="sm" onClick={() => setUploadOpen(true)}>
            Upload dataset
          </Button>
        }
      />

      <div className="p-6 space-y-4">
        <div className="flex gap-3">
          <div className="flex-1 max-w-xs">
            <Input
              placeholder="Search datasets..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              leading={<Search className="w-3.5 h-3.5" />}
            />
          </div>
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={() => refetch()}>
            Refresh
          </Button>
        </div>

        <Card>
          {isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : (
            <>
              <Table>
                <Thead>
                  <Th>Name</Th>
                  <Th>Format</Th>
                  <Th>Rows</Th>
                  <Th>Columns</Th>
                  <Th>Size</Th>
                  <Th>Status</Th>
                  <Th>Last profiled</Th>
                  <Th />
                </Thead>
                <Tbody>
                  {data?.items.map(ds => (
                    <Tr key={ds.id} onClick={() => navigate(`/datasets/${ds.id}`)}>
                      <Td className="font-medium max-w-[200px] truncate">{ds.name}</Td>
                      <TdMuted className="uppercase">{ds.file_format}</TdMuted>
                      <TdMuted className="tabular">{formatNumber(ds.row_count)}</TdMuted>
                      <TdMuted className="tabular">{ds.column_count ?? '—'}</TdMuted>
                      <TdMuted>{formatBytes(ds.file_size_bytes)}</TdMuted>
                      <Td><DatasetStatusBadge status={ds.status} /></Td>
                      <TdMuted>{formatRelative(ds.last_profiled_at)}</TdMuted>
                      <Td className="text-right" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center gap-1 justify-end">
                          <Button variant="ghost" size="xs" icon={<RefreshCw className="w-3 h-3" />} onClick={() => profileMut.mutate(ds.id)} />
                          <Button variant="ghost" size="xs" icon={<Eye className="w-3 h-3" />} onClick={() => navigate(`/datasets/${ds.id}`)} />
                          <Button variant="ghost" size="xs" icon={<Trash2 className="w-3 h-3 text-destructive" />} onClick={() => confirm('Delete dataset?') && deleteMut.mutate(ds.id)} />
                        </div>
                      </Td>
                    </Tr>
                  ))}
                  {data?.items.length === 0 && (
                    <Tr><Td colSpan={8}><EmptyState icon={<Database className="w-10 h-10" />} title="No datasets" description="Upload your first CSV, JSON, or Excel file" action={() => setUploadOpen(true)} actionLabel="Upload dataset" /></Td></Tr>
                  )}
                </Tbody>
              </Table>
              {data && data.total > 0 && (
                <div className="px-3">
                  <Pagination page={page} totalPages={data.total_pages ?? 1} total={data.total} pageSize={20} onChange={setPage} />
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      {/* Upload modal */}
      <Modal open={uploadOpen} onClose={() => setUploadOpen(false)} title="Upload dataset" description="Supports CSV, JSON, and Excel files up to 500MB">
        <div className="space-y-4">
          {!uploadFile ? (
            <div
              className="border-2 border-dashed border-border rounded-lg p-10 text-center cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              <Upload className="w-8 h-8 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm font-medium text-foreground">Click to select file</p>
              <p className="text-xs text-muted-foreground mt-1">CSV, JSON, XLSX up to 500MB</p>
              <input ref={fileRef} type="file" accept=".csv,.json,.xlsx,.xls" className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) { setUploadFile(f); setUploadName(f.name.replace(/\.[^.]+$/, '')) } }} />
            </div>
          ) : (
            <div className="flex items-center gap-3 px-4 py-3 bg-muted rounded-lg">
              <Database className="w-5 h-5 text-primary" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{uploadFile.name}</p>
                <p className="text-xs text-muted-foreground">{formatBytes(uploadFile.size)}</p>
              </div>
              <Button variant="ghost" size="xs" onClick={() => setUploadFile(null)}>Remove</Button>
            </div>
          )}
          <Input label="Dataset name" value={uploadName} onChange={e => setUploadName(e.target.value)} placeholder="My dataset" />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setUploadOpen(false)}>Cancel</Button>
            <Button onClick={() => uploadMut.mutate()} loading={uploadMut.isPending} disabled={!uploadFile || !uploadName}>
              Upload
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
