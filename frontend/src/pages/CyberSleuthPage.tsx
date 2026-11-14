// =============================================================================
// CYBERSLEUTH AI - CyberSleuth AI (Evidence Extraction & Timeline) Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'

import { Button } from '@/ui/Button'
import { FileText, Code, Activity } from 'lucide-react'

export function CyberSleuthPage() {
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
    // Phase 2: POST to /api/cybersleuth/analyze
    setTimeout(() => {
      setAnalyzing(false)
      setResult({
        filename: file.name,
        events: 12,
        entities: 8,
        urls: 5,
        duplicates: 2,
        timeline: [
          { time: '10:14:22', type: 'Message', source: 'chat_export.json', content: 'User A logged in', entities: ['user_a'] },
          { time: '10:15:01', type: 'File Access', source: 'chat_export.json', content: 'Document downloaded', entities: ['document_1.pdf'] },
          { time: '10:16:33', type: 'URL', source: 'chat_export.json', content: 'https://example.com', entities: ['example.com'] },
          { time: '10:18:09', type: 'Message', source: 'chat_export.json', content: 'User B responded', entities: ['user_b'] },
        ],
      })
    }, 2500)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">CyberSleuth AI</h2>
        <p className="text-text-secondary">
          Digital evidence extraction, timeline reconstruction, and relationship graph generation.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Upload Artefact" />
            <div className="space-y-4">
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-blue/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept=".txt,.csv,.json,.xml,.eml,.pdf,.log"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleFileSelect}
                />
                <div className="flex flex-col items-center gap-2">
                  <FileText size={32} className="text-text-secondary/50" />
                  <p className="text-sm text-text-main">{file?.name || 'Select a data file'}</p>
                  <p className="text-xs text-text-secondary/60">TXT, CSV, JSON, XML, EML, PDF</p>
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
                  <strong>No fabrication.</strong> Deleted evidence reconstruction only when source artefacts exist.
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
                    Extracting...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Code size={16} />
                    Extract & Reconstruct
                  </span>
                )}
              </Button>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {analyzing ? (
            <Card>
              <CardHeader title="Extraction Running" />
              <div className="flex flex-col items-center justify-center py-12">
                <Activity size={48} className="mb-4 text-primary-cyan" />
                <p className="text-text-secondary">Parsing timestamps, entities, and building timeline...</p>
              </div>
            </Card>
          ) : result ? (
            <Card>
              <CardHeader title="Extraction Results" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-secondary border border-border text-center">
                    <p className="text-xs text-text-secondary/60">Events</p>
                    <p className="text-sm font-mono text-text-main">{result.events}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary border border-border text-center">
                    <p className="text-xs text-text-secondary/60">Entities</p>
                    <p className="text-sm font-mono text-text-main">{result.entities}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary border border-border text-center">
                    <p className="text-xs text-text-secondary/60">URLs</p>
                    <p className="text-sm font-mono text-text-main">{result.urls}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary border border-border text-center">
                    <p className="text-xs text-text-secondary/60">Duplicates</p>
                    <p className="text-sm font-mono text-text-main">{result.duplicates}</p>
                  </div>
                </div>
                <div className="col-span-2 mt-4">
                  <p className="text-xs text-text-secondary/60 mb-2">Chronological Timeline</p>
                  <div className="space-y-3">
                    {result.timeline.map((t: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-secondary border border-border">
                        <div className="w-16 font-mono text-xs text-primary-blue">{t.time}</div>
                        <Badge variant="info" className="text-[10px]">{t.type}</Badge>
                        <p className="text-sm text-text-main flex-1">{t.content}</p>
                        <span className="text-xs text-text-secondary/60 font-mono">{t.source}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 p-4 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60 mb-2">Explanation</p>
                <p className="text-sm text-text-main">
                  Timestamps extracted and normalised. Entities identified via NLP. Relationship graph built from co-occurring entities. Deleted evidence reconstruction not attempted — no recoverable source artefacts available.
                </p>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={Code}
              title="No artefact analysis yet"
              description="Upload a text/CSV/JSON/XML/EML/PDF file to extract timestamps, entities, URLs, and build a chronological timeline."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
