// =============================================================================
// CYBERSLEUTH AI - Evidence Vault Page
// =============================================================================

import { useEffect, useMemo, useState } from 'react'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'
import { FileScan, Search, Filter, FileImage, FileVideo, FileAudio, FileText, FileCode, Download, ShieldCheck } from 'lucide-react'
import { formatBytes, truncateHash, getFileCategory } from '@/utils/format'
import { evidenceAPI } from '@/services/api'

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  image: FileImage,
  video: FileVideo,
  audio: FileAudio,
  document: FileText,
  data: FileCode,
  android: FileCode,
  other: FileText,
}

const CATEGORIES = ['all', 'image', 'video', 'audio', 'document', 'data', 'android']

export function EvidenceVaultPage() {
  const [evidence, setEvidence] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [demo, setDemo] = useState(false)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  useEffect(() => {
    // Phase 2: live list from /api/evidence
    evidenceAPI
      .list()
      .then((res) => {
        setEvidence(res.data || [])
        setLoading(false)
      })
      .catch(() => {
        setDemo(true)
        setLoading(false)
      })
  }, [])

  const filtered = useMemo(
    () =>
      evidence.filter((e) => {
        const name = (e.original_filename || '').toLowerCase()
        const matchesSearch = name.includes(search.toLowerCase())
        const matchesCategory =
          category === 'all' || getFileCategory(e.original_filename || '') === category
        return matchesSearch && matchesCategory
      }),
    [evidence, search, category],
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-text-main">Evidence Vault</h2>
          <p className="text-text-secondary">
            Secure evidence storage with SHA-256 integrity and chain-of-custody tracking.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="primary" asChild>
            <a href="/evidence/upload">
              <FileScan size={16} className="mr-2" />
              Upload Evidence
            </a>
          </Button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary/50" />
          <Input
            label=""
            placeholder="Search evidence files..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="relative">
          <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary/50 pointer-events-none" />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="input pl-9 min-w-[180px]"
            aria-label="Filter by file type"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c === 'all' ? 'All file types' : c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="h-80 flex items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      ) : demo || filtered.length === 0 ? (
        <EmptyState
          icon={FileScan}
          title={demo ? 'Demo mode — no evidence' : 'No evidence files'}
          description={
            demo
              ? 'Connect the backend in Phase 2 to view real evidence with integrity status.'
              : search || category !== 'all'
                ? 'No files match your search or filter.'
                : 'Upload your first evidence file to begin.'
          }
          action={
            <Button variant="primary" asChild>
              <a href="/evidence/upload">
                <FileScan size={16} className="mr-2" />
                Upload Evidence
              </a>
            </Button>
          }
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse border-border">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">File</th>
                <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Type</th>
                <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase text-right">Size</th>
                <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Hash (SHA-256)</th>
                <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Status</th>
                <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => {
                const Icon = CATEGORY_ICONS[getFileCategory(e.original_filename || '')] ?? FileText
                return (
                  <tr key={e.id} className="border-b border-border/50 hover:bg-secondary/30 transition-colors">
                    <td className="py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center text-text-secondary">
                          <Icon size={14} />
                        </div>
                        <div>
                          <p className="text-sm text-text-main">{e.original_filename}</p>
                          <p className="text-xs text-text-secondary/60">{e.mime_type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 text-xs text-text-secondary">{getFileCategory(e.original_filename || '')}</td>
                    <td className="py-4 text-xs text-text-secondary text-right">{formatBytes(e.file_size)}</td>
                    <td className="py-4">
                      <div className="text-xs font-mono text-text-secondary">{truncateHash(e.sha256_hash, 20)}</div>
                    </td>
                    <td className="py-4">
                      <Badge variant="success">
                        <ShieldCheck size={12} className="mr-1" />
                        {e.status}
                      </Badge>
                    </td>
                    <td className="py-4 text-right">
                      <Button variant="ghost" size="sm">
                        <Download size={14} className="mr-1" />
                        Download
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
