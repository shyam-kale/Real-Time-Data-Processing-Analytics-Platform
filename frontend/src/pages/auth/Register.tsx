import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GitBranch } from 'lucide-react'
import { authApi } from '@/services/auth'
import { useAuthStore } from '@/store/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export default function Register() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', org_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setUser, setOrg } = useAuthStore()
  const navigate = useNavigate()

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.register(form)
      const user = await authApi.me()
      setUser(user)
      const orgs = await authApi.myOrganizations()
      if (orgs[0]) setOrg(orgs[0])
      navigate('/overview')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Registration failed')
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
          <h2 className="text-base font-semibold text-foreground mb-1">Create account</h2>
          <p className="text-sm text-muted-foreground mb-5">Set up your DataFlow workspace</p>

          {error && (
            <div className="mb-4 px-3 py-2 rounded-md bg-destructive/10 border border-destructive/20 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Full name" value={form.full_name} onChange={e => set('full_name', e.target.value)} placeholder="Shyam Kumar" required />
            <Input label="Work email" type="email" value={form.email} onChange={e => set('email', e.target.value)} placeholder="you@company.com" required />
            <Input label="Organization name" value={form.org_name} onChange={e => set('org_name', e.target.value)} placeholder="Acme Corp" required />
            <Input label="Password" type="password" value={form.password} onChange={e => set('password', e.target.value)} placeholder="Min 8 characters" required minLength={8} />
            <Button type="submit" className="w-full" loading={loading}>
              Create account
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-muted-foreground mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
