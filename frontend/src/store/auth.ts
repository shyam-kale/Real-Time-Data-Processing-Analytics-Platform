import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Organization } from '@/types'

interface AuthState {
  user: User | null
  org: Organization | null
  orgId: string | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  setOrg: (org: Organization) => void
  setOrgId: (id: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      org: null,
      orgId: null,
      isAuthenticated: false,

      setUser: (user) => set({ user, isAuthenticated: true }),
      setOrg: (org) => set({ org, orgId: org.id }),
      setOrgId: (id) => set({ orgId: id }),
      logout: () => {
        localStorage.removeItem('df_access_token')
        localStorage.removeItem('df_refresh_token')
        set({ user: null, org: null, orgId: null, isAuthenticated: false })
      },
    }),
    {
      name: 'df-auth',
      partialize: (s) => ({ orgId: s.orgId, org: s.org }),
    }
  )
)
