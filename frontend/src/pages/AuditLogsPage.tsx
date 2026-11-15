// =============================================================================
// CYBERSLEUTH AI - Audit Logs Page
// =============================================================================

import { useEffect, useState } from 'react'
import { Activity, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/ui/Button'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import { auditAPI } from '@/services/api'

const PAGE_SIZE = 25

function actionVariant(action: string): string {
  const key = (action || '').toLowerCase()
  if (['upload', 'analyze', 'correlate', 'generate_report', 'download_report'].includes(key)) return 'text-primary-blue'
  if (['login', 'register'].includes(key)) return 'text-success'
  if (['login_failed', 'upload_rejected', 'access_denied'].includes(key)) return 'text-error'
  if (['logout'].includes(key)) return 'text-warning'
  return 'text-text-secondary'
}

export function AuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    auditAPI
      .list({ limit: PAGE_SIZE, offset })
      .then((res) => {
        if (!cancelled) {
          setLogs(res.data || [])
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Audit logs could not be loaded. Check that the API is running, then retry.')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [offset])

  const filtered = logs.filter((log) => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return (
      String(log.user_name || '').toLowerCase().includes(q) ||
      String(log.action || '').toLowerCase().includes(q) ||
      String(log.resource || '').toLowerCase().includes(q) ||
      String(log.resource_id || '').toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">Audit Logs</h2>
        <p className="text-text-secondary">
          Immutable record of all user actions, evidence access, and system events.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative w-72">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary/50" />
          <input
            type="text"
            placeholder="Filter by user, action or resource..."
            className="input pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Filter audit logs"
          />
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <Button variant="ghost" size="sm" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0}>
            <ChevronLeft size={14} />
          </Button>
          <span className="text-xs text-text-secondary">Rows {offset + 1}–{offset + logs.length}</span>
          <Button variant="ghost" size="sm" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={logs.length < PAGE_SIZE}>
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-error">{error}</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse border-border">
          <thead>
            <tr className="border-b border-border">
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Timestamp</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">User</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Action</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Resource</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">IP</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="h-40 text-center">
                  <LoadingSpinner size="md" />
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="h-32 text-center text-sm text-text-secondary/60">
                  No audit entries match this filter.
                </td>
              </tr>
            ) : (
              filtered.map((log) => (
                <tr key={log.id} className="border-b border-border/50 hover:bg-secondary/30 transition-colors">
                  <td className="py-3 text-xs font-mono text-text-secondary whitespace-nowrap">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                  </td>
                  <td className="py-3 text-xs text-text-main">{log.user_name}</td>
                  <td className={`py-3 text-xs font-semibold ${actionVariant(log.action)}`}>{log.action}</td>
                  <td className="py-3 text-xs text-text-secondary">
                    <span className="font-medium text-text-main">{log.resource}</span>
                    {log.resource_id ? <span className="font-mono text-[10px] block text-text-secondary/60">{log.resource_id}</span> : null}
                  </td>
                  <td className="py-3 text-xs font-mono text-text-secondary/60">{log.ip_address ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="p-4 rounded-lg bg-secondary border border-border">
        <p className="text-xs text-text-secondary/60">
          <Activity size={14} className="mr-1 inline" /> Audit logs are written once and never updated or deleted. They are enforced append-only at the database layer (no UPDATE/DELETE grant or policy).
        </p>
      </div>
    </div>
  )
}
