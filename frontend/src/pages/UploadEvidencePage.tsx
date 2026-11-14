// =============================================================================
// CYBERSLEUTH AI - Upload Evidence Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'

import { Button } from '@/ui/Button'
import { FileScan, ChevronLeft, FileImage, FileVideo, FileAudio, FileText, FileCode } from 'lucide-react'

const supportedTypes = [
  { label: 'Images', ext: 'JPG, JPEG, PNG, WEBP', icon: FileImage },
  { label: 'Videos', ext: 'MP4, MOV, AVI, MKV', icon: FileVideo },
  { label: 'Audio', ext: 'WAV, MP3, FLAC, M4A', icon: FileAudio },
  { label: 'Documents', ext: 'PDF, DOCX, TXT', icon: FileText },
  { label: 'Data', ext: 'JSON, CSV, XML, EML', icon: FileCode },
  { label: 'Android', ext: 'APK', icon: FileCode },
]

export function UploadEvidencePage() {
  const [file, setFile] = useState<File | null>(null)
  const [investigationId, setInvestigationId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploaded, setUploaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hash, setHash] = useState<string | null>(null)

  const MAX_SIZE_MB = 500

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0]
      if (f.size > MAX_SIZE_MB * 1024 * 1024) {
        setError(`File exceeds ${MAX_SIZE_MB} MB limit`)
        return
      }
      setFile(f)
      setError(null)
      setUploaded(false)
      // Calculate SHA-256 (Phase 2: backend also verifies)
      const reader = new FileReader()
      reader.onload = async () => {
        const buf = reader.result as ArrayBuffer
        const hashBuffer = await crypto.subtle.digest('SHA-256', buf)
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        setHash(hashArray.map((b) => b.toString(16).padStart(2, '0')).join(''))
      }
      reader.readAsArrayBuffer(f)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    // Phase 2: POST FormData to /api/evidence/upload with investigation_id
    setTimeout(() => {
      setUploading(false)
      setUploaded(true)
    }, 1500)
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
          <h2 className="text-2xl font-bold text-text-main">Upload Evidence</h2>
          <p className="text-text-secondary">
            Secure upload with SHA-256 hash and chain-of-custody tracking.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Select File" />
            <div className="space-y-4">
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-blue/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleFileSelect}
                />
                <div className="flex flex-col items-center gap-2">
                  <FileScan size={32} className="text-text-secondary/50" />
                  <p className="text-sm text-text-main">
                    {file ? file.name : 'Click to upload evidence'}
                  </p>
                  {hash && (
                    <p className="text-xs font-mono text-text-secondary/60 truncate max-w-[200px]">
                      SHA-256: {hash}
                    </p>
                  )}
                </div>
              </div>
              {file && (
                <div className="p-3 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">File details</p>
                  <p className="text-sm text-text-main">{file.name}</p>
                  <p className="text-xs text-text-secondary/60">
                    {file.type} • {((file.size / 1024 / 1024) * 100).toFixed(2)} MB
                  </p>
                </div>
              )}
              <div className="space-y-2">
                <label className="label">Associate with Investigation (optional)</label>
                <input
                  type="text"
                  placeholder="Case ID or Investigation ID"
                  className="input"
                  value={investigationId}
                  onChange={(e) => setInvestigationId(e.target.value)}
                />
              </div>
              {error && (
                <div className="p-2 rounded-lg bg-error/10 border border-error/20 text-xs text-error">
                  {error}
                </div>
              )}
              <Button
                variant="primary"
                onClick={handleUpload}
                disabled={!file || uploading || uploaded}
                className="w-full"
              >
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Uploading...
                  </span>
                ) : uploaded ? (
                  <span className="flex items-center gap-2 text-success">
                    <span className="text-success">✓</span> Uploaded
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <FileScan size={16} /> Upload Evidence
                  </span>
                )}
              </Button>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardHeader title="Supported File Types" />
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {supportedTypes.map((t) => (
                <div key={t.label} className="flex items-center gap-3 p-3 rounded-lg bg-secondary border border-border">
                  <t.icon size={16} className="text-primary-cyan" />
                  <div>
                    <p className="text-sm text-text-main">{t.label}</p>
                    <p className="text-xs text-text-secondary/60">{t.ext}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-5 p-4 rounded-lg bg-secondary/50 border border-border/50">
              <p className="text-xs font-semibold text-text-secondary/60 uppercase mb-2">Integrity &amp; Custody</p>
              <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
                <li>SHA-256 hash calculated before upload</li>
                <li>Original file stored in private storage (never modified)</li>
                <li>Chain-of-custody event created on upload</li>
                <li>Processed files and thumbnails stored separately</li>
              </ul>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
