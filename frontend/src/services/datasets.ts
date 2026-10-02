import { apiClient } from './client'
import type { Dataset, DatasetDetail, QualityReport, PaginatedResponse, DataExplorerResponse, FilterItem } from '@/types'

export const datasetsApi = {
  async list(orgId: string, page = 1, pageSize = 20, search?: string): Promise<PaginatedResponse<Dataset>> {
    const res = await apiClient.get(`/orgs/${orgId}/datasets`, { params: { page, page_size: pageSize, search } })
    return res.data
  },
  async get(orgId: string, id: string): Promise<DatasetDetail> {
    const res = await apiClient.get<DatasetDetail>(`/orgs/${orgId}/datasets/${id}`)
    return res.data
  },
  async upload(orgId: string, form: FormData): Promise<Dataset> {
    const res = await apiClient.post<Dataset>(`/orgs/${orgId}/datasets`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },
  async delete(orgId: string, id: string): Promise<void> {
    await apiClient.delete(`/orgs/${orgId}/datasets/${id}`)
  },
  async profile(orgId: string, id: string): Promise<void> {
    await apiClient.post(`/orgs/${orgId}/datasets/${id}/profile`)
  },
  async triggerQuality(orgId: string, id: string): Promise<{ report_id: string }> {
    const res = await apiClient.post<{ report_id: string }>(`/orgs/${orgId}/datasets/${id}/quality`)
    return res.data
  },
  async getQualityReports(orgId: string, id: string): Promise<QualityReport[]> {
    const res = await apiClient.get<QualityReport[]>(`/orgs/${orgId}/datasets/${id}/quality`)
    return res.data
  },
  async explore(orgId: string, id: string, query: {
    page: number; page_size: number; search?: string
    sort_column?: string; sort_direction?: string; filters?: FilterItem[]
  }): Promise<DataExplorerResponse> {
    const res = await apiClient.post<DataExplorerResponse>(`/orgs/${orgId}/datasets/${id}/explore`, query)
    return res.data
  },
}
