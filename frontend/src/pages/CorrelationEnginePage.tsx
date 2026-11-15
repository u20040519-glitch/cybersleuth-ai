// =============================================================================
// CYBERSLEUTH AI - Correlation Engine Page
// =============================================================================

import { useEffect, useMemo, useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'
import {
  Share,
  Activity,
  AlertCircle,
  Sparkles,
  Network,
} from 'lucide-react'
import { investigationsAPI, correlationAPI } from '@/services/api'

function ExplanationView({ explanation }: { explanation: any }) {
  // The backend returns { available, reason?, text?, model? }. The text is
  // usually a JSON object from the model; parse and render it when possible.
  let parsed: any = null
  const text: string = typeof explanation?.text === 'string' ? explanation.text : ''
  if (text) {
    const start = text.indexOf('{')
    const end = text.lastIndexOf('}')
    if (start !== -1 && end > start) {
      try {
        parsed = JSON.parse(text.slice(start, end + 1))
      } catch {
        parsed = null
      }
    }
  }

  if (!parsed) {
    return (
      <pre className="whitespace-pre-wrap text-xs text-text-main font-sans leading-relaxed max-h-64 overflow-y-auto">
        {text || 'No explanation was produced.'}
      </pre>
    )
  }

  const entries: Array<[string, any]> = Object.entries(parsed)
  return (
    <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
      {entries.map(([key, value]) => (
        <div key={key}>
          <p className="text-[10px] uppercase tracking-wider text-primary-cyan mb-1">{key.replace(/_/g, ' ')}</p>
          {Array.isArray(value) ? (
            <ul className="list-disc list-inside text-xs text-text-main space-y-1">
              {value.map((item, i) => (
                <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-main leading-relaxed">
              {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

function CircleGraph({ graph }: { graph: any }) {
  const nodes: any[] = Array.isArray(graph?.nodes) ? graph.nodes : []
  const edges: any[] = Array.isArray(graph?.edges) ? graph.edges : []
  const layout = useMemo(() => {
    const placed: Array<{ node: any; x: number; y: number }> = []
    const radius = 120
    const cx = 150
    const cy = 110
    nodes.slice(0, 24).forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1)
      placed.push({ node, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) })
    })
    return { placed, cx, cy }
  }, [nodes])

  const position = new Map(layout.placed.map(({ node, x, y }) => [node.id, { x, y }]))

  if (nodes.length === 0) return null

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox="0 0 300 220" className="w-full min-w-[280px] h-52" role="img" aria-label="Relationship graph">
        {edges.slice(0, 60).map((edge, i) => {
          const from = position.get(edge.source)
          const to = position.get(edge.target)
          if (!from || !to) return null
          return (
            <line
              key={i}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="#3B82F6"
              strokeOpacity={0.45}
              strokeWidth={Math.min(3, 1 + Number(edge.weight ?? 0.5))}
            />
          )
        })}
        {layout.placed.map(({ node, x, y }) => (
          <g key={node.id}>
            <circle
              cx={x}
              cy={y}
              r={node.type === 'evidence' ? 10 : 7}
              fill={node.type === 'evidence' ? '#22D3EE' : '#3B82F6'}
              fillOpacity={0.9}
            >
              <title>{String(node.label)}</title>
            </circle>
            <text
              x={x}
              y={y + (node.type === 'evidence' ? 22 : 18)}
              textAnchor="middle"
              fontSize="6.5"
              fill="#E6F0FF"
            >
              {String(node.label).slice(0, 18)}
            </text>
          </g>
        ))}
      </svg>
      <div className="flex items-center justify-between px-2">
        <p className="text-xs text-text-secondary/60">
          Nodes: {nodes.length} · Edges: {edges.length}
        </p>
        <div className="flex items-center gap-3 text-[10px] text-text-secondary/60">
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-primary-cyan" /> evidence</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-primary-blue" /> event</span>
        </div>
      </div>
    </div>
  )
}

export function CorrelationEnginePage() {
  const [investigations, setInvestigations] = useState<any[]>([])
  const [investigationId, setInvestigationId] = useState('')
  const [correlating, setCorrelating] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    investigationsAPI
      .list()
      .then((res) => setInvestigations(res.data || []))
      .catch(() => setError('Investigations could not be loaded.'))
  }, [])

  // Whenever an investigation is chosen, surface the most recent run (if any).
  useEffect(() => {
    setResult(null)
    setError(null)
    if (!investigationId) return
    setLoading(true)
    correlationAPI
      .get(investigationId)
      .then((res) => {
        setResult(res.data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [investigationId])

  const handleCorrelate = async () => {
    if (!investigationId) return
    setCorrelating(true)
    setError(null)
    try {
      const res = await correlationAPI.analyze(investigationId)
      setResult(res.data)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'The correlation run failed. See the server log for details.')
    } finally {
      setCorrelating(false)
    }
  }

  const timeline: any[] = result?.timeline ?? []
  const connections: any[] = result?.connections ?? []
  const explanation = result?.explanation
  const explanationText: any =
    explanation && typeof explanation === 'object' && explanation.text ? explanation : null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">Correlation Engine</h2>
        <p className="text-text-secondary">
          Unify findings from all four forensic modules into a single investigation timeline and relationship graph.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Run Correlation" />
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="label" htmlFor="correlation-investigation">Investigation</label>
                <select
                  id="correlation-investigation"
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
                <p className="text-xs text-text-secondary/60 mb-2">What it does</p>
                <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
                  <li>Retrieves structured findings from all modules</li>
                  <li>Normalises timestamps across evidence</li>
                  <li>Links shared hashes, URLs, IPs, emails and identical timestamps</li>
                  <li>Builds a chronological timeline and a relationship graph</li>
                  <li>Explains the findings with Gemini (grounded in the data)</li>
                </ul>
              </div>
              {error && (
                <p className="text-xs text-error flex items-center gap-1">
                  <AlertCircle size={12} /> {error}
                </p>
              )}
              <Button
                variant="primary"
                onClick={handleCorrelate}
                disabled={!investigationId || correlating}
                className="w-full"
              >
                {correlating ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Correlating…
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Share size={16} /> Run Correlation
                  </span>
                )}
              </Button>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {correlating || loading ? (
            <Card>
              <CardHeader title={correlating ? 'Correlation Running' : 'Loading Results'} />
              <div className="flex flex-col items-center justify-center py-12">
                <Activity size={48} className="mb-4 text-primary-cyan" />
                <p className="text-text-secondary">
                  {correlating ? 'Connecting findings across all four modules…' : 'Loading the latest correlation run…'}
                </p>
              </div>
            </Card>
          ) : result ? (
            <Card>
              <CardHeader
                title="Correlation Results"
                subtitle={`Generated ${result.generated_at ? new Date(result.generated_at).toLocaleString() : 'just now'} · ${timeline.length} events · ${connections.length} connections`}
              />
              <div className="space-y-5">
                <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                  <div>
                    <p className="text-xs text-text-secondary/60">Connections Found</p>
                    <p className="text-sm font-mono text-text-main">{connections.length}</p>
                  </div>
                  <Badge variant="info">AI-Assisted</Badge>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-text-main mb-3">Chronological Timeline</h3>
                  {timeline.length === 0 ? (
                    <p className="text-xs text-text-secondary/60">
                      No timestamped events were produced by the modules yet. Run analyses on evidence first.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                      {timeline.map((t: any, i: number) => (
                        <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-secondary border border-border">
                          <span className="w-36 shrink-0 font-mono text-[10px] text-primary-blue">
                            {t.timestamp ? new Date(t.timestamp).toLocaleString() : 'undated'}
                          </span>
                          <Badge variant="info" className="text-[10px] shrink-0">{t.module ?? 'event'}</Badge>
                          <p className="text-xs text-text-main flex-1 leading-snug">
                            <span className="font-medium">{t.label}</span>
                            {t.details ? <span className="text-text-secondary"> — {String(t.details).slice(0, 140)}</span> : null}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-text-main mb-3">Evidence Connections</h3>
                  {connections.length === 0 ? (
                    <p className="text-xs text-text-secondary/60">
                      No cross-evidence links yet. The engine links shared hashes, URLs, IPs, emails and identical timestamps — run the module analyses on this case first.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {connections.map((c: any, i: number) => (
                        <div key={i} className="p-3 rounded-lg bg-secondary border border-border">
                          <div className="flex items-center justify-between gap-3 mb-2">
                            <span className="text-[10px] font-mono text-text-secondary truncate">{c.source}</span>
                            <span className="text-[10px] font-mono text-text-secondary truncate">{c.target}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-text-main flex-1">{c.description}</span>
                            <Badge variant={Number(c.confidence ?? 0) >= 0.8 ? 'success' : 'warning'}>
                              {Math.round(Number(c.confidence ?? 0) * 100)}%
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <h3 className="flex items-center gap-2 text-xs font-semibold text-text-secondary/60 mb-3">
                    <Network size={14} /> Relationship Graph
                  </h3>
                  <CircleGraph graph={result.graph} />
                </div>

                {explanationText && (
                  <div className="p-4 rounded-lg bg-primary-blue/5 border border-primary-blue/20">
                    <h3 className="flex items-center gap-2 text-xs font-semibold text-primary-cyan mb-2">
                      <Sparkles size={14} /> AI Explanation ({explanationText.model ?? 'Gemini'} · grounded in the findings)
                    </h3>
                    <ExplanationView explanation={explanationText} />
                  </div>
                )}

                {explanation && explanation.available === false && (
                  <div className="p-3 rounded-lg bg-warning/10 border border-warning/20">
                    <p className="text-xs text-warning">
                      <strong>AI explanation unavailable.</strong> {explanation.reason ?? 'The explanation layer is not configured on this deployment.'}
                    </p>
                  </div>
                )}

                <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                  <p className="text-xs text-error">
                    <strong>Investigator review required.</strong> Correlations are hypotheses, not conclusions. Do not infer identity or guilt from timestamps alone.
                  </p>
                </div>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={Share}
              title="Select an investigation"
              description="Correlate findings across DeepTrace, SpyTrace, VoiceProof, and CyberSleuth modules."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
