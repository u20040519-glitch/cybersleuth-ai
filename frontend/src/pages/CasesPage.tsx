// =============================================================================
// PROJECT NEXUS AI - Cases Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { casesAPI, CaseItem } from '@/services/api'
import { Plus, Loader2, AlertCircle } from 'lucide-react'

export function CasesPage() {
  const [cases, setCases] = useState<CaseItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [formData, setFormData] = useState({ case_number: '', title: '', description: '' })

  useEffect(() => {
    loadCases()
  }, [])

  const loadCases = async () => {
    try {
      setLoading(true)
      const response = await casesAPI.list()
      setCases(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load cases')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await casesAPI.create(formData)
      setShowCreate(false)
      setFormData({ case_number: '', title: '', description: '' })
      loadCases()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create case')
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex h-full items-center justify-center">
          <Loader2 size={24} className="animate-spin" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Investigation Cases</h2>
            <p className="text-slate-400">Manage your forensic investigation cases.</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            New Case
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {showCreate && (
          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Create New Case</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="label">Case Number</label>
                <input
                  {...{}}
                  value={formData.case_number}
                  onChange={(e) => setFormData({ ...formData, case_number: e.target.value })}
                  placeholder="CASE-2026-001"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Title</label>
                <input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Case title"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Case description..."
                  className="input min-h-[80px]"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary">Create Case</button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Case Number</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Title</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Status</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Created</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cases.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No investigation cases found. Create your first case to get started.
                    </td>
                  </tr>
                )}
                {cases.map((c) => (
                  <tr key={c.id} className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 text-sm text-slate-300 font-mono">{c.case_number}</td>
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
                    <td className="py-3 text-sm text-slate-500">{new Date(c.created_at).toLocaleDateString()}</td>
                    <td className="py-3">
                      <Link to={`/cases/${c.id}`} className="text-nexus-accent hover:underline text-sm">
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <p className="text-xs text-slate-500 text-center mt-8">
          PROJECT NEXUS AI - Case access is restricted to case owners and authorized users only.
        </p>
      </div>
    </Layout>
  )
}
