import { useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { useTheme } from '@/utils/theme'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Sun, Moon, User, Building2 } from 'lucide-react'
import { cn } from '@/utils/cn'

export default function Settings() {
  const { user, org } = useAuthStore()
  const { theme, setTheme } = useTheme()
  const [saved, setSaved] = useState(false)

  const handleSave = () => { setSaved(true); setTimeout(() => setSaved(false), 2000) }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Manage your profile and workspace preferences" />
      <div className="p-6 space-y-5 max-w-2xl">

        {/* Profile */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><User className="w-4 h-4" />Profile</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xl font-semibold">
                {user?.full_name?.[0] ?? 'U'}
              </div>
              <div>
                <p className="font-medium text-foreground">{user?.full_name}</p>
                <p className="text-sm text-muted-foreground">{user?.email}</p>
              </div>
            </div>
            <Input label="Full name" defaultValue={user?.full_name ?? ''} />
            <Input label="Email" type="email" defaultValue={user?.email ?? ''} disabled />
            <div className="flex justify-end">
              <Button size="sm" onClick={handleSave}>{saved ? '✓ Saved' : 'Save changes'}</Button>
            </div>
          </CardContent>
        </Card>

        {/* Organization */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="w-4 h-4" />Organization</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Input label="Organization name" defaultValue={org?.name ?? ''} />
            <Input label="Slug" defaultValue={org?.slug ?? ''} disabled hint="Unique identifier — cannot be changed" />
            <div className="flex justify-end">
              <Button size="sm" onClick={handleSave}>{saved ? '✓ Saved' : 'Save changes'}</Button>
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader><CardTitle>Appearance</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">Choose your preferred color scheme</p>
            <div className="flex gap-3">
              {(['light','dark'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  className={cn(
                    'flex-1 flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors',
                    theme === t ? 'border-primary' : 'border-border hover:border-border/80'
                  )}
                >
                  {t === 'light' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                  <span className="text-sm font-medium capitalize">{t}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Danger zone */}
        <Card>
          <CardHeader><CardTitle className="text-destructive">Danger zone</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-border">
              <div>
                <p className="text-sm font-medium">Delete account</p>
                <p className="text-xs text-muted-foreground">Permanently delete your account and all data</p>
              </div>
              <Button variant="destructive" size="sm" onClick={() => alert('Contact support to delete your account')}>Delete account</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
