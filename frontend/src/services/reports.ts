import { apiClient } from './client'
import type { Report, PaginatedResponse } from '@/types'

export const reportsApi = {
  async list(orgId: string, page = 1): Promise<PaginatedResponse<Report>> {
    const res = await apiClient.get(`/orgs/${orgId}/reports`, { params: { page } })
    return res.data
  },
  async get(orgId: string, id: string): Promise<Report> {
    const res = await apiClient.get<Report>(`/orgs/${orgId}/reports/${id}`)
    return res.data
  },
  async create(orgId: string, data: Partial<Report>): Promise<Report> {
    const res = await apiClient.post<Report>(`/orgs/${orgId}/reports`, data)
    return res.data
  },
  async update(orgId: string, id: string, data: Partial<Report>): Promise<Report> {
    const res = await apiClient.put<Report>(`/orgs/${orgId}/reports/${id}`, data)
    return res.data
  },
  async delete(orgId: string, id: string): Promise<void> {
    await apiClient.delete(`/orgs/${orgId}/reports/${id}`)
  },
}
