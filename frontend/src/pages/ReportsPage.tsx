// =============================================================================
// CYBERSLEUTH AI - Reports Page
// =============================================================================

import { useEffect, useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import {
  FileText,
  Download,
  ChevronLeft,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react'
import { investigationsAPI, reportsAPI } from '@/services/api'
import { formatDateTime, truncateHash } from '@/utils/format'
import { useNavigate } from 'react-router-dom'

export function ReportsPage() {
  const navigate = useNavigate()
  const [investigations, setInvestigations] = useState<any[]>([])
  const [investigationId, setInvestigationId] = useState('')
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    investigationsAPI
      .list()
      .then((res) => setInvestigations(res.data || []))
      .catch(() => setError('Investigations could not be loaded.'))
  }, [])

  useEffect(() => {
    if (!investigationId) {
      setReports([])
      return
    }
    setLoading(true)
    setError(null)
    reportsAPI
      .list(investigationId)
      .then((res) => {
        setReports(res.data || [])
        setLoading(false)
      })
      .catch(() => {
        setError('Reports for this investigation could not be loaded.')
        setLoading(false)
      })
  }, [investigationId])

  const refreshReports = async () => {
    if (!investigationId) return
    const res = await reportsAPI.list(investigationId)
    setReports(res.data || [])
  }

  const handleGenerate = async () => {
    if (!investigationId) return
    setGenerating(true)
    setError(null)
    try {
      await reportsAPI.generate(investigationId)
      await refreshReports()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Report generation failed. See the server log for details.')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = async (report: any) => {
    setDownloadingId(report.id)
    try {
      const res = await reportsAPI.download(report.id)
      const url = URL.createObjectURL(res.data as Blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${(report.title || 'cybersleuth-report').replace(/[^a-z0-9-_]+/gi, '_')}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch {
      setError('The report could not be downloaded.')
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate(-1)}
          className="text-text-secondary/60 hover:text-text-main lg:hidden"
          aria-label="Back"
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
                <label className="label" htmlFor="report-investigation">Investigation</label>
                <select
                  id="report-investigation"
                  className="input"
                  value={investigationId}
                  onChange={(e) => setInvestigationId(e.target.value)}
                >
                  <option value="">Select an investigation…</option>
                  {investigations.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.case_id} — {inv.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                <p className="text-xs text-text-secondary/60 mb-2">Report includes</p>
                <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
                  <li>Investigation &amp; investigator details</li>
                  <li>Evidence inventory with SHA-256 hashes</li>
                  <li>Chain-of-custody events with the hash chain</li>
                  <li>All four module findings</li>
                  <li>Correlation connections</li>
                  <li>Investigator review and limitations section</li>
                </ul>
              </div>
              <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                <p className="text-xs text-error">
                  <strong>Not court-certified.</strong> This report is an investigative aid, not legally conclusive.
                </p>
              </div>
              {error && (
                <p className="text-xs text-error flex items-center gap-1">
                  <AlertCircle size={12} /> {error}
                </p>
              )}
              <Button
                variant="primary"
                onClick={handleGenerate}
                disabled={!investigationId || generating}
                className="w-full"
              >
                {generating ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Generating PDF…
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
          <Card>
            <CardHeader title="Reports" subtitle="Generated PDFs for the selected investigation" />
            {loading ? (
              <div className="h-40 flex items-center justify-center">
                <LoadingSpinner size="md" />
              </div>
            ) : !investigationId ? (
              <EmptyState
                icon={FileText}
                title="Select an investigation"
                description="Choose an investigation to see its generated reports, or generate a new one."
                action={null}
              />
            ) : reports.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No reports yet"
                description="Generate the first forensic report for this investigation."
                action={null}
              />
            ) : (
              <div className="space-y-3">
                {reports.map((report) => (
                  <div key={report.id} className="p-4 rounded-lg bg-secondary border border-border">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-text-main">{report.title}</p>
                        <p className="text-xs text-text-secondary/60 mt-1">
                          {formatDateTime(report.generated_at)} · {(report.file_size / 1024).toFixed(1)} KB
                        </p>
                        {report.sha256_hash && (
                          <p className="text-[10px] font-mono text-text-secondary/50 mt-1">
                            SHA-256 {truncateHash(report.sha256_hash, 24)}
                          </p>
                        )}
                      </div>
                      <Badge variant={report.status === 'ready' ? 'success' : 'warning'}>
                        {report.status}
                      </Badge>
                    </div>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <p className="text-[10px] font-mono text-text-secondary/50 flex items-center gap-1 min-w-0">
                        <ShieldCheck size={12} className="shrink-0" />
                        <span className="truncate">{report.id}</span>
                      </p>
                      <Button
                        variant="cyan"
                        size="sm"
                        disabled={report.status !== 'ready' || downloadingId === report.id}
                        onClick={() => handleDownload(report)}
                      >
                        <Download size={14} className="mr-1" />
                        {downloadingId === report.id ? 'Downloading…' : 'Download PDF'}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
