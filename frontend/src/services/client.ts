import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || ''

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('df_access_token')
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401
let isRefreshing = false
let waitQueue: Array<(token: string) => void> = []

apiClient.interceptors.response.use(
  res => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status !== 401 || original._retry) return Promise.reject(error)

    const refreshToken = localStorage.getItem('df_refresh_token')
    if (!refreshToken) { clearTokens(); window.location.href = '/login'; return Promise.reject(error) }

    if (isRefreshing) {
      return new Promise(resolve => {
        waitQueue.push((token: string) => {
          original.headers['Authorization'] = `Bearer ${token}`
          resolve(apiClient(original))
        })
      })
    }

    original._retry = true
    isRefreshing = true
    try {
      const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, { refresh_token: refreshToken })
      setTokens(data.access_token, data.refresh_token)
      waitQueue.forEach(cb => cb(data.access_token))
      waitQueue = []
      original.headers['Authorization'] = `Bearer ${data.access_token}`
      return apiClient(original)
    } catch {
      clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  }
)

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('df_access_token', access)
  localStorage.setItem('df_refresh_token', refresh)
}

export function clearTokens() {
  localStorage.removeItem('df_access_token')
  localStorage.removeItem('df_refresh_token')
}
