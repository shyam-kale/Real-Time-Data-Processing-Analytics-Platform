import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GitBranch } from 'lucide-react'
import { authApi } from '@/services/auth'
import { useAuthStore } from '@/store/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export default function Login() {
  const [email, setEmail]       = useState('shyam@dataflow.io')
  const [password, setPassword] = useState('dataflow123')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const { setUser, setOrg }     = useAuthStore()
  const navigate                = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.login(email, password)
      const user = await authApi.me()
      setUser(user)
      const orgs = await authApi.myOrganizations()
      if (orgs.length > 0) {
        setOrg(orgs[0])
        navigate('/overview')
      } else {
        setError('No organization found for this account')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-white" />
          </div>
          <span className="text-xl font-semibold text-foreground">DataFlow</span>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-base font-semibold text-foreground mb-1">Sign in</h2>
          <p className="text-sm text-muted-foreground mb-5">Welcome back to your workspace</p>

          {error && (
            <div className="mb-4 px-3 py-2 rounded-md bg-destructive/10 border border-destructive/20 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Email" type="email" value={email}
              onChange={e => setEmail(e.target.value)} placeholder="you@company.com" required autoFocus />
            <Input label="Password" type="password" value={password}
              onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
            <Button type="submit" className="w-full" loading={loading}>Sign in</Button>
          </form>
        </div>

        <p className="text-center text-sm text-muted-foreground mt-4">
          No account?{' '}
          <Link to="/register" className="text-primary hover:underline font-medium">Create one</Link>
        </p>
      </div>
    </div>
  )
}
