// =============================================================================
// CYBERSLEUTH AI - Reports Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'

import { FileText, Download, ChevronLeft, Clock } from 'lucide-react'

export function ReportsPage() {
  const [investigationId, setInvestigationId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState(false)
  const [reportId, setReportId] = useState<string | null>(null)

  const handleGenerate = async () => {
    if (!investigationId) return
    setGenerating(true)
    // Phase 2: POST to /api/reports/{investigation_id}, returns PDF
    setTimeout(() => {
      setGenerating(false)
      setGenerated(true)
      setReportId(`RPT-${Date.now().toString(36).slice(-6)}`)
    }, 2000)
  }

  const handleDownload = () => {
    // Phase 2: download PDF from backend
    const link = document.createElement('a')
    link.href = '#'
    link.download = `cybersleuth-report-${investigationId || 'case'}.pdf`
    link.click()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <button
          onClick={() => window.history.back()}
          className="text-text-secondary/60 hover:text-text-main lg:hidden"
        >
          <ChevronLeft size={20} />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-text-main">Forensic Reports</h2>
          <p className="text-text-secondary">
            Generate professional PDF forensic reports with chain-of-custody and integrity information.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Generate Report" />
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="label">Investigation ID</label>
                <input
                  type="text"
                  placeholder="Enter investigation ID"
                  className="input"
                  value={investigationId}
                  onChange={(e) => setInvestigationId(e.target.value)}
                />
              </div>
              <div className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                <p className="text-xs text-text-secondary/60 mb-2">Report includes</p>
                <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
                  <li>Investigation &amp; investigator details</li>
                  <li>Evidence inventory with SHA-256 hashes</li>
                  <li>Chain-of-custody events</li>
                  <li>All four module findings</li>
                  <li>Correlation timeline &amp; graph</li>
                  <li>AI-generated summary (grounded in evidence)</li>
                  <li>Limitations and investigator review</li>
                </ul>
              </div>
              <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                <p className="text-xs text-error">
                  <strong>Not court-certified.</strong> This report is an investigative aid, not legally conclusive.
                </p>
              </div>
              <Button
                variant="primary"
                onClick={handleGenerate}
                disabled={!investigationId || generating}
                className="w-full"
              >
                {generating ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Generating PDF...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <FileText size={16} /> Generate Report
                  </span>
                )}
              </Button>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {generating ? (
            <Card>
              <CardHeader title="Generating Report" />
              <div className="flex flex-col items-center justify-center py-12">
                <Clock size={48} className="mb-4 text-primary-cyan" />
                <p className="text-text-secondary">Compiling evidence and analysis findings into PDF...</p>
              </div>
            </Card>
          ) : generated ? (
            <Card>
              <CardHeader title="Report Ready" />
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-secondary border border-border">
                  <div>
                    <p className="text-xs text-text-secondary/60">Report ID</p>
                    <p className="text-sm font-mono text-text-main">{reportId}</p>
                  </div>
                  <Badge variant="success">Ready</Badge>
                </div>
                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60 mb-2">Contents</p>
                  <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside pl-4">
                    <li>Investigation overview</li>
                    <li>Evidence inventory &amp; hashes</li>
                    <li>DeepTrace, SpyTrace, VoiceProof, CyberSleuth findings</li>
                    <li>Correlation timeline</li>
                    <li>Investigator review section</li>
                  </ul>
                </div>
                <Button variant="cyan" onClick={handleDownload} className="w-full">
                  <Download size={18} className="mr-2" /> Download PDF
                </Button>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={FileText}
              title="No reports generated"
              description="Enter an investigation ID and generate a forensic PDF report."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
