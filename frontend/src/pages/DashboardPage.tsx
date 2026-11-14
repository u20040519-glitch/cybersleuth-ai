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
import { LayoutDashboard, FileText, ShieldCheck, Image, Smartphone, Mic, Code, Activity, FileScan, Plus, Upload } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Link } from 'react-router-dom'
import { investigationsAPI } from '@/services/api'

const moduleStats = [
  { name: 'DeepTrace AI', href: '/deeptrace', icon: Image, color: 'text-primary-blue' },
  { name: 'SpyTrace AI', href: '/spytrace', icon: Smartphone, color: 'text-primary-cyan' },
  { name: 'VoiceProof AI', href: '/voiceproof', icon: Mic, color: 'text-primary-blue' },
  { name: 'CyberSleuth AI', href: '/cybersleuth', icon: Code, color: 'text-primary-cyan' },
]

export function DashboardPage() {
  const { user } = useAuth()
  const [investigations, setInvestigations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    investigationsAPI.list()
      .then((res) => {
        setInvestigations(res.data || [])
        setLoading(false)
      })
      .catch(() => {
        setDemo(true)
        setLoading(false)
      })
  }, [])

  const totalInvestigations = demo ? 4 : investigations.length
  const totalEvidence = demo ? 12 : investigations.reduce((s, i) => s + (i.evidence_count || 0), 0)
  const completedAnalyses = demo ? 8 : investigations.filter((i) => i.status === 'closed').length
  const pendingReviews = demo ? 2 : investigations.filter((i) => i.status === 'review').length

  // While the request is in flight we must not render a hard "0" — that reads as
  // a real measurement. Show a placeholder until the true value is known.
  const v = (n: number) => (loading ? '—' : n)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-text-main">Dashboard</h2>
        <p className="text-text-secondary">
          Welcome back, {user?.full_name}. Here&apos;s your forensic command centre.
        </p>
      </div>

      {/* Demo-mode disclosure */}
      {demo && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-warning/10 border border-warning/20">
          <Badge variant="warning" className="uppercase tracking-wider">
            Demo Data
          </Badge>
          <p className="text-xs text-text-secondary">
            The backend is not running, so these figures are illustrative sample values —
            not real case data.
          </p>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Investigations"
          value={v(totalInvestigations)}
          subtitle="Active cases"
          icon={FileText}
          color="text-primary-blue"
          trend={{ value: 12, label: 'vs last month', positive: true }}
        />
        <StatCard
          title="Evidence Files"
          value={v(totalEvidence)}
          subtitle="Securely stored"
          icon={FileScan}
          color="text-primary-cyan"
          trend={{ value: 5, label: 'vs last month', positive: true }}
        />
        <StatCard
          title="Completed Analyses"
          value={v(completedAnalyses)}
          subtitle="Forensic modules"
          icon={ShieldCheck}
          color="text-success"
          trend={{ value: 8, label: 'vs last month', positive: true }}
        />
        <StatCard
          title="Pending Reviews"
          value={v(pendingReviews)}
          subtitle="Awaiting supervisor"
          icon={Activity}
          color="text-warning"
          trend={{ value: -3, label: 'vs last month', positive: false }}
        />
      </div>

      {/* Quick actions + module access */}
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
            {moduleStats.map((m) => (
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
          ) : demo || investigations.length === 0 ? (
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
              {investigations.slice(0, 5).map((inv) => (
                <div
                  key={inv.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors cursor-pointer"
                  onClick={() => {}}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center text-xs font-mono text-text-secondary">
                      {inv.case_id?.slice(-4) || 'CASE'}
                    </div>
                    <div>
                      <p className="text-sm text-text-main">{inv.title}</p>
                      <p className="text-xs text-text-secondary/60">{inv.category}</p>
                    </div>
                  </div>
                  <Badge variant={inv.priority === 'critical' || inv.priority === 'high' ? 'error' : 'info'}>
                    {inv.priority}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Analysis distribution chart placeholder */}
      <Card>
        <CardHeader title="Analysis Distribution Across Modules" />
        <div className="h-64 flex items-center justify-center">
          <div className="text-text-secondary/50 text-sm">
            Charts connect to live data in Phase 2 (backend + database).
          </div>
        </div>
      </Card>
    </div>
  )
}
