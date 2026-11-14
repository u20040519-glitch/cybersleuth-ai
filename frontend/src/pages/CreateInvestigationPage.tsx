// =============================================================================
// CYBERSLEUTH AI - Create Investigation Page
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader } from '@/ui/Card'
import { Button } from '@/ui/Button'
import { TextArea } from '@/ui/Input'
import { FileText, ChevronLeft } from 'lucide-react'

const categories = [
  'Cyber Intrusion',
  'Malware Analysis',
  'Data Breach',
  'Insider Threat',
  'Fraud Investigation',
  'Intellectual Property Theft',
  'Child Exploitation',
  'Terrorism',
  'Other',
]

const priorities = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

export function CreateInvestigationPage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    case_id: '',
    title: '',
    description: '',
    category: categories[0],
    priority: 'medium',
    assigned_users: '',
    notes: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    // Phase 2: POST to /api/investigations
    // Simulate navigation after creation
    setTimeout(() => {
      setIsLoading(false)
      navigate('/investigations')
    }, 800)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate(-1)}
          className="text-text-secondary/60 hover:text-text-main lg:hidden"
        >
          <ChevronLeft size={20} />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-text-main">New Investigation</h2>
          <p className="text-text-secondary">
            Create a case to containerise evidence and forensic analysis.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader title="Case Details" />
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <label className="label">Case ID</label>
              <input
                type="text"
                placeholder="e.g. CASE-2026-001"
                className="input"
                value={formData.case_id}
                onChange={(e) => setFormData({ ...formData, case_id: e.target.value })}
              />
              <p className="text-xs text-text-secondary/60">
                Unique identifier for this investigation (UUID generated on save)
              </p>
            </div>
            <div className="space-y-2">
              <label className="label">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="input"
              >
                {priorities.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="label">Case Title</label>
            <input
              type="text"
              placeholder="Enter investigation title"
              className="input"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="label">Category</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="input"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="label">Description</label>
            <TextArea
              label=""
              placeholder="Describe the scope and objectives of this investigation..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <label className="label">Assigned Users (email, comma-separated)</label>
            <input
              type="text"
              placeholder="investigator@cybersleuth.ai, supervisor@cybersleuth.ai"
              className="input"
              value={formData.assigned_users}
              onChange={(e) => setFormData({ ...formData, assigned_users: e.target.value })}
            />
            <p className="text-xs text-text-secondary/60">
              Supervisors can view authorised investigations.
            </p>
          </div>

          <div className="space-y-2">
            <label className="label">Investigator Notes</label>
            <TextArea
              label=""
              placeholder="Initial case notes, observations, hypotheses..."
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={4}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/50">
            <Button variant="ghost" type="button" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                  Creating...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <FileText size={16} /> Create Investigation
                </span>
              )}
            </Button>
          </div>
        </form>
      </Card>

      <div className="bg-secondary/30 border border-border/50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-text-main mb-2">How investigations work</h3>
        <ul className="text-xs text-text-secondary space-y-2 list-disc list-inside">
          <li>Each investigation gets a unique UUID and acts as the central container for all evidence and analysis.</li>
          <li>Evidence uploaded to the vault can be linked to one or more investigations.</li>
          <li>All four forensic modules (DeepTrace, SpyTrace, VoiceProof, CyberSleuth) write results to the same investigation.</li>
          <li>The Correlation Engine connects findings across modules within an investigation.</li>
        </ul>
      </div>
    </div>
  )
}
