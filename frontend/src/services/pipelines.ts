import { apiClient } from './client'
import type { Pipeline, PipelineDetail, PipelineRun, PaginatedResponse } from '@/types'

export const pipelinesApi = {
  async list(orgId: string, page = 1, pageSize = 20): Promise<PaginatedResponse<Pipeline>> {
    const res = await apiClient.get(`/orgs/${orgId}/pipelines`, { params: { page, page_size: pageSize } })
    return res.data
  },
  async get(orgId: string, id: string): Promise<PipelineDetail> {
    const res = await apiClient.get<PipelineDetail>(`/orgs/${orgId}/pipelines/${id}`)
    return res.data
  },
  async create(orgId: string, data: unknown): Promise<PipelineDetail> {
    const res = await apiClient.post<PipelineDetail>(`/orgs/${orgId}/pipelines`, data)
    return res.data
  },
  async update(orgId: string, id: string, data: unknown): Promise<PipelineDetail> {
    const res = await apiClient.put<PipelineDetail>(`/orgs/${orgId}/pipelines/${id}`, data)
    return res.data
  },
  async delete(orgId: string, id: string): Promise<void> {
    await apiClient.delete(`/orgs/${orgId}/pipelines/${id}`)
  },
  async run(orgId: string, id: string): Promise<PipelineRun> {
    const res = await apiClient.post<PipelineRun>(`/orgs/${orgId}/pipelines/${id}/run`)
    return res.data
  },
  async getRuns(orgId: string, id: string, page = 1, pageSize = 20): Promise<PaginatedResponse<PipelineRun>> {
    const res = await apiClient.get(`/orgs/${orgId}/pipelines/${id}/runs`, { params: { page, page_size: pageSize } })
    return res.data
  },
}

export const runsApi = {
  async list(orgId: string, page = 1, pageSize = 20): Promise<PaginatedResponse<PipelineRun>> {
    const res = await apiClient.get(`/orgs/${orgId}/runs`, { params: { page, page_size: pageSize } })
    return res.data
  },
  async get(orgId: string, runId: string): Promise<PipelineRun> {
    const res = await apiClient.get<PipelineRun>(`/orgs/${orgId}/runs/${runId}`)
    return res.data
  },
}
