// =============================================================================
// CYBERSLEUTH AI - Shared module analysis page
// =============================================================================
// One implementation behind all four forensic module pages. The flow is the
// real one: pick an investigation, pick stored evidence (filtered to the file
// classes the module understands), run the analysis on the backend, render
// the structured result it returns.
// =============================================================================

import { useEffect, useMemo, useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import { Link } from 'react-router-dom'
import { FileScan, ShieldAlert, Info, AlertCircle, ExternalLink, ChevronDown } from 'lucide-react'
import { investigationsAPI, evidenceAPI, analysisAPI } from '@/services/api'
import { truncateHash } from '@/utils/format'

export type ModuleKey = 'deeptrace' | 'spytrace' | 'voiceproof' | 'cybersleuth'

interface ModuleAnalysisPageProps {
  module: ModuleKey
  title: string
  tagline: string
  purpose: string
  outputs: string
  misuseWarning: string
  acceptedMimes: string[] // mime prefixes or exact types; empty = all
  acceptLabel: string
  accentIcon: React.ElementType
  accentColor: string
  runButtonLabel: string
}

const METHOD_LABEL: Record<string, string> = {
  measured: 'measured',
  heuristic: 'heuristic',
  model: 'model',
}

function severityVariant(severity: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  const key = (severity || '').toLowerCase()
  if (['critical', 'high', 'error', 'danger'].includes(key)) return 'error'
  if (['medium', 'warning', 'moderate'].includes(key)) return 'warning'
  if (['low', 'info', 'informational'].includes(key)) return 'info'
  if (['success', 'ok', 'pass'].includes(key)) return 'success'
  return 'default'
}

function confidenceText(value: any): string {
  if (value === null || value === undefined) return 'Not model-calibrated'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return `${(n * 100).toFixed(1)}%`
}

export function ModuleAnalysisPage({
  module,
  title,
  tagline,
  purpose,
  outputs,
  misuseWarning,
  acceptedMimes,
  acceptLabel,
  accentIcon: AccentIcon,
  accentColor,
  runButtonLabel,
}: ModuleAnalysisPageProps) {
  const [investigations, setInvestigations] = useState<any[]>([])
  const [evidence, setEvidence] = useState<any[]>([])
  const [investigationId, setInvestigationId] = useState('')
  const [evidenceId, setEvidenceId] = useState('')
  const [loadingEvidence, setLoadingEvidence] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<any | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  useEffect(() => {
    investigationsAPI
      .list()
      .then((res) => setInvestigations(res.data || []))
      .catch(() => setEvidenceError('Investigations could not be loaded.'))
  }, [])

  // Stable dependency key: the prop is a fresh array reference each render.
  const acceptedMimesKey = acceptedMimes.join('|')

  useEffect(() => {
    if (!investigationId) {
      setEvidence([])
      setEvidenceId('')
      return
    }
    setLoadingEvidence(true)
    setEvidenceError(null)
    evidenceAPI
      .list({ investigation_id: investigationId })
      .then((res) => {
        const rows = res.data || []
        const prefixes = acceptedMimesKey ? acceptedMimesKey.split('|') : []
        const filtered =
          prefixes.length === 0
            ? rows
            : rows.filter((row: any) => {
                const mime = String(row.mime_type || '').toLowerCase()
                return prefixes.some((prefix) => mime.startsWith(prefix.toLowerCase()))
              })
        setEvidence(filtered)
        setEvidenceId('')
        setLoadingEvidence(false)
      })
      .catch(() => {
        setEvidenceError('Evidence for this investigation could not be loaded.')
        setLoadingEvidence(false)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [investigationId, acceptedMimesKey])

  const selectedEvidence = useMemo(
    () => evidence.find((row) => row.id === evidenceId) ?? null,
    [evidence, evidenceId],
  )

  const handleAnalyze = async () => {
    if (!evidenceId) return
    setAnalyzing(true)
    setResult(null)
    setAnalysisError(null)
    try {
      const analyze = analysisAPI[module]
      const res = await analyze(evidenceId, {})
      const payload = res.data
      setResult(payload?.result_data ? { ...payload.result_data, _record: payload } : payload)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setAnalysisError(typeof detail === 'string' ? detail : 'The analysis request failed. See the server log for details.')
    } finally {
      setAnalyzing(false)
    }
  }

  const resultData = result ?? null
  const findings: any[] = Array.isArray(resultData?.findings) ? resultData.findings : []
  const timeline: any[] = Array.isArray(resultData?.timeline) ? resultData.timeline : []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main flex items-center gap-3">
          <AccentIcon size={26} className={accentColor} /> {title}
        </h2>
        <p className="text-text-secondary">{tagline}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Analysis launcher */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Run Analysis" />
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="label" htmlFor="investigation-select">Investigation</label>
                <select
                  id="investigation-select"
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

              <div className="space-y-2">
                <label className="label" htmlFor="evidence-select">Evidence ({acceptLabel})</label>
                <select
                  id="evidence-select"
                  className="input"
                  value={evidenceId}
                  onChange={(e) => setEvidenceId(e.target.value)}
                  disabled={!investigationId || loadingEvidence}
                >
                  <option value="">
                    {!investigationId
                      ? 'Select an investigation first'
                      : loadingEvidence
                        ? 'Loading evidence…'
                        : evidence.length === 0
                          ? 'No compatible evidence in this case'
                          : 'Select evidence…'}
                  </option>
                  {evidence.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.original_filename}
                    </option>
                  ))}
                </select>
              </div>

              {evidenceError && (
                <p className="text-xs text-error flex items-center gap-1">
                  <AlertCircle size={12} /> {evidenceError}
                </p>
              )}

              {selectedEvidence && (
                <div className="p-3 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Selected evidence</p>
                  <p className="text-sm text-text-main truncate">{selectedEvidence.original_filename}</p>
                  <p className="text-xs text-text-secondary/60 font-mono">
                    {truncateHash(selectedEvidence.sha256_hash, 24)}
                  </p>
                  <p className="text-xs text-text-secondary/60">{selectedEvidence.mime_type}</p>
                </div>
              )}

              <Button
                variant="primary"
                onClick={handleAnalyze}
                disabled={!evidenceId || analyzing}
                className="w-full"
              >
                {analyzing ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Analyzing…
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <ShieldAlert size={16} />
                    {runButtonLabel}
                  </span>
                )}
              </Button>

              <p className="text-xs text-text-secondary/60">
                Don&apos;t see your file?{' '}
                <Link to="/evidence/upload" className="text-primary-blue hover:text-primary-cyan">
                  Upload it first <ExternalLink size={10} className="inline" />
                </Link>
              </p>
            </div>
          </Card>

          <Card>
            <CardHeader title="Module Info" />
            <div className="space-y-3 text-xs text-text-secondary/70">
              <p><strong className="text-text-main">Purpose:</strong> {purpose}</p>
              <p><strong className="text-text-main">Outputs:</strong> {outputs}</p>
              <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                <p className="text-xs text-error">
                  <strong>Important:</strong> {misuseWarning}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Results */}
        <div className="lg:col-span-2">
          {analysisError && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-error/10 border border-error/20 mb-4">
              <AlertCircle size={18} className="text-error shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-error font-semibold">Analysis failed</p>
                <p className="text-xs text-error/80">{analysisError}</p>
              </div>
            </div>
          )}

          {analyzing ? (
            <Card>
              <CardHeader title="Analysis Running" />
              <div className="flex flex-col items-center justify-center py-12">
                <LoadingSpinner size="lg" />
                <p className="text-text-secondary mt-4">Running the {title} pipeline on the backend…</p>
                <p className="text-xs text-text-secondary/60 mt-1">Static analysis only; the evidence is never modified or executed.</p>
              </div>
            </Card>
          ) : resultData ? (
            <Card>
              <CardHeader
                title="Analysis Results"
                subtitle={resultData?.summary || undefined}
              />
              <div className="space-y-5">
                {resultData?.reason && resultData?.status !== 'completed' && (
                  <div className="p-3 rounded-lg bg-warning/10 border border-warning/20">
                    <p className="text-xs text-warning">
                      <strong>Status: {resultData.status}.</strong> {resultData.reason}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-secondary border border-border rounded-xl p-4">
                    <p className="text-xs text-text-secondary/60 mb-2">Evidence</p>
                    <p className="text-sm text-text-main truncate">{resultData?.filename ?? 'Unknown'}</p>
                    <p className="text-[10px] text-text-secondary/60 font-mono break-all mt-1">
                      SHA-256: {resultData?.sha256 ?? 'not reported'}
                    </p>
                    <p className="text-xs text-text-secondary/60 mt-1">
                      {resultData?.dimensions ? `${resultData.dimensions} • ` : ''}{resultData?.mime}
                    </p>
                  </div>
                  <div className="bg-secondary border border-border rounded-xl p-4">
                    <p className="text-xs text-text-secondary/60 mb-2">Confidence</p>
                    <p className="text-sm text-text-main">{confidenceText(resultData?.confidence_score)}</p>
                    <p className="text-xs text-text-secondary/60 mt-2">
                      {findings.length} finding(s) · {timeline.length} timeline event(s)
                    </p>
                  </div>
                </div>

                {/* Findings */}
                {findings.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-text-main mb-2">Findings</h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                      {findings.map((finding, i) => (
                        <div key={i} className="p-3 rounded-lg bg-secondary border border-border">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-2 min-w-0">
                              <Info size={14} className="text-text-secondary/50 mt-0.5 shrink-0" />
                              <div className="min-w-0">
                                <p className="text-xs font-semibold text-text-main">{finding.label}</p>
                                <p className="text-xs text-text-secondary mt-0.5 leading-relaxed">{finding.detail}</p>
                              </div>
                            </div>
                            <div className="flex flex-col items-end gap-1 shrink-0">
                              <Badge variant={severityVariant(String(finding.severity))}>
                                {String(finding.severity ?? 'info')}
                              </Badge>
                              <span className="text-[10px] uppercase tracking-wider text-text-secondary/50">
                                {METHOD_LABEL[String(finding.method)] ?? String(finding.method ?? 'measured')}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timeline */}
                {timeline.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-text-main mb-2">Timeline Events</h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {timeline.slice(0, 30).map((event, i) => (
                        <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-secondary border border-border">
                          <span className="text-[10px] font-mono text-primary-blue w-36 shrink-0">
                            {event.timestamp ? new Date(event.timestamp).toLocaleString() : 'undated'}
                          </span>
                          <p className="text-xs text-text-main flex-1 truncate">{event.label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw metadata */}
                {resultData?.metadata && Object.keys(resultData.metadata).length > 0 && (
                  <details className="rounded-lg bg-secondary border border-border">
                    <summary className="flex items-center gap-2 p-3 cursor-pointer text-xs font-semibold text-text-secondary/70 hover:text-text-main">
                      <ChevronDown size={14} /> Raw module metadata (JSON)
                    </summary>
                    <pre className="text-[10px] font-mono text-text-secondary overflow-x-auto p-3 pt-0 max-h-64">
                      {JSON.stringify(resultData.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={FileScan}
              title="No analysis yet"
              description="Select the investigation and evidence above, then run the module to see real findings here."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
