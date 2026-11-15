// =============================================================================
// CYBERSLEUTH AI - Settings Page
// =============================================================================
// Shows the real signed-in identity and the real security model of this
// deployment. There is deliberately no fake "save" flow: profile fields are
// read-only (accounts are provisioned by an administrator) and password
// changes are not exposed by the backend, so this page does not pretend they
// exist.
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Button } from '@/ui/Button'
import { Badge } from '@/ui/Badge'
import { Users, Shield, LogOut, Info } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useNavigate } from 'react-router-dom'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'profile' | 'security'>('profile')
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const tabs = [
    { id: 'profile' as const, label: 'Profile', icon: Users },
    { id: 'security' as const, label: 'Security', icon: Shield },
  ]

  const initials = (user?.full_name || user?.email || '?')
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">Settings</h2>
        <p className="text-text-secondary">
          Your account and the security model of this deployment.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-3">
          <div className="flex flex-col h-full">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-blue/10 text-primary-blue border border-primary-blue/20'
                      : 'text-text-secondary hover:text-text-main hover:bg-secondary'
                  }`}
                >
                  <tab.icon size={16} className="mr-2" />
                  {tab.label}
                </button>
              ))}
            </nav>
            <div className="mt-auto p-4 rounded-lg bg-secondary/50 border border-border/50">
              <p className="text-xs text-text-secondary/60">
                Role: <span className="capitalize">{user?.role ?? 'investigator'}</span>
              </p>
              <p className="text-xs text-text-secondary">Platform: CyberSleuth AI v1.0.0</p>
            </div>
          </div>
        </div>

        <div className="lg:col-span-9">
          {activeTab === 'profile' && (
            <Card>
              <CardHeader title="Profile" subtitle="Read-only. Accounts are provisioned by an administrator." />
              <div className="flex items-center gap-4 mb-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-blue to-primary-cyan flex items-center justify-center text-xl font-bold text-[#080D18]">
                  {initials}
                </div>
                <div>
                  <p className="text-lg font-semibold text-text-main">{user?.full_name}</p>
                  <Badge variant="info" className="mt-1 capitalize">{user?.role}</Badge>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Full name</p>
                  <p className="text-sm text-text-main">{user?.full_name}</p>
                </div>
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Email</p>
                  <p className="text-sm text-text-main">{user?.email}</p>
                </div>
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Account ID</p>
                  <p className="text-[10px] font-mono text-text-main break-all">{user?.id}</p>
                </div>
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Role</p>
                  <p className="text-sm text-text-main capitalize">
                    {user?.role === 'supervisor'
                      ? 'Supervisor — can see every case and approve findings'
                      : 'Investigator — access limited to cases you own or are assigned to'}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'security' && (
            <Card>
              <CardHeader title="Security" subtitle="How this deployment protects your session and the evidence." />
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs font-semibold text-text-main mb-1">Authentication</p>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    Passwords are hashed with Argon2id. Sessions use short-lived JWT access tokens with a separate
                    refresh token. Tokens are never exposed to third-party origins.
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs font-semibold text-text-main mb-1">Evidence protection</p>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    Every evidence original is SHA-256 fingerprinted at intake, stored in an immutable bucket, and
                    tracked by an append-only, hash-chained chain of custody. Row Level Security in the database
                    restricts every table to the cases you own or are assigned to — it is enforced by PostgreSQL
                    itself, not by the UI.
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs font-semibold text-text-main mb-1">Password changes</p>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    This deployment does not self-serve password resets. Contact your platform administrator to
                    rotate your credentials.
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-warning/5 border border-warning/20 flex items-start gap-2">
                  <Info size={16} className="text-warning mt-0.5 shrink-0" />
                  <p className="text-xs text-warning leading-relaxed">
                    Two-factor authentication is not enabled in this build. Sensitive operations are protected by
                    short token lifetimes and per-request authorisation checks instead.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={async () => {
                    await logout()
                    navigate('/login', { replace: true })
                  }}
                >
                  <LogOut size={16} className="mr-2" /> Sign out of this device
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
