// =============================================================================
// CYBERSLEUTH AI - Correlation Engine Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'

import { Share, Activity } from 'lucide-react'

export function CorrelationEnginePage() {
  const [investigationId, setInvestigationId] = useState('')
  const [correlating, setCorrelating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [demo, setDemo] = useState(true)

  const handleCorrelate = async () => {
    if (!investigationId) {
      setResult(null)
      return
    }
    setCorrelating(true)
    setResult(null)
    // Phase 2: POST to /api/correlation/{investigation_id}
    setTimeout(() => {
      setCorrelating(false)
      setDemo(false)
      setResult({
        investigation_id: investigationId,
        totalConnections: 7,
        timeline: [
          { time: '10:14:22', source: 'Surveillance Footage.mp4', type: 'Video frame', event: 'Subject enters frame' },
          { time: '10:15:01', source: 'Recording.wav', type: 'Audio segment', event: 'Voice command detected' },
          { time: '10:16:33', source: 'Mobile_App.apk', type: 'Network', event: 'Connection to analytics domain' },
          { time: '10:18:09', source: 'chat_export.json', type: 'Message', event: 'Coordination message sent' },
        ],
        connections: [
          { source: 'Surveillance Footage.mp4', target: 'Recording.wav', reason: 'Overlapping timestamps (±2s)', confidence: 0.92 },
          { source: 'Mobile_App.apk', target: 'chat_export.json', reason: 'Shared domain: example-tracker.com', confidence: 0.78 },
          { source: 'Recording.wav', target: 'chat_export.json', reason: 'Same device metadata', confidence: 0.65 },
        ],
        graph: {
          nodes: [
            { id: 'ev1', label: 'Surveillance Footage.mp4', module: 'deeptrace' },
            { id: 'ev2', label: 'Recording.wav', module: 'voiceproof' },
            { id: 'ev3', label: 'Mobile_App.apk', module: 'spytrace' },
            { id: 'ev4', label: 'chat_export.json', module: 'cybersleuth' },
          ],
          edges: [
            { from: 'ev1', to: 'ev2' },
            { from: 'ev3', to: 'ev4' },
            { from: 'ev2', to: 'ev4' },
          ],
        },
      })
    }, 2000)
  }

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
                <p className="text-xs text-text-secondary/60 mb-2">What it does</p>
                <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
                  <li>Retrieves structured findings from all modules</li>
                  <li>Normalises timestamps across evidence</li>
                  <li>Extracts shared entities and indicators</li>
                  <li>Builds chronological timeline and graph</li>
                </ul>
              </div>
              <Button
                variant="primary"
                onClick={handleCorrelate}
                disabled={!investigationId || correlating}
                className="w-full"
              >
                {correlating ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Correlating...
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
          {correlating ? (
            <Card>
              <CardHeader title="Correlation Running" />
              <div className="flex flex-col items-center justify-center py-12">
                <Activity size={48} className="mb-4 text-primary-cyan" />
                <p className="text-text-secondary">Connecting findings across all four modules...</p>
              </div>
            </Card>
          ) : result ? (
            <Card>
              <CardHeader title="Correlation Results" />
              <div className="space-y-5">
                <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                  <div>
                    <p className="text-xs text-text-secondary/60">Connections Found</p>
                    <p className="text-sm font-mono text-text-main">{result.totalConnections}</p>
                  </div>
                  <Badge variant="info">AI-Assisted</Badge>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-text-main mb-3">Chronological Timeline</h3>
                  <div className="space-y-3">
                    {result.timeline.map((t: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-secondary border border-border">
                        <div className="w-20 font-mono text-xs text-primary-blue">{t.time}</div>
                        <Badge variant="info" className="text-[10px]">{t.type}</Badge>
                        <p className="text-sm text-text-main flex-1">{t.event}</p>
                        <span className="text-xs text-text-secondary/60 font-mono truncate">{t.source}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-text-main mb-3">Evidence Connections</h3>
                  <div className="space-y-2">
                    {result.connections.map((c: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg bg-secondary border border-border">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono text-text-secondary">{c.source}</span>
                          <span className="text-xs font-mono text-text-secondary">{c.target}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-text-main">{c.reason}</span>
                          <Badge variant={c.confidence > 0.8 ? 'success' : 'warning'}>
                            {Math.round(c.confidence * 100)}%
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-secondary border border-border">
                  <h3 className="text-xs font-semibold text-text-secondary/60 mb-2">Relationship Graph</h3>
                  <div className="h-32 bg-[#080D18] rounded-lg border border-border flex items-center justify-center relative overflow-hidden">
                    <div className="absolute inset-0 border-2 border-primary-blue/20 rounded-full animate-spin" />
                    <div className="absolute inset-0 border-2 border-primary-cyan/20 rounded-full animate-spin" style={{ animationDirection: 'reverse' }} />
                    <span className="text-text-secondary/50 text-xs">Graph visualization renders in Phase 2 (NetworkX + React flow)</span>
                  </div>
                  <p className="text-xs text-text-secondary/60 mt-2">
                    Nodes: {result.graph.nodes.length} • Edges: {result.graph.edges.length}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                  <p className="text-xs text-error">
                    <strong>Investigator review required.</strong> Correlations are hypotheses, not conclusions. Do not infer identity or guilt from timestamps alone.
                  </p>
                </div>
              </div>
            </Card>
          ) : demo ? (
            <EmptyState
              icon={Share}
              title="Enter an investigation ID"
              description="Correlate findings across DeepTrace, SpyTrace, VoiceProof, and CyberSleuth modules."
              action={null}
            />
          ) : (
            <EmptyState
              icon={Share}
              title="No correlation results"
              description="Run correlation on an investigation to see connected findings."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
