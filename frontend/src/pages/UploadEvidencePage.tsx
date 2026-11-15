// =============================================================================
// CYBERSLEUTH AI - Upload Evidence Page
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardHeader } from '@/ui/Card'
import { Button } from '@/ui/Button'
import {
  FileScan,
  ChevronLeft,
  FileImage,
  FileVideo,
  FileAudio,
  FileText,
  FileCode,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react'
import { investigationsAPI, evidenceAPI } from '@/services/api'
import { useNavigate } from 'react-router-dom'

const supportedTypes = [
  { label: 'Images', ext: 'JPG, JPEG, PNG, TIFF, WEBP', mimes: ['image/'], icon: FileImage },
  { label: 'Videos', ext: 'MP4, MOV', mimes: ['video/'], icon: FileVideo },
  { label: 'Audio', ext: 'WAV, MP3, M4A', mimes: ['audio/'], icon: FileAudio },
  { label: 'Documents', ext: 'PDF, DOCX, TXT', mimes: ['application/pdf', 'text/'], icon: FileText },
  { label: 'Data', ext: 'JSON, CSV, XML', mimes: ['application/json', 'application/xml', 'text/'], icon: FileCode },
  { label: 'Android', ext: 'APK', mimes: ['application/vnd.android.package-archive'], icon: FileCode },
]

const MAX_SIZE_MB = 100

export function UploadEvidencePage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [investigations, setInvestigations] = useState<any[]>([])
  const [investigationId, setInvestigationId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploaded, setUploaded] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hash, setHash] = useState<string | null>(null)

  useEffect(() => {
    investigationsAPI
      .list()
      .then((res) => setInvestigations(res.data || []))
      .catch(() => setError('Investigations could not be loaded.'))
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0]
      if (f.size > MAX_SIZE_MB * 1024 * 1024) {
        setError(`File exceeds the ${MAX_SIZE_MB} MB limit`)
        return
      }
      setFile(f)
      setError(null)
      setUploaded(null)
      // Client-side SHA-256 is informational; the backend recomputes and is authoritative.
      const reader = new FileReader()
      reader.onload = async () => {
        try {
          const buf = reader.result as ArrayBuffer
          const hashBuffer = await crypto.subtle.digest('SHA-256', buf)
          const hashArray = Array.from(new Uint8Array(hashBuffer))
          setHash(hashArray.map((b) => b.toString(16).padStart(2, '0')).join(''))
        } catch {
          setHash(null)
        }
      }
      reader.readAsArrayBuffer(f)
    }
  }

  const handleUpload = async () => {
    if (!file || !investigationId) return
    setUploading(true)
    setError(null)
    try {
      const res = await evidenceAPI.upload(file, investigationId)
      setUploaded(res.data)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'The upload failed. See the server log for details.')
    } finally {
      setUploading(false)
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
                  aria-label="Choose evidence file"
                />
                <div className="flex flex-col items-center gap-2">
                  <FileScan size={32} className="text-text-secondary/50" />
                  <p className="text-sm text-text-main max-w-[16rem] truncate">
                    {file ? file.name : 'Click to upload evidence'}
                  </p>
                  {hash && (
                    <p className="text-[10px] font-mono text-text-secondary/60 break-all max-w-[16rem]">
                      SHA-256 (client): {hash}
                    </p>
                  )}
                </div>
              </div>
              {file && (
                <div className="p-3 rounded-lg bg-secondary border border-border">
                  <p className="text-xs text-text-secondary/60">File details</p>
                  <p className="text-sm text-text-main">{file.name}</p>
                  <p className="text-xs text-text-secondary/60">
                    {file.type || 'unknown type'} • {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              )}
              <div className="space-y-2">
                <label className="label" htmlFor="upload-investigation">Investigation <span className="text-error">*</span></label>
                <select
                  id="upload-investigation"
                  className="input"
                  value={investigationId}
                  onChange={(e) => setInvestigationId(e.target.value)}
                  required
                >
                  <option value="">Select an investigation…</option>
                  {investigations.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.case_id} — {inv.title}
                    </option>
                  ))}
                </select>
              </div>
              {error && (
                <div className="p-2 rounded-lg bg-error/10 border border-error/20 text-xs text-error flex items-start gap-2">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  {error}
                </div>
              )}
              <Button
                variant="primary"
                onClick={handleUpload}
                disabled={!file || !investigationId || uploading || !!uploaded}
                className="w-full"
              >
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full border-2 border-current text-current h-4 w-4" />
                    Uploading…
                  </span>
                ) : uploaded ? (
                  <span className="flex items-center gap-2 text-success">
                    <ShieldCheck size={16} /> Uploaded & verified
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
          {uploaded ? (
            <Card>
              <CardHeader title="Upload Complete" />
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-success/5 border border-success/20">
                  <p className="text-sm font-semibold text-success flex items-center gap-2">
                    <ShieldCheck size={16} /> Original stored and hash-verified
                  </p>
                  <p className="text-xs text-text-secondary mt-2 break-all font-mono">
                    SHA-256: {uploaded.sha256_hash}
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-secondary border border-border">
                    <p className="text-xs text-text-secondary/60">Evidence ID</p>
                    <p className="text-xs font-mono text-text-main break-all">{uploaded.id}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary border border-border">
                    <p className="text-xs text-text-secondary/60">Status</p>
                    <p className="text-xs text-text-main">{uploaded.status} · {uploaded.mime_type}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button variant="primary" asChild>
                    <Link to={`/investigations/${investigationId}`}>Open Investigation</Link>
                  </Button>
                  <Button variant="secondary" asChild>
                    <Link to="/evidence">Evidence Vault</Link>
                  </Button>
                  <Button variant="cyan" asChild>
                    <Link to="/deeptrace">Analyze with DeepTrace</Link>
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
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
                  <li>SHA-256 computed on upload; the stored object is re-hashed and compared</li>
                  <li>Original file stored in the immutable originals bucket (never rewritten)</li>
                  <li>Append-only chain-of-custody event created automatically</li>
                  <li>Forensic modules process copies, never the original</li>
                </ul>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
