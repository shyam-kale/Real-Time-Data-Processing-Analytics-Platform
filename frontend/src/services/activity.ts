import { apiClient } from './client'
import type { ActivityLog, PaginatedResponse } from '@/types'

export const activityApi = {
  async list(orgId: string, page = 1, pageSize = 50, action?: string): Promise<PaginatedResponse<ActivityLog>> {
    const res = await apiClient.get(`/orgs/${orgId}/activity`, { params: { page, page_size: pageSize, action } })
    return res.data
  },
}
