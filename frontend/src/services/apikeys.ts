import { apiClient } from './client'
import type { ApiKey, ApiKeyCreated } from '@/types'

export const apiKeysApi = {
  async list(orgId: string): Promise<ApiKey[]> {
    const res = await apiClient.get<ApiKey[]>(`/orgs/${orgId}/api-keys`)
    return res.data
  },
  async create(orgId: string, name: string, scopes: string[]): Promise<ApiKeyCreated> {
    const res = await apiClient.post<ApiKeyCreated>(`/orgs/${orgId}/api-keys`, { name, scopes })
    return res.data
  },
  async revoke(orgId: string, id: string): Promise<void> {
    await apiClient.delete(`/orgs/${orgId}/api-keys/${id}`)
  },
}
