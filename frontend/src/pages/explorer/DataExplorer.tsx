import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { datasetsApi } from '@/services/datasets'
import { useOrg } from '@/hooks/useOrg'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, Thead, Th, Tbody, Tr, Td } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Pagination'
import { InlineLoader } from '@/components/ui/Spinner'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { formatNumber } from '@/utils/format'
import { Search, Database, SortAsc, SortDesc, Download } from 'lucide-react'
import type { Dataset } from '@/types'

export default function DataExplorer() {
  const orgId = useOrg()
  const [params] = useSearchParams()
  const presetId = params.get('dataset') ?? ''

  const [selectedId, setSelectedId] = useState(presetId)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState<string | undefined>()
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const { data: datasets } = useQuery({
    queryKey: ['datasets-list', orgId],
    queryFn: () => datasetsApi.list(orgId, 1, 100),
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['explorer', orgId, selectedId, page, search, sortCol, sortDir],
    queryFn: () => datasetsApi.explore(orgId, selectedId, { page, page_size: 50, search: search || undefined, sort_column: sortCol, sort_direction: sortDir }),
    enabled: !!selectedId,
    placeholderData: (prev) => prev,
  })

  useEffect(() => { setPage(1) }, [selectedId, search, sortCol, sortDir])

  const handleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('asc') }
  }

  const exportCsv = () => {
    if (!data) return
    const header = data.columns.join(',')
    const rows = data.rows.map(r => data.columns.map(c => JSON.stringify(r[c] ?? '')).join(','))
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'export.csv'; a.click()
  }

  return (
    <div>
      <PageHeader
        title="Data Explorer"
        subtitle="Browse and search your dataset records with server-side pagination"
        actions={
          <Button variant="outline" size="sm" icon={<Download className="w-3.5 h-3.5" />} onClick={exportCsv} disabled={!data}>
            Export page
          </Button>
        }
      />

      <div className="p-6 space-y-4">
        {/* Dataset selector + search */}
        <div className="flex flex-wrap gap-3 items-end">
          <div className="w-64">
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Dataset</label>
            <select
              value={selectedId}
              onChange={e => setSelectedId(e.target.value)}
              className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select a dataset...</option>
              {datasets?.items.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <div className="flex-1 max-w-xs">
            <Input
              placeholder="Search all columns..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              leading={<Search className="w-3.5 h-3.5" />}
            />
          </div>
          {data && (
            <p className="text-sm text-muted-foreground">{formatNumber(data.total_rows)} total rows</p>
          )}
        </div>

        <Card>
          {!selectedId ? (
            <EmptyState icon={<Database className="w-10 h-10" />} title="Select a dataset" description="Choose a dataset above to browse its records" />
          ) : isLoading ? <InlineLoader /> : error ? <ErrorState onRetry={refetch} /> : !data ? null : (
            <>
              <div className="overflow-auto max-h-[calc(100vh-320px)]">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-card border-b border-border z-10">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground w-12 uppercase">#</th>
                      {data.columns.map(col => (
                        <th
                          key={col}
                          onClick={() => handleSort(col)}
                          className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer whitespace-nowrap hover:text-foreground select-none group"
                        >
                          <span className="flex items-center gap-1">
                            {col}
                            {sortCol === col
                              ? sortDir === 'asc' ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />
                              : <SortAsc className="w-3 h-3 opacity-0 group-hover:opacity-40" />}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.rows.map((row, i) => (
                      <tr key={i} className="hover:bg-muted/30 transition-colors">
                        <td className="px-3 py-2 text-xs text-muted-foreground tabular">{(page - 1) * 50 + i + 1}</td>
                        {data.columns.map(col => (
                          <td key={col} className="px-3 py-2 text-xs text-foreground max-w-[200px] truncate font-mono whitespace-nowrap">
                            {row[col] == null ? <span className="text-muted-foreground/50 italic">null</span> : String(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-3 border-t border-border">
                <Pagination page={page} totalPages={data.total_pages} total={data.total_rows} pageSize={50} onChange={setPage} />
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
