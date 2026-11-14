// =============================================================================
// CYBERSLEUTH AI - VoiceProof AI (Audio Forensics) Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'

import { Button } from '@/ui/Button'
import { Mic, Play, Info } from 'lucide-react'

export function VoiceProofPage() {
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
    // Phase 2: POST to /api/voiceproof/analyze
    setTimeout(() => {
      setAnalyzing(false)
      setResult({
        filename: file.name,
        duration: '02:14',
        sampleRate: '44.1 kHz',
        channels: 'Stereo',
        format: 'WAV',
        findings: [
          { label: 'Waveform', value: 'Normal amplitude distribution', status: 'info' },
          { label: 'Spectrogram', value: 'No obvious synthetic artifacts', status: 'success' },
          { label: 'Synthetic Voice Model', value: 'Inconclusive — below confidence threshold', status: 'warning' },
        ],
      })
    }, 2500)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">VoiceProof AI</h2>
        <p className="text-text-secondary">
          Audio forensics. Waveform, spectrogram, and synthetic voice detection.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Upload Audio" />
            <div className="space-y-4">
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-blue/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept="audio/*"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleFileSelect}
                />
                <div className="flex flex-col items-center gap-2">
                  <Mic size={32} className="text-text-secondary/50" />
                  <p className="text-sm text-text-main">{file?.name || 'Select an audio file'}</p>
                  <p className="text-xs text-text-secondary/60">WAV, MP3, FLAC, M4A</p>
                </div>
              </div>
              {file && (
                <div className="p-3 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">Selected file</p>
                  <p className="text-sm text-text-main truncate">{file.name}</p>
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
                    <Play size={16} />
                    Run Audio Analysis
                  </span>
                )}
              </Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Module Info" />
            <div className="space-y-3 text-xs text-text-secondary/70">
              <p><strong className="text-text-main">Purpose:</strong> Detect anomalies and synthetic speech indicators in audio.</p>
              <p><strong className="text-text-main">Outputs:</strong> Duration, sample rate, channels, waveform, spectrogram, anomaly detection, model confidence.</p>
              <div className="p-3 rounded-lg bg-error/5 border border-error/10">
                <p className="text-xs text-error">
                  <strong>Important:</strong> Does not identify speaker identity. Synthetic voice detection is not conclusive proof. State model limitations clearly.
                </p>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {analyzing ? (
            <Card>
              <CardHeader title="Analysis Running" />
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-32 h-8 bg-secondary rounded-full overflow-hidden mb-4 relative">
                  <div className="absolute left-0 top-0 h-full bg-primary-cyan/50 w-1/3 animate-pulse" />
                  <div className="absolute left-1/3 top-0 h-full bg-primary-blue/30 w-1/3 animate-pulse" style={{ animationDelay: '0.2s' }} />
                  <div className="absolute left-2/3 top-0 h-full bg-primary-cyan/50 w-1/3 animate-pulse" style={{ animationDelay: '0.4s' }} />
                </div>
                <p className="text-text-secondary">Generating waveform and spectrogram...</p>
              </div>
            </Card>
          ) : result ? (
            <Card>
              <CardHeader title="Audio Analysis Results" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <div className="p-4 rounded-lg bg-secondary border border-border">
                    <p className="text-xs text-text-secondary/60">File</p>
                    <p className="text-sm text-text-main truncate">{result.filename}</p>
                    <p className="text-xs text-text-secondary/60">{result.format} • {result.duration}</p>
                    <p className="text-xs text-text-secondary/60">{result.sampleRate} • {result.channels}</p>
                  </div>
                  <div className="bg-secondary border border-border rounded-xl p-4">
                    <p className="text-xs text-text-secondary/60 mb-2">Audio Player</p>
                    <div className="w-full bg-[#080D18] rounded-lg p-3 border border-border">
                      <audio controls className="w-full" />
                    </div>
                    <div className="mt-3 h-1 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-primary-blue to-primary-cyan w-3/4" />
                    </div>
                  </div>
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
              <div className="mt-4 p-4 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60 mb-2">Technical Explanation</p>
                <p className="text-sm text-text-main">
                  Librosa was used to generate waveform and spectrogram visualisations. The synthetic voice model returned a result below the confidence threshold — inconclusive. This is not speaker identification and not proof of synthetic audio.
                </p>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={Mic}
              title="No audio analysis yet"
              description="Upload an audio file to generate waveform, spectrogram, and synthetic voice indicators."
              action={null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
