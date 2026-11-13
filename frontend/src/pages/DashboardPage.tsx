// =============================================================================
// PROJECT NEXUS AI - Dashboard Page
// =============================================================================

import { useAuth } from '@/context/AuthContext'
import { Layout } from '@/components/Layout'
import { LayoutDashboard, FileText, ShieldAlert, BarChart3, FileScan } from 'lucide-react'

const statCards = [
  { title: 'Active Cases', value: '12', icon: FileText, color: 'text-nexus-accent' },
  { title: 'Evidence Files', value: '45', icon: FileScan, color: 'text-blue-400' },
  { title: 'Evidence Gaps', value: '3', icon: ShieldAlert, color: 'text-orange-400' },
  { title: 'Reports Generated', value: '8', icon: BarChart3, color: 'text-green-400' },
]

const recentCases = [
  { case_number: 'CASE-2026-001', title: 'Digital Evidence Analysis', status: 'Active', updated: '2 hours ago' },
  { case_number: 'CASE-2026-002', title: 'Network Forensics', status: 'Closed', updated: '1 day ago' },
  { case_number: 'CASE-2026-003', title: 'Mobile Device Extraction', status: 'Draft', updated: '3 days ago' },
]

export function DashboardPage() {
  const { user } = useAuth()

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Dashboard</h2>
          <p className="text-slate-400">
            Welcome back, {user?.full_name}. Here&rsquo;s an overview of your investigations.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat) => (
            <div key={stat.title} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">{stat.title}</p>
                  <p className="text-2xl font-bold text-white">{stat.value}</p>
                </div>
                <div className="p-2 bg-slate-800 rounded-lg">
                  <stat.icon size={20} className={stat.color} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Recent Cases */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-200">Recent Cases</h3>
            <a href="/cases" className="text-sm text-nexus-accent hover:underline">
              View all cases
            </a>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Case Number</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Title</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Status</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Updated</th>
                </tr>
              </thead>
              <tbody>
                {recentCases.map((c) => (
                  <tr key={c.case_number} className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 text-sm text-slate-300">{c.case_number}</td>
                    <td className="py-3 text-sm text-slate-300">{c.title}</td>
                    <td className="py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        c.status === 'Active' ? 'bg-green-500/10 text-green-400' :
                        c.status === 'Closed' ? 'bg-slate-500/10 text-slate-400' :
                        'bg-yellow-500/10 text-yellow-400'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-slate-500">{c.updated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button className="btn-secondary flex items-center gap-2 py-3">
              <LayoutDashboard size={18} /> New Case
            </button>
            <button className="btn-secondary flex items-center gap-2 py-3">
              <FileScan size={18} /> Upload Evidence
            </button>
            <button className="btn-secondary flex items-center gap-2 py-3">
              <ShieldAlert size={18} /> ECHO Analysis
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}
