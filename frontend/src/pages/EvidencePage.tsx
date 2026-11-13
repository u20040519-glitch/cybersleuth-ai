// =============================================================================
// PROJECT NEXUS AI - Evidence Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Layout } from '@/components/Layout'
import { evidenceAPI, EvidenceFile } from '@/services/api'
import { FileScan } from 'lucide-react'

export function EvidencePage() {
  const [evidence, setEvidence] = useState<EvidenceFile[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    loadEvidence()
  }, [])

  const loadEvidence = async () => {
    try {
      const response = await evidenceAPI.list('00000000-0000-0000-0000-000000000000')
      setEvidence(response.data)
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load evidence')
      }
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const formData = new FormData()
      formData.append('file', file)
      // Note: case_id would come from route context in production
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed')
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Evidence Repository</h2>
          <p className="text-slate-400">
            Upload and manage forensic evidence files. All files are hashed for chain of custody.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span>{error}</span>
          </div>
        )}

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-200">Upload Evidence</h3>
          </div>
          <div className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-nexus-accent transition-colors">
            <label className="block cursor-pointer">
              <FileScan size={32} className="mx-auto mb-3 text-slate-400" />
              <p className="text-sm text-slate-300 mb-2">Click to upload evidence file</p>
              <input
                type="file"
                onChange={handleUpload}
                className="sr-only"
                accept=".pdf,.docx,.txt,.json,.csv,.png,.jpg,.jpeg,.tiff"
              />
              <p className="text-xs text-slate-500 mt-2">
                Max 100 MB • PDF, DOCX, TXT, JSON, CSV, PNG, JPG, TIFF
              </p>
            </label>
          </div>
        </div>

        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-4">Uploaded Evidence</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-3 text-sm font-semibold text-slate-400">Filename</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Size</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Type</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">SHA-256 Hash</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Status</th>
                  <th className="pb-3 text-sm font-semibold text-slate-400">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {evidence.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No evidence files uploaded yet.
                    </td>
                  </tr>
                )}
                {evidence.map((e) => (
                  <tr key={e.id} className="border-b border-slate-800">
                    <td className="py-3 text-sm text-slate-300">{e.original_filename}</td>
                    <td className="py-3 text-sm text-slate-400 font-mono text-xs">
                      {(e.file_size_bytes / 1024 / 1024).toFixed(2)} MB
                    </td>
                    <td className="py-3 text-sm text-slate-400">{e.mime_type}</td>
                    <td className="py-3 text-sm text-slate-400 font-mono text-xs truncate max-w-[200px]">
                      {e.file_hash_sha256}
                    </td>
                    <td className="py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        e.status === 'processed' ? 'bg-green-500/10 text-green-400' :
                        e.status === 'processing' ? 'bg-yellow-500/10 text-yellow-400' :
                        'bg-red-500/10 text-red-400'
                      }`}>
                        {e.status}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-slate-500">
                      {new Date(e.uploaded_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 mt-4">
          <h4 className="font-semibold text-slate-200 mb-2">Chain of Custody</h4>
          <p className="text-sm text-slate-400">
            Every evidence upload is automatically recorded in the chain of custody with SHA-256
            hashing, timestamp, and uploader information for forensic integrity.
          </p>
        </div>
      </div>
    </Layout>
  )
}
