// =============================================================================
// PROJECT NEXUS AI - ECHO Evidence Gap Discovery Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Layout } from '@/components/Layout'
import { echoAPI } from '@/services/api'
import { Plus } from 'lucide-react'

interface EvidenceGap {
  id: string
  gap_description: string
  suggested_evidence?: string
  priority: string
  created_at: string
}

export function EchoPage() {
  const [gaps, setGaps] = useState<EvidenceGap[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [formData, setFormData] = useState({ gap_description: '', suggested_evidence: '', priority: 'medium' as const })

  useEffect(() => {
    loadGaps()
  }, [])

  const loadGaps = async () => {
    try {
      const response = await echoAPI.listGaps('00000000-0000-0000-0000-000000000000')
      setGaps(response.data)
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load evidence gaps')
      }
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await echoAPI.createGap('00000000-0000-0000-0000-000000000000', formData)
      setShowCreate(false)
      setFormData({ gap_description: '', suggested_evidence: '', priority: 'medium' })
      loadGaps()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create evidence gap')
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">ECHO - Evidence Gap Discovery</h2>
            <p className="text-slate-400">
              Identify gaps in your evidence collection and discover what additional evidence
              may be needed for a complete investigation.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Add Gap
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span>{error}</span>
          </div>
        )}

        {showCreate && (
          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Record Evidence Gap</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="label">Gap Description</label>
                <textarea
                  value={formData.gap_description}
                  onChange={(e) => setFormData({ ...formData, gap_description: e.target.value })}
                  placeholder="Describe the evidence gap..."
                  className="input min-h-[100px]"
                />
              </div>
              <div>
                <label className="label">Suggested Evidence (optional)</label>
                <input
                  value={formData.suggested_evidence}
                  onChange={(e) => setFormData({ ...formData, suggested_evidence: e.target.value })}
                  placeholder="What evidence would fill this gap?"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Priority</label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                  className="input"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary">Record Gap</button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-4">Identified Evidence Gaps</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Description</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Suggested Evidence</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Priority</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Created</th>
                </tr>
              </thead>
              <tbody>
                {gaps.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      No evidence gaps identified yet.
                    </td>
                  </tr>
                )}
                {gaps.map((g) => (
                  <tr key={g.id} className="border-b border-slate-800">
                    <td className="py-3 text-sm text-slate-300">{g.gap_description}</td>
                    <td className="py-3 text-sm text-slate-400">{g.suggested_evidence || '—'}</td>
                    <td className="py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        g.priority === 'critical' ? 'bg-red-500/10 text-red-400' :
                        g.priority === 'high' ? 'bg-orange-500/10 text-orange-400' :
                        g.priority === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                        'bg-green-500/10 text-green-400'
                      }`}>
                        {g.priority}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-slate-500">
                      {new Date(g.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-slate-400">🔍</span>
            <h4 className="font-semibold text-slate-200">ECHO Methodology</h4>
          </div>
          <p className="text-sm text-slate-400">
            ECHO (Evidence Gap Discovery) systematically identifies what evidence is missing
            from your investigation. All gap records are timestamped and associated with your
            case for forensic traceability.
          </p>
        </div>
      </div>
    </Layout>
  )
}
