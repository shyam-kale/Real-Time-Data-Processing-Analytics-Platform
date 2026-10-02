import { apiClient, setTokens, clearTokens } from './client'
import type { TokenResponse, User, Organization } from '@/types'

export const authApi = {
  async register(data: { email: string; password: string; full_name: string; org_name: string }): Promise<TokenResponse> {
    const res = await apiClient.post<TokenResponse>('/auth/register', data)
    setTokens(res.data.access_token, res.data.refresh_token)
    return res.data
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const res = await apiClient.post<TokenResponse>('/auth/login', { email, password })
    setTokens(res.data.access_token, res.data.refresh_token)
    return res.data
  },

  async me(): Promise<User> {
    const res = await apiClient.get<User>('/auth/me')
    return res.data
  },

  async myOrganizations(): Promise<Organization[]> {
    const res = await apiClient.get<{ organizations: Organization[] }>('/auth/organizations')
    return res.data.organizations ?? []
  },

  logout() {
    clearTokens()
  },
}
