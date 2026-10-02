import { apiClient } from './client'
import type { Alert, PaginatedResponse } from '@/types'

export const alertsApi = {
  async list(orgId: string, page = 1): Promise<PaginatedResponse<Alert>> {
    const res = await apiClient.get(`/orgs/${orgId}/alerts`, { params: { page } })
    return res.data
  },
  async create(orgId: string, data: Partial<Alert>): Promise<Alert> {
    const res = await apiClient.post<Alert>(`/orgs/${orgId}/alerts`, data)
    return res.data
  },
  async update(orgId: string, id: string, data: Partial<Alert>): Promise<Alert> {
    const res = await apiClient.put<Alert>(`/orgs/${orgId}/alerts/${id}`, data)
    return res.data
  },
  async delete(orgId: string, id: string): Promise<void> {
    await apiClient.delete(`/orgs/${orgId}/alerts/${id}`)
  },
}
