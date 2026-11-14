// =============================================================================
// CYBERSLEUTH AI - Sidebar Navigation
// =============================================================================

import { useState } from 'react'
import {
  LayoutDashboard,
  FileText,
  Image,
  Smartphone,
  Mic,
  Code,
  Share,
  FileScan,
  Activity,
  Settings,
  Menu,
  ChevronLeft,
  BarChart3,
  Lock,
} from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/utils/cn'

interface NavItem {
  name: string
  href: string
  icon: React.ElementType
}

const mainNavigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Investigations', href: '/investigations', icon: FileText },
  { name: 'Evidence Vault', href: '/evidence', icon: FileScan },
  { name: 'DeepTrace AI', href: '/deeptrace', icon: Image },
  { name: 'SpyTrace AI', href: '/spytrace', icon: Smartphone },
  { name: 'VoiceProof AI', href: '/voiceproof', icon: Mic },
  { name: 'CyberSleuth AI', href: '/cybersleuth', icon: Code },
  { name: 'Correlation Engine', href: '/correlation', icon: Share },
  { name: 'Reports', href: '/reports', icon: BarChart3 },
  { name: 'Audit Logs', href: '/audit-logs', icon: Activity },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const { logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()
  const navigate = useNavigate()

  const isMobileCollapsed = window.innerWidth < 768 && !sidebarOpen

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <aside
      className={`fixed left-0 top-0 h-full z-30 transform transition-transform duration-300 ${
        collapsed || isMobileCollapsed ? '-translate-x-full' : 'translate-x-0'
      } lg:relative lg:translate-x-0 w-64 bg-sidebar border-r border-border`}
    >
      <div className="flex items-center justify-between h-14 px-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-blue to-primary-cyan flex items-center justify-center text-text-main font-bold text-xs shadow-glow-blue">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          {!collapsed && !isMobileCollapsed && (
            <span className="font-bold text-lg tracking-tighter text-text-main">
              CyberSleuth<span className="text-primary-cyan"> AI</span>
            </span>
          )}
        </div>
        {window.innerWidth < 768 && (
          <button
            onClick={() => setSidebarOpen(false)}
            className="text-text-secondary/60 hover:text-text-main"
            aria-label="Close sidebar"
          >
            <ChevronLeft size={20} />
          </button>
        )}
      </div>

      <nav className="mt-4 px-3 space-y-1">
        {mainNavigation.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-primary-blue/10 text-primary-blue border border-primary-blue/20'
                  : 'text-text-secondary hover:bg-secondary hover:text-text-main',
              )}
            >
              <Icon size={17} />
              {!collapsed && !isMobileCollapsed && <span>{item.name}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="absolute bottom-0 w-full p-3 border-t border-border/50">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-error/90 hover:bg-error/10 hover:text-error rounded-lg transition-colors"
        >
          <Lock size={17} />
          <span>Logout</span>
        </button>
      </div>

      {window.innerWidth < 768 && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </aside>
  )
}

export function MobileSidebarToggle({ onToggle }: { onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className="text-text-secondary/60 hover:text-text-main lg:hidden p-2"
      aria-label="Toggle sidebar"
    >
      <Menu size={20} />
    </button>
  )
}
