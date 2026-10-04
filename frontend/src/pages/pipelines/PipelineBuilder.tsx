import { useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import ReactFlow, {
  addEdge, Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  type Node, type Edge, type Connection,
  Handle, Position, NodeProps
} from 'reactflow'
import 'reactflow/dist/style.css'
import { pipelinesApi } from '@/services/pipelines'
import { datasetsApi } from '@/services/datasets'
import { useOrg } from '@/hooks/useOrg'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { cn } from '@/utils/cn'
import { Save, ArrowLeft, Plus } from 'lucide-react'
import type { NodeType } from '@/types'

// ── Node type palette ─────────────────────────────────────────────────────────
const NODE_TYPES_DEF: { type: NodeType; label: string; color: string }[] = [
  { type: 'source',        label: 'Source',        color: 'bg-blue-50 border-blue-300 dark:bg-blue-900/30 dark:border-blue-600' },
  { type: 'validation',    label: 'Validation',    color: 'bg-purple-50 border-purple-300 dark:bg-purple-900/30 dark:border-purple-600' },
  { type: 'filter',        label: 'Filter',        color: 'bg-amber-50 border-amber-300 dark:bg-amber-900/30 dark:border-amber-600' },
  { type: 'transform',     label: 'Transform',     color: 'bg-emerald-50 border-emerald-300 dark:bg-emerald-900/30 dark:border-emerald-600' },
  { type: 'deduplicate',   label: 'Deduplicate',   color: 'bg-pink-50 border-pink-300 dark:bg-pink-900/30 dark:border-pink-600' },
  { type: 'aggregate',     label: 'Aggregate',     color: 'bg-orange-50 border-orange-300 dark:bg-orange-900/30 dark:border-orange-600' },
  { type: 'quality_check', label: 'Quality Check', color: 'bg-teal-50 border-teal-300 dark:bg-teal-900/30 dark:border-teal-600' },
  { type: 'output',        label: 'Output',        color: 'bg-slate-50 border-slate-300 dark:bg-slate-900/30 dark:border-slate-600' },
]

const colorMap = Object.fromEntries(NODE_TYPES_DEF.map(n => [n.type, n.color]))

function PipelineNodeComponent({ data, selected }: NodeProps) {
  const color = colorMap[data.nodeType as NodeType] ?? 'bg-card border-border'
  return (
    <div className={cn('rounded-lg border px-4 py-2.5 min-w-[140px] shadow-sm', color, selected && 'ring-2 ring-primary')}>
      <Handle type="target" position={Position.Left} className="!bg-primary !border-primary !w-2.5 !h-2.5" />
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      <p className="text-2xs text-muted-foreground capitalize mt-0.5">{data.nodeType?.replace('_', ' ')}</p>
      <Handle type="source" position={Position.Right} className="!bg-primary !border-primary !w-2.5 !h-2.5" />
    </div>
  )
}

const NODE_COMPONENTS: Record<string, React.ComponentType<NodeProps>> = {
  pipelineNode: PipelineNodeComponent,
}

let nodeCount = 0
function makeNode(type: NodeType, label: string, x: number, y: number): Node {
  nodeCount++
  return {
    id: `node_${nodeCount}_${Date.now()}`,
    type: 'pipelineNode',
    position: { x, y },
    data: { label, nodeType: type, config: {} },
  }
}

// ── Config panel per node type ─────────────────────────────────────────────────
interface ConfigPanelProps {
  node: Node
  datasets: { id: string; name: string; file_path: string; file_format: string }[]
  onChange: (config: Record<string, unknown>) => void
}

function ConfigPanel({ node, datasets, onChange }: ConfigPanelProps) {
  const cfg = (node.data.config ?? {}) as Record<string, unknown>
  const set = (key: string, value: unknown) => onChange({ ...cfg, [key]: value })

  const field = (label: string, key: string, placeholder = ''): JSX.Element => (
    <div key={key}>
      <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
      <input
        value={String(cfg[key] ?? '')}
        onChange={e => set(key, e.target.value)}
        placeholder={placeholder}
        className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
      />
    </div>
  )

  const select = (label: string, key: string, options: string[]): JSX.Element => (
    <div key={key}>
      <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
      <select
        value={String(cfg[key] ?? options[0])}
        onChange={e => set(key, e.target.value)}
        className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
      >
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )

  const ntype = node.data.nodeType as NodeType

  if (ntype === 'source') {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Pick a dataset you already uploaded. The pipeline will read its actual file.</p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Dataset</label>
          <select
            value={String(cfg.dataset_id ?? '')}
            onChange={e => {
              const ds = datasets.find(d => d.id === e.target.value)
              if (ds) onChange({ ...cfg, dataset_id: ds.id, file_path: ds.file_path, file_format: ds.file_format })
            }}
            className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">— select dataset —</option>
            {datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        {cfg.file_path && (
          <p className="text-2xs font-mono text-muted-foreground truncate">{String(cfg.file_path)}</p>
        )}
      </div>
    )
  }

  if (ntype === 'filter') {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Keep rows where the column matches the condition.</p>
        {field('Column name', 'column', 'e.g. status')}
        {select('Operator', 'operator', ['eq', 'neq', 'gt', 'lt', 'contains', 'not_null'])}
        {(cfg.operator ?? 'eq') !== 'not_null' && field('Value', 'value', 'e.g. active')}
      </div>
    )
  }

  if (ntype === 'transform') {
    // Show up to 3 transform operations
    const transforms = (cfg.transforms as { op: string; column: string; value?: string; new_name?: string }[]) ?? []
    const ops = ['uppercase', 'lowercase', 'strip', 'fill_null', 'to_numeric', 'to_datetime', 'rename']
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Apply operations to specific columns.</p>
        {[0, 1, 2].map(i => {
          const t = transforms[i] ?? { op: 'uppercase', column: '' }
          const update = (patch: Partial<typeof t>) => {
            const next = [...transforms]
            next[i] = { ...t, ...patch }
            // remove trailing empty entries
            while (next.length > 0 && !next[next.length - 1].column) next.pop()
            onChange({ ...cfg, transforms: next })
          }
          return (
            <div key={i} className="space-y-1.5 border border-border rounded-md p-2">
              <p className="text-2xs font-semibold text-muted-foreground uppercase">Step {i + 1}</p>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Column</label>
                <input value={t.column} onChange={e => update({ column: e.target.value })} placeholder="column_name"
                  className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Operation</label>
                <select value={t.op} onChange={e => update({ op: e.target.value })}
                  className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring">
                  {ops.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              {t.op === 'fill_null' && (
                <input value={t.value ?? ''} onChange={e => update({ value: e.target.value })} placeholder="fill value"
                  className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
              )}
              {t.op === 'rename' && (
                <input value={t.new_name ?? ''} onChange={e => update({ new_name: e.target.value })} placeholder="new column name"
                  className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
              )}
            </div>
          )
        })}
      </div>
    )
  }

  if (ntype === 'deduplicate') {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Remove duplicate rows. Leave subset blank to deduplicate on all columns.</p>
        {field('Subset columns (comma-separated)', 'subset_raw', 'e.g. email,name')}
        <p className="text-2xs text-muted-foreground">Saved as array automatically on run.</p>
      </div>
    )
  }

  if (ntype === 'aggregate') {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Group rows and compute a summary statistic.</p>
        {field('Group by columns (comma-separated)', 'group_by_raw', 'e.g. category,region')}
        {field('Aggregate column', 'column', 'e.g. amount')}
        {select('Function', 'function', ['count', 'sum', 'avg', 'min', 'max'])}
      </div>
    )
  }

  if (ntype === 'validation') {
    const rules = (cfg.rules as { column: string; check: string }[]) ?? []
    const checks = ['not_null', 'positive', 'unique']
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Drop rows that fail a validation rule.</p>
        {[0, 1, 2].map(i => {
          const r = rules[i] ?? { column: '', check: 'not_null' }
          const update = (patch: Partial<typeof r>) => {
            const next = [...rules]
            next[i] = { ...r, ...patch }
            while (next.length > 0 && !next[next.length - 1].column) next.pop()
            onChange({ ...cfg, rules: next })
          }
          return (
            <div key={i} className="space-y-1.5 border border-border rounded-md p-2">
              <p className="text-2xs font-semibold text-muted-foreground uppercase">Rule {i + 1}</p>
              <input value={r.column} onChange={e => update({ column: e.target.value })} placeholder="column_name"
                className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
              <select value={r.check} onChange={e => update({ check: e.target.value })}
                className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring">
                {checks.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          )
        })}
      </div>
    )
  }

  if (ntype === 'quality_check') {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Log a warning when any column's completeness falls below the threshold.</p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Min completeness %</label>
          <input type="number" min={0} max={100} value={String(cfg.min_completeness ?? 90)}
            onChange={e => set('min_completeness', Number(e.target.value))}
            className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
        </div>
      </div>
    )
  }

  if (ntype === 'output') {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">Final node. Records the output row count and marks the run complete.</p>
        {field('Label / description', 'label', 'e.g. Final output')}
      </div>
    )
  }

  return <p className="text-xs text-muted-foreground">No configuration required for this node type.</p>
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function PipelineBuilder() {
  const orgId = useOrg()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()

  const [name, setName] = useState('Untitled pipeline')
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selected, setSelected] = useState<Node | null>(null)

  // Fetch uploaded datasets for the source node picker
  const { data: datasetsRes } = useQuery({
    queryKey: ['datasets-list', orgId],
    queryFn: () => datasetsApi.list(orgId, 1, 100),
    enabled: !!orgId,
  })
  const datasets = (datasetsRes?.items ?? []).map(d => ({
    id: d.id,
    name: d.name,
    // file_path is on DatasetDetail only; fall back to empty — the backend resolves from dataset_id
    file_path: (d as any).file_path ?? '',
    file_format: d.file_format,
  }))

  // Load existing pipeline when editing
  useQuery({
    queryKey: ['pipeline-load', orgId, id],
    queryFn: async () => {
      if (!id) return null
      const p = await pipelinesApi.get(orgId, id)
      setName(p.name)
      setNodes(p.nodes.map(n => ({
        id: n.id,
        type: 'pipelineNode',
        position: { x: n.position_x ?? 0, y: n.position_y ?? 0 },
        data: { label: n.label, nodeType: n.node_type, config: n.config ?? {} },
      })))
      setEdges(p.edges.map(e => ({ id: e.id, source: e.source_node_id, target: e.target_node_id })))
      return p
    },
    enabled: !!id,
  })

  const saveMut = useMutation({
    mutationFn: () => {
      // Normalise subset/group_by fields that users enter as comma-separated strings
      const processedNodes = nodes.map(n => {
        const cfg = { ...(n.data.config ?? {}) } as Record<string, unknown>
        if (n.data.nodeType === 'deduplicate' && cfg.subset_raw) {
          cfg.subset = String(cfg.subset_raw).split(',').map((s: string) => s.trim()).filter(Boolean)
          delete cfg.subset_raw
        }
        if (n.data.nodeType === 'aggregate' && cfg.group_by_raw) {
          cfg.group_by = String(cfg.group_by_raw).split(',').map((s: string) => s.trim()).filter(Boolean)
          delete cfg.group_by_raw
        }
        return {
          id: n.id,
          node_type: n.data.nodeType,
          label: n.data.label,
          config: cfg,
          position: n.position,
        }
      })
      const payload = {
        name,
        nodes: processedNodes,
        edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
      }
      return id ? pipelinesApi.update(orgId, id, payload) : pipelinesApi.create(orgId, payload)
    },
    onSuccess: (p) => navigate(`/pipelines/${p.id}`),
  })

  const onConnect = useCallback((conn: Connection) => setEdges(e => addEdge(conn, e)), [setEdges])

  const addNode = (type: NodeType, label: string) => {
    const x = 120 + Math.random() * 280
    const y = 80 + Math.random() * 220
    setNodes(ns => [...ns, makeNode(type, label, x, y)])
  }

  const updateConfig = (nodeId: string, config: Record<string, unknown>) => {
    setNodes(ns => ns.map(n => n.id === nodeId ? { ...n, data: { ...n.data, config } } : n))
    // keep selected in sync
    setSelected(prev => prev?.id === nodeId ? { ...prev, data: { ...prev.data, config } } : prev)
  }

  // Sync selected node data from live nodes list (position/config can change externally)
  const liveSelected = selected ? nodes.find(n => n.id === selected.id) ?? selected : null

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-card flex-shrink-0">
        <Button variant="ghost" size="sm" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={() => navigate('/pipelines')} />
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          className="flex-1 max-w-xs bg-transparent text-sm font-semibold text-foreground border-0 focus:outline-none focus:ring-0 placeholder:text-muted-foreground"
          placeholder="Pipeline name..."
        />
        <span className="text-xs text-muted-foreground">{nodes.length} nodes · {edges.length} edges</span>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<Save className="w-3.5 h-3.5" />} loading={saveMut.isPending} onClick={() => saveMut.mutate()}>
            Save
          </Button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left panel — node palette */}
        <div className="w-48 border-r border-border bg-card overflow-y-auto p-3 space-y-1 flex-shrink-0">
          <p className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider px-1 mb-2">Add node</p>
          {NODE_TYPES_DEF.map(n => (
            <button
              key={n.type}
              onClick={() => addNode(n.type, n.label)}
              className={cn('w-full text-left px-3 py-2 rounded-md border text-xs font-medium hover:opacity-80 transition-opacity flex items-center gap-2', n.color)}
            >
              <Plus className="w-3 h-3 flex-shrink-0" />
              {n.label}
            </button>
          ))}
          <div className="pt-3 border-t border-border mt-2">
            <p className="text-2xs text-muted-foreground px-1">Drag nodes on the canvas, connect them left→right, then Save.</p>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 bg-muted/20">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={NODE_COMPONENTS}
            onNodeClick={(_, n) => setSelected(n)}
            onPaneClick={() => setSelected(null)}
            fitView
          >
            <Background gap={16} color="hsl(var(--border))" />
            <Controls />
            <MiniMap nodeColor={() => '#3b82f6'} maskColor="rgba(0,0,0,0.05)" />
          </ReactFlow>
        </div>

        {/* Right panel — node config */}
        {liveSelected && (
          <div className="w-72 border-l border-border bg-card p-4 overflow-y-auto flex-shrink-0 space-y-4">
            <div>
              <p className="text-xs font-semibold text-foreground mb-3">Configure node</p>
              {/* Label */}
              <div className="mb-3">
                <label className="block text-xs font-medium text-muted-foreground mb-1">Label</label>
                <input
                  value={liveSelected.data.label}
                  onChange={e => setNodes(ns => ns.map(n => n.id === liveSelected.id ? { ...n, data: { ...n.data, label: e.target.value } } : n))}
                  className="w-full h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>

              {/* Type badge */}
              <div className="mb-4">
                <span className={cn('inline-block px-2 py-0.5 rounded border text-xs font-medium capitalize', colorMap[liveSelected.data.nodeType] ?? '')}>
                  {String(liveSelected.data.nodeType).replace('_', ' ')}
                </span>
              </div>

              {/* Dynamic config fields */}
              <ConfigPanel
                node={liveSelected}
                datasets={datasets}
                onChange={(config) => updateConfig(liveSelected.id, config)}
              />
            </div>

            <button
              onClick={() => { setNodes(ns => ns.filter(n => n.id !== liveSelected.id)); setSelected(null) }}
              className="w-full mt-2 px-3 py-1.5 rounded-md border border-destructive text-destructive text-xs font-medium hover:bg-destructive/10 transition-colors"
            >
              Remove node
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
