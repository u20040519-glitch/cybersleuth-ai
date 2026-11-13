// =============================================================================
// PROJECT NEXUS AI - TIMEGLASS Temporal Analysis Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Layout } from '@/components/Layout'
import { timeglassAPI } from '@/services/api'
import { Plus } from 'lucide-react'

interface TimelineEvent {
  id: string
  event_timestamp: string
  event_description: string
  source_evidence_id?: string
  created_at: string
}

export function TimeglassPage() {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [formData, setFormData] = useState({ event_timestamp: '', event_description: '', source_evidence_id: '' })

  useEffect(() => {
    loadEvents()
  }, [])

  const loadEvents = async () => {
    try {
      const response = await timeglassAPI.listEvents('00000000-0000-0000-0000-000000000000')
      setEvents(response.data)
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load timeline events')
      }
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await timeglassAPI.createEvent('00000000-0000-0000-0000-000000000000', formData)
      setShowCreate(false)
      setFormData({ event_timestamp: '', event_description: '', source_evidence_id: '' })
      loadEvents()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create timeline event')
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">TIMEGLASS - Temporal Analysis</h2>
            <p className="text-slate-400">
              Build a chronological timeline of events from your evidence. TIMEGLASS helps
              establish the sequence of activities in your investigation.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Add Event
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span>{error}</span>
          </div>
        )}

        {showCreate && (
          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Add Timeline Event</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="label">Event Timestamp</label>
                <input
                  type="datetime-local"
                  value={formData.event_timestamp}
                  onChange={(e) => setFormData({ ...formData, event_timestamp: e.target.value })}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Event Description</label>
                <textarea
                  value={formData.event_description}
                  onChange={(e) => setFormData({ ...formData, event_description: e.target.value })}
                  placeholder="Describe what happened..."
                  className="input min-h-[100px]"
                />
              </div>
              <div>
                <label className="label">Source Evidence ID (optional)</label>
                <input
                  value={formData.source_evidence_id}
                  onChange={(e) => setFormData({ ...formData, source_evidence_id: e.target.value })}
                  placeholder="Evidence file ID"
                  className="input"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary">Add Event</button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-4">Timeline Events</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Timestamp</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Description</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Source Evidence</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Created</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      No timeline events recorded yet.
                    </td>
                  </tr>
                )}
                {events.map((e) => (
                  <tr key={e.id} className="border-b border-slate-800">
                    <td className="py-3 text-sm text-slate-300 font-mono text-xs">
                      {new Date(e.event_timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 text-sm text-slate-400">{e.event_description}</td>
                    <td className="py-3 text-sm text-slate-500">{e.source_evidence_id || '—'}</td>
                    <td className="py-3 text-sm text-slate-500">
                      {new Date(e.created_at).toLocaleDateString()}
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
