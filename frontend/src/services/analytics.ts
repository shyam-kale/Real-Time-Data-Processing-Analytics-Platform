import { apiClient } from './client'
import type { AnalyticsQuery, AnalyticsResult } from '@/types'

export const analyticsApi = {
  async query(orgId: string, q: AnalyticsQuery): Promise<AnalyticsResult> {
    const res = await apiClient.post<AnalyticsResult>(`/orgs/${orgId}/analytics/query`, q)
    return res.data
  },
}
