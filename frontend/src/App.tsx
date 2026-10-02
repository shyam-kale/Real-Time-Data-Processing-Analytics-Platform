import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/services/auth'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageLoader } from '@/components/ui/Spinner'

// Auth
import Login    from '@/pages/auth/Login'
import Register from '@/pages/auth/Register'

// App pages
import Overview       from '@/pages/overview/Overview'
import Analytics      from '@/pages/analytics/Analytics'
import Datasets       from '@/pages/datasets/Datasets'
import DatasetDetail  from '@/pages/datasets/DatasetDetail'
import DataExplorer   from '@/pages/explorer/DataExplorer'
import Pipelines      from '@/pages/pipelines/Pipelines'
import PipelineDetail from '@/pages/pipelines/PipelineDetail'
import PipelineBuilder from '@/pages/pipelines/PipelineBuilder'
import Runs           from '@/pages/runs/Runs'
import RunDetail      from '@/pages/runs/RunDetail'
import DataQuality    from '@/pages/quality/DataQuality'
import Reports        from '@/pages/reports/Reports'
import Alerts         from '@/pages/alerts/Alerts'
import Team           from '@/pages/team/Team'
import ApiKeys        from '@/pages/apikeys/ApiKeys'
import Activity       from '@/pages/activity/Activity'
import Settings       from '@/pages/settings/Settings'

// Restore session on page refresh
function SessionRestorer({ children }: { children: React.ReactNode }) {
  const { setUser, setOrg, user } = useAuthStore()
  const [checking, setChecking] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('df_access_token')
    if (!token) { setChecking(false); return }
    if (user) { setChecking(false); return }

    authApi.me()
      .then(async (u) => {
        setUser(u)
        const orgs = await authApi.myOrganizations()
        if (orgs.length > 0) setOrg(orgs[0])
      })
      .catch(() => {
        localStorage.removeItem('df_access_token')
        localStorage.removeItem('df_refresh_token')
        navigate('/login')
      })
      .finally(() => setChecking(false))
  }, [])

  if (checking) return <PageLoader />
  return <>{children}</>
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('df_access_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Shell({ children }: { children: React.ReactNode }) {
  return <RequireAuth><AppLayout>{children}</AppLayout></RequireAuth>
}

export default function App() {
  return (
    <SessionRestorer>
      <Routes>
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route path="/overview"           element={<Shell><Overview /></Shell>} />
        <Route path="/analytics"          element={<Shell><Analytics /></Shell>} />
        <Route path="/datasets"           element={<Shell><Datasets /></Shell>} />
        <Route path="/datasets/:id"       element={<Shell><DatasetDetail /></Shell>} />
        <Route path="/explorer"           element={<Shell><DataExplorer /></Shell>} />
        <Route path="/quality"            element={<Shell><DataQuality /></Shell>} />
        <Route path="/pipelines"          element={<Shell><Pipelines /></Shell>} />
        <Route path="/pipelines/builder"  element={<Shell><PipelineBuilder /></Shell>} />
        <Route path="/pipelines/builder/:id" element={<Shell><PipelineBuilder /></Shell>} />
        <Route path="/pipelines/:id"      element={<Shell><PipelineDetail /></Shell>} />
        <Route path="/runs"               element={<Shell><Runs /></Shell>} />
        <Route path="/runs/:id"           element={<Shell><RunDetail /></Shell>} />
        <Route path="/reports"            element={<Shell><Reports /></Shell>} />
        <Route path="/alerts"             element={<Shell><Alerts /></Shell>} />
        <Route path="/team"               element={<Shell><Team /></Shell>} />
        <Route path="/api-keys"           element={<Shell><ApiKeys /></Shell>} />
        <Route path="/activity"           element={<Shell><Activity /></Shell>} />
        <Route path="/settings"           element={<Shell><Settings /></Shell>} />

        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </SessionRestorer>
  )
}
