// =============================================================================
// CYBERSLEUTH AI - Investigations Management Page
// =============================================================================

import { useEffect, useState } from 'react'

import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'
import { FileText, Search, Filter, Plus, ChevronRight } from 'lucide-react'
import { investigationsAPI } from '@/services/api'

const STATUS_FILTERS = ['all', 'draft', 'active', 'review', 'closed', 'archived']

function priorityVariant(priority: string): 'success' | 'warning' | 'error' | 'info' {
  if (priority === 'critical') return 'error'
  if (priority === 'high') return 'error'
  if (priority === 'medium') return 'warning'
  if (priority === 'low') return 'success'
  return 'info'
}

function statusVariant(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (status === 'active') return 'info'
  if (status === 'review') return 'warning'
  if (status === 'closed') return 'success'
  if (status === 'archived') return 'error'
  return 'default'
}

export function InvestigationsPage() {
  const [investigations, setInvestigations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [demo, setDemo] = useState(false)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

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

  const filtered = investigations.filter((inv) => {
    const matchSearch =
      inv.title.toLowerCase().includes(search.toLowerCase()) ||
      (inv.case_id || '').toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'all' || inv.status === filter
    return matchSearch && matchFilter
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-text-main">Investigations</h2>
          <p className="text-text-secondary">
            Manage cases, assign investigators, and track evidence.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="primary" asChild>
            <a href="/investigations/create">
              <Plus size={16} /> New Investigation
            </a>
          </Button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary/50" />
          <Input
            label=""
            placeholder="Search cases by title or case ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="relative">
          <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary/50 pointer-events-none" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input pl-9 min-w-[170px]"
            aria-label="Filter by status"
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All statuses' : s}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse border-border">
          <thead>
            <tr className="border-b border-border">
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">Case ID</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">Title</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">Category</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">Priority</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">Status</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">Evidence</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="h-48 text-center">
                  <LoadingSpinner size="md" />
                </td>
              </tr>
            ) : demo || filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="h-64 text-center">
                  <EmptyState
                    icon={FileText}
                    title={demo ? 'Demo mode — no investigations' : 'No investigations found'}
                    description={
                      demo
                        ? 'Connect the backend in Phase 2 to see real investigation data.'
                        : 'Try adjusting your search or filters.'
                    }
                    action={
                      <Button variant="primary" asChild>
                        <a href="/investigations/create">
                          <Plus size={16} /> Create Investigation
                        </a>
                      </Button>
                    }
                  />
                </td>
              </tr>
            ) : (
              filtered.map((inv) => (
                <tr
                  key={inv.id}
                  className="border-b border-border/50 hover:bg-secondary/30 transition-colors group cursor-pointer"
                >
                  <td className="py-4 text-xs font-mono text-text-secondary">
                    {inv.case_id || 'CASE-....'}
                  </td>
                  <td className="py-4 text-sm text-text-main">{inv.title}</td>
                  <td className="py-4 text-xs text-text-secondary">{inv.category}</td>
                  <td className="py-4">
                    <Badge variant={priorityVariant(inv.priority || 'low')}>
                      {inv.priority}
                    </Badge>
                  </td>
                  <td className="py-4">
                    <Badge variant={statusVariant(inv.status || 'draft')}>
                      {inv.status}
                    </Badge>
                  </td>
                  <td className="py-4 text-xs text-text-secondary">{inv.evidence_count || 0}</td>
                  <td className="py-4 text-right">
                    <Button variant="ghost" size="sm" className="text-text-secondary/60 hover:text-primary-cyan" asChild>
                      <a href={`/investigations/${inv.id}`}>
                        <ChevronRight size={14} />
                      </a>
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
