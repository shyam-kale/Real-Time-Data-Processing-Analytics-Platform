import { useAuthStore } from '@/store/auth'

export function useOrg(): string {
  const orgId = useAuthStore(s => s.orgId)
  if (!orgId) {
    // Don't throw — return empty string, pages will show loading/empty state
    return ''
  }
  return orgId
}

export function useOrgSafe() {
  return useAuthStore(s => s.orgId)
}
