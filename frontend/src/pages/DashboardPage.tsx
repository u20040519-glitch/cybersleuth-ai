// =============================================================================
// CYBERSLEUTH AI - Dashboard Page
// =============================================================================

import { useEffect, useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { StatCard } from '@/ui/StatCard'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import { Button } from '@/ui/Button'
import {
  LayoutDashboard,
  FileText,
  ShieldCheck,
  Image,
  Smartphone,
  Mic,
  Code,
  Activity,
  FileScan,
  Plus,
  Upload,
  AlertCircle,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Link, useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { dashboardAPI } from '@/services/api'
import { formatBytes } from '@/utils/format'

const moduleAccess = [
  { name: 'DeepTrace AI', href: '/deeptrace', icon: Image, color: 'text-primary-blue' },
  { name: 'SpyTrace AI', href: '/spytrace', icon: Smartphone, color: 'text-primary-cyan' },
  { name: 'VoiceProof AI', href: '/voiceproof', icon: Mic, color: 'text-primary-blue' },
  { name: 'CyberSleuth AI', href: '/cybersleuth', icon: Code, color: 'text-primary-cyan' },
]

const MODULE_LABELS: Record<string, string> = {
  deeptrace: 'DeepTrace',
  spytrace: 'SpyTrace',
  voiceproof: 'VoiceProof',
  cybersleuth: 'CyberSleuth',
}

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    dashboardAPI
      .stats()
      .then((res) => {
        if (!cancelled) {
          setStats(res.data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('The dashboard could not reach the backend. Make sure the API is running and you are signed in.')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const v = (n?: number | null) => (loading ? '—' : n ?? 0)
  const recent: any[] = stats?.recent_investigations ?? []
  const moduleRuns: Array<{ module: string; runs: number }> = Object.entries(stats?.module_runs ?? {}).map(
    ([module, runs]) => ({ module: MODULE_LABELS[module] ?? module, runs: Number(runs) }),
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-text-main">Dashboard</h2>
          <p className="text-text-secondary">
            Welcome back, {user?.full_name}. Here&apos;s your forensic command centre.
          </p>
        </div>
        <Badge variant="info" className="self-start sm:self-auto">
          Live data · {stats?.generated_at ? new Date(stats.generated_at).toLocaleTimeString() : '—'}
        </Badge>
      </div>

      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-error/10 border border-error/20">
          <AlertCircle size={18} className="text-error shrink-0" />
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Investigations"
          value={v(stats?.total_investigations)}
          subtitle="Cases in this workspace"
          icon={FileText}
          color="text-primary-blue"
        />
        <StatCard
          title="Evidence Files"
          value={v(stats?.evidence_files)}
          subtitle={stats?.total_evidence_bytes ? `${formatBytes(stats.total_evidence_bytes)} secured` : 'Securely stored'}
          icon={FileScan}
          color="text-primary-cyan"
        />
        <StatCard
          title="Completed Analyses"
          value={v(stats?.analysis_runs)}
          subtitle="Forensic module runs"
          icon={ShieldCheck}
          color="text-success"
        />
        <StatCard
          title="Pending Reviews"
          value={v(stats?.pending_reviews)}
          subtitle="Awaiting supervisor"
          icon={Activity}
          color="text-warning"
        />
      </div>

      {/* Quick actions + module access + recent investigations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick actions */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Quick Actions" />
            <div className="space-y-3">
              <Button variant="primary" className="w-full" asChild>
                <Link to="/investigations/create">
                  <Plus size={16} /> New Investigation
                </Link>
              </Button>
              <Button variant="cyan" className="w-full" asChild>
                <Link to="/evidence/upload">
                  <Upload size={16} /> Upload Evidence
                </Link>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <Link to="/investigations">
                  <LayoutDashboard size={16} /> View All Investigations
                </Link>
              </Button>
            </div>
          </Card>
        </div>

        {/* Module access */}
        <Card>
          <CardHeader title="Forensic Modules" subtitle="All modules share the same investigation context" />
          <div className="space-y-3">
            {moduleAccess.map((m) => (
              <Link
                key={m.name}
                to={m.href}
                className="flex items-center gap-3 px-4 py-3 rounded-lg bg-secondary border border-border hover:bg-[#1f2d44] hover:border-primary-blue/50 transition-colors group"
              >
                <m.icon size={18} className={m.color} />
                <span className="text-sm text-text-main group-hover:text-primary-cyan transition-colors">
                  {m.name}
                </span>
              </Link>
            ))}
          </div>
        </Card>

        {/* Recent investigations */}
        <Card>
          <CardHeader title="Recent Investigations" />
          {loading ? (
            <div className="h-48 flex items-center justify-center">
              <LoadingSpinner size="md" />
            </div>
          ) : recent.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No investigations yet"
              description="Create your first investigation to get started."
              action={
                <Button variant="primary" asChild>
                  <Link to="/investigations/create">
                    <Plus size={16} /> Create Investigation
                  </Link>
                </Button>
              }
            />
          ) : (
            <div className="space-y-2">
              {recent.map((inv) => (
                <button
                  key={inv.id}
                  onClick={() => navigate(`/investigations/${inv.id}`)}
                  className="w-full flex items-center justify-between p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors text-left"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center text-xs font-mono text-text-secondary shrink-0">
                      {(inv.case_id || 'CASE').slice(-4)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm text-text-main truncate">{inv.title}</p>
                      <p className="text-xs text-text-secondary/60">{inv.category}</p>
                    </div>
                  </div>
                  <Badge variant={inv.priority === 'critical' || inv.priority === 'high' ? 'error' : 'info'}>
                    {inv.priority}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Analysis distribution across modules */}
      <Card>
        <CardHeader
          title="Analysis Distribution Across Modules"
          subtitle="Completed module runs, counted from the database"
        />
        {loading ? (
          <div className="h-64 flex items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        ) : moduleRuns.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-text-secondary/50 text-sm">
            No forensic analyses have been run yet. Upload evidence and use a module to begin.
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={moduleRuns} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2d44" />
                <XAxis dataKey="module" stroke="#91A4BE" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} stroke="#91A4BE" tick={{ fontSize: 12 }} />
                <Tooltip
                  cursor={{ fill: 'rgba(59, 130, 246, 0.08)' }}
                  contentStyle={{
                    background: '#111B2B',
                    border: '1px solid #1f2d44',
                    borderRadius: 8,
                    color: '#E6F0FF',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="runs" name="Analysis runs" fill="#3B82F6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  )
}
