// =============================================================================
// CYBERSLEUTH AI - SpyTrace AI (Android Spyware Analysis) Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'

import { Button } from '@/ui/Button'
import { Smartphone, Bug, Terminal } from 'lucide-react'

export function SpyTracePage() {
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [file, setFile] = useState<File | null>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0])
  }

  const handleAnalyze = async () => {
    if (!file) return
    setAnalyzing(true)
    setResult(null)
    // Phase 2: POST to /api/spytrace/analyze (static analysis only — never execute APK)
    setTimeout(() => {
      setAnalyzing(false)
      setResult({
        filename: file.name,
        packageName: 'com.example.suspicious.app',
        version: '2.1.4',
        sdkMin: 21,
        sdkTarget: 33,
        permissions: [
          { name: 'READ_SMS', sensitive: true },
          { name: 'SEND_SMS', sensitive: true },
          { name: 'ACCESS_FINE_LOCATION', sensitive: true },
          { name: 'RECORD_AUDIO', sensitive: true },
          { name: 'INTERNET', sensitive: false },
          { name: 'ACCESS_NETWORK_STATE', sensitive: false },
        ],
        suspiciousCombinations: [
          'READ_SMS + SEND_SMS + INTERNET (potential exfiltration)',
          'RECORD_AUDIO + ACCESS_FINE_LOCATION (surveillance pattern)',
        ],
        services: ['com.example.suspicious.app.BackgroundTrackerService'],
        receivers: ['com.example.suspicious.app.BootReceiver'],
        domains: ['analytics.example-tracker.com', 'cmd.example-c2.net'],
        risk: 'high',
      })
    }, 2500)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">SpyTrace AI</h2>
        <p className="text-text-secondary">
          Android APK static analysis. Permissions, components, services, and network indicators.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Upload APK" />
            <div className="space-y-4">
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-blue/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept=".apk"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleFileSelect}
                />
                <div className="flex flex-col items-center gap-2">
                  <Smartphone size={32} className="text-text-secondary/50" />
                  <p className="text-sm text-text-main">{file?.name || 'Select an APK file'}</p>
                  <p className="text-xs text-text-secondary/60">Static analysis only</p>
                </div>
              </div>
              {file && (
                <div className="p-3 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Selected file</p>
                  <p className="text-sm text-text-main truncate">{file.name}</p>
                </div>
              )}
              <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                <p className="text-xs text-error">
                  <strong>Static analysis only.</strong> The APK is never executed on this host.
                </p>
              </div>
              <Button
                variant="primary"
                onClick={handleAnalyze}
                disabled={!file || analyzing}
                className="w-full"
              >
                {analyzing ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Analyzing...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Bug size={16} />
                    Run Static Analysis
                  </span>
                )}
              </Button>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {analyzing ? (
            <Card>
              <CardHeader title="Analysis Running" />
              <div className="flex flex-col items-center justify-center py-12">
                <Terminal size={48} className="mb-4 text-primary-cyan" />
                <p className="text-text-secondary">Parsing AndroidManifest.xml and extracting indicators...</p>
              </div>
            </Card>
          ) : result ? (
            <Card>
              <CardHeader title="APK Analysis Results" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <div className="p-4 rounded-lg bg-secondary border border-border">
                    <p className="text-xs text-text-secondary/60">Package</p>
                    <p className="text-sm font-mono text-text-main">{result.packageName}</p>
                    <p className="text-xs text-text-secondary/60">v{result.version} • SDK {result.sdkMin}+</p>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                    <span className="text-sm text-text-main">Risk Classification</span>
                    <Badge variant="error">{result.risk.toUpperCase()}</Badge>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-secondary border border-border">
                    <p className="text-xs font-semibold text-text-secondary/60 mb-2">Requested Permissions</p>
                    {result.permissions.map((p: any, i: number) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="text-text-main">{p.name}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded ${p.sensitive ? 'bg-error/10 text-error' : 'bg-secondary/50 text-text-secondary'}`}>
                          {p.sensitive ? 'Sensitive' : 'Normal'}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="p-3 rounded-lg bg-secondary border border-border">
                    <p className="text-xs font-semibold text-text-secondary/60 mb-2">Suspicious Combinations</p>
                    {result.suspiciousCombinations.map((c: string, i: number) => (
                      <div key={i} className="text-xs text-text-main bg-secondary/30 p-2 rounded border border-border/50">{c}</div>
                    ))}
                  </div>
                  <div className="p-3 rounded-lg bg-secondary border border-border">
                    <p className="text-xs font-semibold text-text-secondary/60 mb-2">Network Indicators</p>
                    {result.domains.map((d: string, i: number) => (
                      <div key={i} className="text-xs text-text-main bg-secondary/30 p-2 rounded border border-border/50">{d}</div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 p-4 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60 mb-2">Explanation</p>
                  <p className="text-sm text-text-main">
                    The app requests sensitive permissions (SMS, location, audio). Permission combinations match common spyware patterns, but sensitive permissions alone do not confirm spyware. Static analysis only — no APK was executed.
                  </p>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={Bug}
              title="No APK analysis yet"
              description="Upload an APK for static analysis. Results show package metadata, permissions, and risk indicators."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
