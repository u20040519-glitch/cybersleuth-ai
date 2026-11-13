// =============================================================================
// PROJECT NEXUS AI - Layout Component
// =============================================================================
// Main application layout with sidebar navigation.
// =============================================================================

import { useState } from 'react'
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  FileScan,
  Users,
  Settings,
  Activity,
  Menu,
  ChevronLeft,
  ShieldCheck,
  ShieldAlert,
  Lock,
} from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Cases', href: '/cases', icon: FileText },
  { name: 'ECHO - Evidence Gaps', href: '/echo', icon: ShieldAlert },
  { name: 'MOSAIC - Scenarios', href: '/mosaic', icon: BarChart3 },
  { name: 'TIMEGLASS - Timeline', href: '/timeglass', icon: Activity },
  { name: 'Evidence', href: '/evidence', icon: FileScan },
  { name: 'AI Assistant', href: '/chatbot', icon: ShieldCheck },
  { name: 'Reports', href: '/reports', icon: FileText },
]

const adminNavigation = [
  { name: 'Users', href: '/admin/users', icon: Users },
  { name: 'Settings', href: '/admin/settings', icon: Settings },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, logout } = useAuth()
  const location = useLocation()

  const isSidebarCollapsed = window.innerWidth < 768 && !sidebarOpen

  return (
    <div className="flex h-screen overflow-hidden bg-nexus-dark">
      {/* Mobile Overlay */}
      {sidebarOpen && window.innerWidth < 768 && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full w-64 bg-slate-900 border-r border-slate-700 z-30 transform transition-transform duration-300 ${
          isSidebarCollapsed ? '-translate-x-full' : 'translate-x-0'
        } lg:relative lg:translate-x-0`}
      >
        <div className="flex items-center justify-between h-12 px-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-nexus-accent rounded-lg flex items-center justify-center text-nexus-dark font-bold text-xs">
              N
            </div>
            {!isSidebarCollapsed && (
              <span className="font-bold text-lg tracking-tighter">NEXUS AI</span>
            )}
          </div>
          {window.innerWidth < 768 && (
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-slate-400 hover:text-white"
              aria-label="Close sidebar"
            >
              <ChevronLeft size={20} />
            </button>
          )}
        </div>

        <nav className="mt-4 px-3 space-y-1">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-3">
            Investigation
          </h2>
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-nexus-accent/10 text-nexus-accent border border-nexus-accent/20'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon size={18} />
                {!isSidebarCollapsed && <span>{item.name}</span>}
              </Link>
            )
          })}

          {user?.role === 'admin' && (
            <>
              <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mt-6 mb-3">
                Administration
              </h2>
              {adminNavigation.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-nexus-accent/10 text-nexus-accent border border-nexus-accent/20'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    <Icon size={18} />
                    {!isSidebarCollapsed && <span>{item.name}</span>}
                  </Link>
                )
              })}
            </>
          )}
        </nav>

        <div className="absolute bottom-0 w-full p-3 border-t border-slate-700">
          <button
            onClick={logout}
            className="flex items-center gap-3 w-full px-3 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 rounded-lg transition-colors"
          >
            <Lock size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`flex-1 flex flex-col overflow-hidden ${isSidebarCollapsed ? 'lg:pl-0' : 'lg:pl-64'}`}>
        {/* Top Bar */}
        <header className="h-12 border-b border-slate-700 bg-slate-900/50 backdrop-blur flex items-center justify-between px-4 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-slate-400 hover:text-white lg:hidden"
              aria-label="Toggle sidebar"
            >
              <Menu size={20} />
            </button>
            <h1 className="font-semibold text-slate-200">{getPageTitle(location.pathname)}</h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-slate-700 text-xs">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-slate-300">Online</span>
            </div>
            <div className="flex items-center gap-2 pl-3 border-l border-slate-700">
              <span className="text-sm text-slate-300 font-medium">{user?.full_name}</span>
              <span className="text-xs text-slate-500 uppercase">{user?.role}</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}

function getPageTitle(pathname: string): string {
  const titles: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/cases': 'Investigation Cases',
    '/echo': 'ECHO - Evidence Gap Discovery',
    '/mosaic': 'MOSAIC - Scenario Reconstruction',
    '/timeglass': 'TIMEGLASS - Temporal Analysis',
    '/evidence': 'Evidence Repository',
    '/chatbot': 'NEXUS AI Assistant',
    '/reports': 'Forensic Reports',
    '/admin/users': 'User Management',
    '/admin/settings': 'System Settings',
  }
  return titles[pathname] || 'PROJECT NEXUS AI'
}
