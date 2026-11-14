// =============================================================================
// CYBERSLEUTH AI - Top Navigation Bar
// =============================================================================

import { Search } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { MobileSidebarToggle } from './Sidebar'

const pageTitles: Record<string, string> = {
  '/dashboard': 'Forensic Command Centre',
  '/investigations': 'Investigation Management',
  '/investigations/create': 'New Investigation',
  '/evidence': 'Evidence Vault',
  '/evidence/upload': 'Upload Evidence',
  '/deeptrace': 'DeepTrace AI — Image & Video Forensics',
  '/spytrace': 'SpyTrace AI — Android Spyware Analysis',
  '/voiceproof': 'VoiceProof AI — Audio Forensics',
  '/cybersleuth': 'CyberSleuth AI — Evidence Extraction',
  '/correlation': 'Correlation Engine',
  '/reports': 'Forensic Reports',
  '/audit-logs': 'Audit Logs',
  '/settings': 'Settings',
  '/login': 'Sign In',
  '/register': 'Create Account',
}

/** Titles for dynamic routes that need a prefix. */
function resolveTitle(pathname: string): string {
  if (pageTitles[pathname]) return pageTitles[pathname]
  if (pathname.startsWith('/investigations/')) return 'Investigation Details'
  return 'CyberSleuth AI'
}

export function TopNav({ sidebarOpen, setSidebarOpen }: { sidebarOpen: boolean; setSidebarOpen: (v: boolean) => void }) {
  const location = useLocation()
  const { user } = useAuth()

  return (
    <header className="h-14 border-b border-border bg-background/80 backdrop-blur flex items-center justify-between px-4 z-20">
      <div className="flex items-center gap-3">
        <MobileSidebarToggle onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <h1 className="font-semibold text-text-main tracking-tight text-sm md:text-base">
          {resolveTitle(location.pathname)}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-1 px-3 py-1.5 rounded-full bg-secondary border border-border/50">
          <Search size={14} className="text-text-secondary/50" />
          <input
            type="text"
            placeholder="Search evidence, cases..."
            className="bg-transparent border-none outline-none text-xs text-text-main placeholder-text-secondary/40 w-32"
          />
        </div>

        <div className="flex items-center gap-2 pl-3 border-l border-border/50">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border/50 text-xs">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            <span className="text-text-secondary">Online</span>
          </div>
          <div className="flex items-center gap-2 pl-3 border-l border-border/50">
            <div className="w-8 h-8 rounded-full bg-secondary border border-border overflow-hidden flex items-center justify-center text-xs font-semibold text-text-main">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div>
              <p className="text-xs font-semibold text-text-main">{user?.full_name || 'User'}</p>
              <p className="text-[10px] text-text-secondary/60 uppercase">{user?.role || 'investigator'}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
