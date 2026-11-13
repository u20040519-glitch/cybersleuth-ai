// =============================================================================
// PROJECT NEXUS AI - Reports Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Layout } from '@/components/Layout'
import { reportsAPI } from '@/services/api'
import { Plus, Download } from 'lucide-react'

interface Report {
  id: string
  report_title: string
  report_content: string
  generated_at: string
  owner_id: string
}

export function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [formData, setFormData] = useState({ report_title: '', report_content: '' })

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    try {
      const response = await reportsAPI.list('00000000-0000-0000-0000-000000000000')
      setReports(response.data)
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load reports')
      }
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await reportsAPI.create('00000000-0000-0000-0000-000000000000', formData)
      setShowCreate(false)
      setFormData({ report_title: '', report_content: '' })
      loadReports()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate report')
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Forensic Reports</h2>
            <p className="text-slate-400">
              Generate and manage investigation reports. Reports document findings from
              ECHO, MOSAIC, TIMEGLASS, and AI assistant analysis.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            New Report
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span>{error}</span>
          </div>
        )}

        {showCreate && (
          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Generate Report</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="label">Report Title</label>
                <input
                  value={formData.report_title}
                  onChange={(e) => setFormData({ ...formData, report_title: e.target.value })}
                  placeholder="Investigation Report - Case 001"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Report Content</label>
                <textarea
                  value={formData.report_content}
                  onChange={(e) => setFormData({ ...formData, report_content: e.target.value })}
                  placeholder="Enter report findings..."
                  className="input min-h-[150px]"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary">Generate Report</button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-4">Generated Reports</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Title</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Content Preview</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Generated</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      No reports generated yet.
                    </td>
                  </tr>
                )}
                {reports.map((r) => (
                  <tr key={r.id} className="border-b border-slate-800">
                    <td className="py-3 text-sm text-slate-300">{r.report_title}</td>
                    <td className="py-3 text-sm text-slate-400 truncate max-w-[200px]">
                      {r.report_content.substring(0, 100)}...
                    </td>
                    <td className="py-3 text-sm text-slate-500">
                      {new Date(r.generated_at).toLocaleDateString()}
                    </td>
                    <td className="py-3">
                      <button className="text-xs text-nexus-accent hover:underline flex items-center gap-1">
                        <Download size={14} /> Download
                      </button>
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
