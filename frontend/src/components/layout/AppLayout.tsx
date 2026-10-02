import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/store/auth'
import { useTheme } from '@/utils/theme'
import {
  LayoutDashboard, BarChart3, Database, GitBranch, Play, ShieldCheck,
  FileText, Bell, Users, Key, Activity, Settings, LogOut, Sun, Moon,
  Search, ChevronDown, Building2, Menu, X
} from 'lucide-react'

const NAV = [
  { label: 'WORKSPACE', items: [
    { to: '/overview',  icon: LayoutDashboard, label: 'Overview' },
    { to: '/analytics', icon: BarChart3,        label: 'Analytics' },
    { to: '/datasets',  icon: Database,         label: 'Datasets' },
    { to: '/pipelines', icon: GitBranch,        label: 'Pipelines' },
    { to: '/runs',      icon: Play,             label: 'Runs' },
    { to: '/quality',   icon: ShieldCheck,      label: 'Data Quality' },
  ]},
  { label: 'EXPLORE', items: [
    { to: '/explorer',  icon: Search,  label: 'Data Explorer' },
    { to: '/reports',   icon: FileText, label: 'Reports' },
    { to: '/alerts',    icon: Bell,    label: 'Alerts' },
  ]},
  { label: 'MANAGEMENT', items: [
    { to: '/team',      icon: Users,    label: 'Team' },
    { to: '/api-keys',  icon: Key,      label: 'API Keys' },
    { to: '/activity',  icon: Activity, label: 'Activity' },
    { to: '/settings',  icon: Settings, label: 'Settings' },
  ]},
]

function NavItem({ to, icon: Icon, label, collapsed }: { to: string; icon: React.ElementType; label: string; collapsed: boolean }) {
  const { pathname } = useLocation()
  const active = pathname === to || pathname.startsWith(to + '/')
  return (
    <Link
      to={to}
      title={collapsed ? label : undefined}
      className={cn(
        'flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors group',
        active
          ? 'bg-sidebar-active text-sidebar-active-foreground font-medium'
          : 'text-sidebar-foreground hover:bg-white/5 hover:text-white'
      )}
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  )
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, org, logout } = useAuthStore()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className={cn(
        'flex-shrink-0 flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-200',
        collapsed ? 'w-14' : 'w-52',
        'hidden md:flex'
      )}>
        {/* Logo */}
        <div className={cn('flex items-center gap-2 px-4 h-12 border-b border-sidebar-border', collapsed && 'justify-center')}>
          <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center flex-shrink-0">
            <GitBranch className="w-3.5 h-3.5 text-white" />
          </div>
          {!collapsed && <span className="text-white font-semibold text-sm tracking-tight">DataFlow</span>}
        </div>

        {/* Org selector */}
        {!collapsed && org && (
          <div className="px-3 py-2 border-b border-sidebar-border">
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-white/5 cursor-pointer">
              <Building2 className="w-3.5 h-3.5 text-sidebar-foreground flex-shrink-0" />
              <span className="text-xs text-sidebar-foreground truncate flex-1">{org.name}</span>
              <ChevronDown className="w-3 h-3 text-sidebar-foreground" />
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 space-y-4 px-2">
          {NAV.map(section => (
            <div key={section.label}>
              {!collapsed && (
                <p className="px-3 mb-1 text-2xs font-semibold text-sidebar-foreground/50 uppercase tracking-wider">
                  {section.label}
                </p>
              )}
              <div className="space-y-0.5">
                {section.items.map(item => (
                  <NavItem key={item.to} {...item} collapsed={collapsed} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className={cn('border-t border-sidebar-border p-2 space-y-0.5')}>
          <button
            onClick={toggle}
            className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm text-sidebar-foreground hover:bg-white/5 transition-colors"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {!collapsed && <span>Toggle theme</span>}
          </button>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm text-sidebar-foreground hover:bg-white/5 hover:text-red-400 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            {!collapsed && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-12 flex items-center gap-3 px-4 border-b border-border bg-card flex-shrink-0">
          <button
            className="hidden md:flex text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setCollapsed(c => !c)}
          >
            <Menu className="w-4 h-4" />
          </button>
          <button
            className="md:hidden text-muted-foreground"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Search */}
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                placeholder="Search anything..."
                className="w-full h-7 pl-8 pr-3 rounded-md border border-border bg-muted text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-2xs text-muted-foreground bg-background border border-border px-1 rounded">⌘K</kbd>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-semibold">
              {user?.full_name?.[0] ?? 'U'}
            </div>
            <span className="text-sm text-foreground hidden sm:block">{user?.full_name}</span>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-52 bg-sidebar flex flex-col">
            <div className="flex items-center justify-between px-4 h-12 border-b border-sidebar-border">
              <span className="text-white font-semibold text-sm">DataFlow</span>
              <button onClick={() => setMobileOpen(false)}><X className="w-4 h-4 text-sidebar-foreground" /></button>
            </div>
            <nav className="flex-1 overflow-y-auto py-3 space-y-4 px-2">
              {NAV.map(section => (
                <div key={section.label}>
                  <p className="px-3 mb-1 text-2xs font-semibold text-sidebar-foreground/50 uppercase tracking-wider">{section.label}</p>
                  <div className="space-y-0.5">
                    {section.items.map(item => (
                      <NavItem key={item.to} {...item} collapsed={false} />
                    ))}
                  </div>
                </div>
              ))}
            </nav>
          </aside>
        </div>
      )}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between px-6 py-5 border-b border-border">
      <div>
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
