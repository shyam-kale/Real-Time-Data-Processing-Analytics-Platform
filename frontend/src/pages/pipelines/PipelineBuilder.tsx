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
import { useOrg } from '@/hooks/useOrg'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { cn } from '@/utils/cn'
import { Save, Play, ArrowLeft, Plus } from 'lucide-react'
import type { NodeType } from '@/types'

// ── Node type definitions ─────────────────────────────────────────────────────
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

const NODE_COMPONENTS = { pipelineNode: PipelineNodeComponent }

let nodeCount = 0
function makeNode(type: NodeType, label: string, x: number, y: number): Node {
  nodeCount++
  return {
    id: `node_${nodeCount}_${Date.now()}`,
    type: 'pipelineNode',
    position: { x, y },
    data: { label, nodeType: type },
  }
}

export default function PipelineBuilder() {
  const orgId = useOrg()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()

  const [name, setName] = useState('Untitled pipeline')
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selected, setSelected] = useState<Node | null>(null)

  // Load existing pipeline
  useQuery({
    queryKey: ['pipeline-load', orgId, id],
    queryFn: async () => {
      if (!id) return null
      const p = await pipelinesApi.get(orgId, id)
      setName(p.name)
      setNodes(p.nodes.map(n => ({
        id: n.id,
        type: 'pipelineNode',
        position: { x: n.position_x, y: n.position_y },
        data: { label: n.label, nodeType: n.node_type, config: n.config },
      })))
      setEdges(p.edges.map(e => ({ id: e.id, source: e.source_node_id, target: e.target_node_id })))
      return p
    },
    enabled: !!id,
  })

  const saveMut = useMutation({
    mutationFn: () => {
      const payload = {
        name,
        nodes: nodes.map(n => ({ id: n.id, node_type: n.data.nodeType, label: n.data.label, config: n.data.config ?? {}, position: n.position })),
        edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
      }
      return id ? pipelinesApi.update(orgId, id, payload) : pipelinesApi.create(orgId, payload)
    },
    onSuccess: (p) => navigate(`/pipelines/${p.id}`),
  })

  const onConnect = useCallback((conn: Connection) => setEdges(e => addEdge(conn, e)), [setEdges])

  const addNode = (type: NodeType, label: string) => {
    const x = 100 + Math.random() * 300
    const y = 100 + Math.random() * 200
    setNodes(ns => [...ns, makeNode(type, label, x, y)])
  }

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
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<Save className="w-3.5 h-3.5" />} loading={saveMut.isPending} onClick={() => saveMut.mutate()}>
            Save
          </Button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left panel — node palette */}
        <div className="w-48 border-r border-border bg-card overflow-y-auto p-3 space-y-1 flex-shrink-0">
          <p className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider px-1 mb-2">Node types</p>
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
        {selected && (
          <div className="w-64 border-l border-border bg-card p-4 overflow-y-auto flex-shrink-0">
            <p className="text-xs font-semibold text-foreground mb-3">Configure node</p>
            <div className="space-y-3">
              <Input
                label="Label"
                value={selected.data.label}
                onChange={e => setNodes(ns => ns.map(n => n.id === selected.id ? { ...n, data: { ...n.data, label: e.target.value } } : n))}
              />
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Type</label>
                <select
                  value={selected.data.nodeType}
                  onChange={e => setNodes(ns => ns.map(n => n.id === selected.id ? { ...n, data: { ...n.data, nodeType: e.target.value } } : n))}
                  className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {NODE_TYPES_DEF.map(t => <option key={t.type} value={t.type}>{t.label}</option>)}
                </select>
              </div>
              {selected.data.nodeType === 'source' && (
                <Input
                  label="File path"
                  value={(selected.data.config as any)?.file_path ?? ''}
                  onChange={e => setNodes(ns => ns.map(n => n.id === selected.id ? { ...n, data: { ...n.data, config: { ...(n.data.config ?? {}), file_path: e.target.value } } } : n))}
                  placeholder="/uploads/file.csv"
                />
              )}
              {selected.data.nodeType === 'filter' && (
                <>
                  <Input label="Column" value={(selected.data.config as any)?.column ?? ''} onChange={e => setNodes(ns => ns.map(n => n.id === selected.id ? { ...n, data: { ...n.data, config: { ...(n.data.config ?? {}), column: e.target.value } } } : n))} placeholder="column_name" />
                  <Input label="Value" value={(selected.data.config as any)?.value ?? ''} onChange={e => setNodes(ns => ns.map(n => n.id === selected.id ? { ...n, data: { ...n.data, config: { ...(n.data.config ?? {}), value: e.target.value } } } : n))} />
                </>
              )}
              <Button variant="destructive" size="xs" className="w-full" onClick={() => { setNodes(ns => ns.filter(n => n.id !== selected.id)); setSelected(null) }}>
                Remove node
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
