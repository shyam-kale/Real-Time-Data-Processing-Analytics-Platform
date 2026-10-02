import { apiClient } from './client'
import type { Member, OrgRole } from '@/types'

export const teamApi = {
  async list(orgId: string): Promise<Member[]> {
    const res = await apiClient.get<Member[]>(`/orgs/${orgId}/team`)
    return res.data
  },
  async invite(orgId: string, email: string, role: OrgRole): Promise<Member> {
    const res = await apiClient.post<Member>(`/orgs/${orgId}/team/invite`, { email, role })
    return res.data
  },
  async updateRole(orgId: string, memberId: string, role: OrgRole): Promise<void> {
    await apiClient.put(`/orgs/${orgId}/team/${memberId}`, { role })
  },
  async remove(orgId: string, memberId: string): Promise<void> {
    await apiClient.delete(`/orgs/${orgId}/team/${memberId}`)
  },
}
