// =============================================================================
// CYBERSLEUTH AI - DeepTrace AI (Image & Video Forensics) Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'

import { Button } from '@/ui/Button'
import { Image, FileImage, Play, ShieldAlert, Info } from 'lucide-react'

export function DeepTracePage() {
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
    // Phase 2: POST to /api/deeptrace/analyze, poll /api/analysis/:id/status
    setTimeout(() => {
      setAnalyzing(false)
      setResult({
        type: 'image',
        filename: file.name,
        sha256: 'a1b2c3d4e5f6...',
        dimensions: '1920 × 1080',
        mime: 'image/jpeg',
        findings: [
          { label: 'Metadata', value: 'Standard EXIF present', status: 'info' },
          { label: 'Compression', value: 'Inconsistent ELA levels detected', status: 'warning' },
          { label: 'Deepfake Model', value: 'No conclusive synthetic indicators', status: 'success' },
        ],
      })
    }, 2500)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">DeepTrace AI</h2>
        <p className="text-text-secondary">
          Image and video forensics. Metadata extraction, frame analysis, and manipulation detection.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload panel */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Upload Evidence" />
            <div className="space-y-4">
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-blue/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept="image/*,video/*"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleFileSelect}
                />
                <div className="flex flex-col items-center gap-2">
                  {file ? (
                    <FileImage size={32} className="text-primary-cyan" />
                  ) : (
                    <Image size={32} className="text-text-secondary/50" />
                  )}
                  <p className="text-sm text-text-main">{file?.name || 'Click to upload image or video'}</p>
                  <p className="text-xs text-text-secondary/60">JPG, PNG, MP4, MOV, AVI, MKV</p>
                </div>
              </div>
              {file && (
                <div className="p-3 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Selected file</p>
                  <p className="text-sm text-text-main truncate">{file.name}</p>
                  <p className="text-xs text-text-secondary/60">{((file.size / 1024 / 1024) * 100).toFixed(2)} MB</p>
                </div>
              )}
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
                    <ShieldAlert size={16} />
                    Run Forensic Analysis
                  </span>
                )}
              </Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Module Info" />
            <div className="space-y-3 text-xs text-text-secondary/70">
              <p><strong className="text-text-main">Purpose:</strong> Detect manipulation in images and video.</p>
              <p><strong className="text-text-main">Outputs:</strong> Metadata, frame thumbnails, manipulation indicators, confidence scores (model-calibrated only).</p>
              <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                <p className="text-xs text-error">
                  <strong>Important:</strong> Unusual metadata does not mean deepfake. Model predictions are clearly distinguished from heuristic checks.
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Results panel */}
        <div className="lg:col-span-2">
          {analyzing ? (
            <Card>
              <CardHeader title="Analysis Running" />
              <div className="flex flex-col items-center justify-center py-12">
                <div className="relative w-32 h-32 mb-4">
                  <Play size={48} className="absolute inset-0 flex items-center justify-center text-primary-cyan bg-[#080D18]/50 rounded-full" />
                  <div className="absolute inset-0 border-4 border-primary-blue/20 rounded-full animate-spin" />
                </div>
                <p className="text-text-secondary">Extracting frames and running forensic checks...</p>
              </div>
            </Card>
          ) : result ? (
            <Card>
              <CardHeader title="Analysis Results" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-secondary border border-border rounded-xl p-4">
                  <p className="text-xs text-text-secondary/60 mb-2">Evidence</p>
                  <p className="text-sm text-text-main truncate">{result.filename}</p>
                  <p className="text-xs text-text-secondary/60">{result.sha256}</p>
                  <p className="text-xs text-text-secondary/60">{result.dimensions} • {result.mime}</p>
                </div>
                <div className="space-y-3">
                  {result.findings.map((f: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                      <div className="flex items-center gap-3">
                        <Info size={16} className="text-text-secondary/50" />
                        <p className="text-sm text-text-main">{f.label}</p>
                      </div>
                      <Badge variant={f.status === 'warning' ? 'warning' : f.status === 'error' ? 'error' : f.status === 'success' ? 'success' : 'info'}>
                        {f.value}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-6 p-4 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60 mb-2">Technical Explanation</p>
                <p className="text-sm text-text-main">
                  Error Level Analysis (ELA) was performed to detect re-saving and manipulation. No calibrated deepfake model produced a conclusive synthetic indicator. Findings above are heuristic observations pending investigator review.
                </p>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={ShieldAlert}
              title="No analysis yet"
              description="Upload an image or video and run forensic analysis to see results here."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
