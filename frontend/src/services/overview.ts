import { apiClient } from './client'
import type { OverviewData } from '@/types'

export const overviewApi = {
  async get(orgId: string): Promise<OverviewData> {
    const res = await apiClient.get<OverviewData>(`/orgs/${orgId}/overview`)
    return res.data
  },
}
