// =============================================================================
// PROJECT NEXUS AI - MOSAIC Scenario Reconstruction Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Layout } from '@/components/Layout'
import { mosaicAPI } from '@/services/api'
import { Plus } from 'lucide-react'

interface Scenario {
  id: string
  scenario_name: string
  scenario_description: string
  confidence_level?: string
  created_at: string
}

export function MosaicPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [formData, setFormData] = useState({ scenario_name: '', scenario_description: '', confidence_level: '' })

  useEffect(() => {
    loadScenarios()
  }, [])

  const loadScenarios = async () => {
    try {
      const response = await mosaicAPI.listScenarios('00000000-0000-0000-0000-000000000000')
      setScenarios(response.data)
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load scenarios')
      }
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await mosaicAPI.createScenario('00000000-0000-0000-0000-000000000000', formData)
      setShowCreate(false)
      setFormData({ scenario_name: '', scenario_description: '', confidence_level: '' })
      loadScenarios()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create scenario')
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">MOSAIC - Scenario Reconstruction</h2>
            <p className="text-slate-400">
              Reconstruct possible scenarios from collected evidence. MOSAIC helps investigators
              explore different narratives supported by the evidence.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            New Scenario
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span>{error}</span>
          </div>
        )}

        {showCreate && (
          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Create Scenario</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="label">Scenario Name</label>
                <input
                  value={formData.scenario_name}
                  onChange={(e) => setFormData({ ...formData, scenario_name: e.target.value })}
                  placeholder="e.g., Unauthorized Access Scenario"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Scenario Description</label>
                <textarea
                  value={formData.scenario_description}
                  onChange={(e) => setFormData({ ...formData, scenario_description: e.target.value })}
                  placeholder="Describe the reconstructed scenario..."
                  className="input min-h-[100px]"
                />
              </div>
              <div>
                <label className="label">Confidence Level</label>
                <input
                  value={formData.confidence_level}
                  onChange={(e) => setFormData({ ...formData, confidence_level: e.target.value })}
                  placeholder="e.g., High, Medium, Low"
                  className="input"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary">Create Scenario</button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-4">Reconstructed Scenarios</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Scenario Name</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Description</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Confidence</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Created</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      No scenarios generated yet.
                    </td>
                  </tr>
                )}
                {scenarios.map((s) => (
                  <tr key={s.id} className="border-b border-slate-800">
                    <td className="py-3 text-sm text-slate-300">{s.scenario_name}</td>
                    <td className="py-3 text-sm text-slate-400">{s.scenario_description}</td>
                    <td className="py-3 text-sm text-slate-400">{s.confidence_level || '—'}</td>
                    <td className="py-3 text-sm text-slate-500">
                      {new Date(s.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  )
}
