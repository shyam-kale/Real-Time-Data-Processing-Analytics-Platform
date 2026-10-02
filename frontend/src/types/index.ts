// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  full_name: string
  avatar_url: string | null
  is_active: boolean
  is_superuser: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  description: string | null
  logo_url: string | null
  is_active: boolean
}

export type OrgRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface Member {
  id: string
  user_id: string
  organization_id: string
  role: OrgRole
  user_email: string
  user_full_name: string
  user_avatar_url: string | null
  joined_at: string
}

// ─── Datasets ─────────────────────────────────────────────────────────────────
export type DatasetStatus = 'pending' | 'processing' | 'ready' | 'error'
export type FileFormat = 'csv' | 'json' | 'excel'
export type ColumnDataType = 'integer' | 'float' | 'string' | 'boolean' | 'datetime' | 'date' | 'unknown'

export interface Dataset {
  id: string
  name: string
  description: string | null
  file_format: FileFormat
  file_size_bytes: number
  status: DatasetStatus
  row_count: number | null
  column_count: number | null
  null_count: number | null
  duplicate_count: number | null
  tags: string | null
  created_at: string
  updated_at: string
  last_profiled_at: string | null
}

export interface DatasetColumn {
  id: string
  name: string
  position: number
  data_type: ColumnDataType
  nullable: boolean
  null_count: number | null
  unique_count: number | null
  min_value: string | null
  max_value: string | null
  mean_value: number | null
  std_value: number | null
  sample_values: unknown[] | null
}

export interface DatasetDetail extends Dataset {
  columns: DatasetColumn[]
  profile_data: Record<string, unknown> | null
}

// ─── Quality ──────────────────────────────────────────────────────────────────
export type QualitySeverity = 'info' | 'warning' | 'error' | 'critical'
export type QualityIssueType =
  | 'missing_values'
  | 'duplicates'
  | 'invalid_type'
  | 'invalid_format'
  | 'outlier'
  | 'schema_drift'
  | 'constraint_violation'

export interface QualityIssue {
  id: string
  issue_type: QualityIssueType
  severity: QualitySeverity
  column_name: string | null
  description: string
  affected_rows: number
  affected_percentage: number
  sample_values: unknown[] | null
  suggestion: string | null
}

export interface QualityReport {
  id: string
  dataset_id: string
  overall_score: number
  completeness_score: number
  uniqueness_score: number
  validity_score: number
  consistency_score: number
  total_rows: number
  passed_rows: number
  failed_rows: number
  issue_count: number
  summary: Record<string, unknown> | null
  created_at: string
  issues: QualityIssue[]
}

// ─── Pipelines ────────────────────────────────────────────────────────────────
export type PipelineStatus = 'draft' | 'active' | 'archived'
export type RunStatus = 'pending' | 'running' | 'success' | 'warning' | 'failed' | 'cancelled'
export type NodeType =
  | 'source'
  | 'validation'
  | 'filter'
  | 'transform'
  | 'deduplicate'
  | 'aggregate'
  | 'quality_check'
  | 'output'

export interface PipelineNode {
  id: string
  node_type: NodeType
  label: string
  config: Record<string, unknown>
  position_x: number
  position_y: number
}

export interface PipelineEdge {
  id: string
  source_node_id: string
  target_node_id: string
}

export interface Pipeline {
  id: string
  name: string
  description: string | null
  status: PipelineStatus
  tags: string | null
  created_at: string
  updated_at: string
  last_run_at: string | null
  last_run_status: RunStatus | null
}

export interface PipelineDetail extends Pipeline {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}

export interface PipelineRun {
  id: string
  pipeline_id: string
  status: RunStatus
  current_stage: string | null
  input_records: number | null
  output_records: number | null
  failed_records: number | null
  duration_seconds: number | null
  error_message: string | null
  logs: LogEntry[] | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface LogEntry {
  ts: number
  stage: string
  message: string
  level: 'info' | 'warning' | 'error'
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export interface AnalyticsQuery {
  dataset_id: string
  dimensions: string[]
  measures: string[]
  aggregation: 'count' | 'sum' | 'avg' | 'min' | 'max'
  filters?: FilterItem[]
  date_column?: string
  date_from?: string
  date_to?: string
  chart_type: 'bar' | 'line' | 'area' | 'scatter' | 'pie' | 'histogram'
  limit?: number
}

export interface AnalyticsResult {
  data: Record<string, unknown>[]
  columns: string[]
  row_count: number
  query_time_ms: number
}

// ─── Reports ──────────────────────────────────────────────────────────────────
export interface Report {
  id: string
  name: string
  description: string | null
  config: Record<string, unknown>
  is_public: boolean
  tags: string | null
  created_by: string
  created_at: string
  updated_at: string
}

// ─── Alerts ───────────────────────────────────────────────────────────────────
export type AlertConditionType =
  | 'quality_score_below'
  | 'missing_values_above'
  | 'duplicate_percentage_above'
  | 'pipeline_failure'
  | 'processing_duration_above'
  | 'schema_change'
  | 'row_count_change'

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'
export type AlertStatus = 'active' | 'inactive' | 'triggered'

export interface Alert {
  id: string
  name: string
  description: string | null
  condition_type: AlertConditionType
  threshold: number | null
  dataset_id: string | null
  pipeline_id: string | null
  severity: AlertSeverity
  status: AlertStatus
  last_triggered_at: string | null
  created_at: string
}

// ─── API Keys ─────────────────────────────────────────────────────────────────
export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  last_used_at: string | null
  expires_at: string | null
  created_at: string
}

export interface ApiKeyCreated extends ApiKey {
  raw_key: string
}

// ─── Activity ─────────────────────────────────────────────────────────────────
export interface ActivityLog {
  id: string
  action: string
  resource_type: string | null
  resource_id: string | null
  resource_name: string | null
  user_id: string | null
  details: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

// ─── Shared ───────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages?: number
}

export interface FilterItem {
  column: string
  operator: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'not_null'
  value?: unknown
}

export interface DataExplorerResponse {
  rows: Record<string, unknown>[]
  total_rows: number
  page: number
  page_size: number
  total_pages: number
  columns: string[]
}

export interface OverviewData {
  total_datasets: number
  total_records: number
  total_pipelines: number
  active_pipelines: number
  quality_score: number | null
  recent_runs: RecentRun[]
  processing_activity: ActivityPoint[]
  recent_activity: ActivityLog[]
  run_statuses: Record<string, number>
}

export interface RecentRun {
  id: string
  pipeline_id: string
  pipeline_name: string
  status: RunStatus
  input_records: number | null
  output_records: number | null
  duration_seconds: number | null
  created_at: string
}

export interface ActivityPoint {
  date: string
  runs: number
  records: number
}
