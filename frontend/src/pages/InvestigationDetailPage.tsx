// =============================================================================
// CYBERSLEUTH AI - Investigation Detail Page
// =============================================================================

import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { LoadingSpinner } from '@/ui/LoadingSpinner'
import {
  FileText,
  ChevronLeft,
  FileScan,
  Activity,
  Users,
  AlertCircle,
  Download,
  ShieldCheck,
  ScanLine,
} from 'lucide-react'
import { investigationsAPI } from '@/services/api'
import { formatBytes, formatDateTime, truncateHash } from '@/utils/format'

function priorityVariant(priority?: string): 'success' | 'warning' | 'error' | 'info' {
  const key = (priority || '').toLowerCase()
  if (key === 'critical' || key === 'high') return 'error'
  if (key === 'medium') return 'warning'
  if (key === 'low') return 'success'
  return 'info'
}

export function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    investigationsAPI
      .get(id)
      .then((res) => {
        setDetail(res.data)
        setLoading(false)
      })
      .catch(() => {
        setError('This investigation could not be loaded, or you do not have access to it.')
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <LoadingSpinner size="md" />
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle size={32} className="text-error" />
        <p className="text-sm text-error">{error}</p>
        <Button variant="secondary" onClick={() => navigate('/investigations')}>
          Back to Investigations
        </Button>
      </div>
    )
  }

  const evidence: any[] = Array.isArray(detail.evidence) ? detail.evidence : []
  const analyses: any[] = Array.isArray(detail.analysis) ? detail.analysis : []
  const members: any[] = Array.isArray(detail.members) ? detail.members : []

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
          <h2 className="text-2xl font-bold text-text-main">{detail.title}</h2>
          <p className="text-text-secondary">
            Case ID: <span className="font-mono text-text-secondary/60">{detail.case_id}</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          {/* Overview */}
          <Card>
            <CardHeader title="Overview" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60">Status</p>
                <Badge variant="info" className="mt-1">{detail.status}</Badge>
              </div>
              <div className="p-3 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60">Priority</p>
                <Badge variant={priorityVariant(detail.priority)} className="mt-1">{detail.priority}</Badge>
              </div>
              <div className="p-3 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60">Category</p>
                <p className="text-sm text-text-main">{detail.category}</p>
              </div>
              <div className="p-3 rounded-lg bg-secondary border border-border">
                <p className="text-xs text-text-secondary/60">Owner</p>
                <p className="text-sm text-text-main">{detail.owner_name ?? 'You'}</p>
              </div>
              {detail.description && (
                <div className="p-3 rounded-lg bg-secondary border border-border md:col-span-2">
                  <p className="text-xs text-text-secondary/60">Description</p>
                  <p className="text-sm text-text-main leading-relaxed">{detail.description}</p>
                </div>
              )}
              {detail.notes && (
                <div className="p-3 rounded-lg bg-secondary border border-border md:col-span-2">
                  <p className="text-xs text-text-secondary/60">Notes</p>
                  <p className="text-sm text-text-main">{detail.notes}</p>
                </div>
              )}
            </div>
          </Card>

          {/* Evidence */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <CardHeader
                title="Evidence"
                subtitle={`${evidence.length} item(s) · all hash-verified at intake`}
                className="mb-0"
              />
              <Button variant="primary" size="sm" asChild>
                <Link to="/evidence/upload">
                  <FileScan size={14} className="mr-1" /> Upload
                </Link>
              </Button>
            </div>
            {evidence.length === 0 ? (
              <p className="text-sm text-text-secondary/60 py-4 text-center">
                No evidence has been uploaded for this investigation yet.
              </p>
            ) : (
              <div className="space-y-2">
                {evidence.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg bg-secondary border border-border"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <FileScan size={18} className="text-primary-cyan shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm text-text-main truncate">{item.original_filename}</p>
                        <p className="text-[10px] font-mono text-text-secondary/60">
                          {truncateHash(item.sha256_hash, 20)} · {formatBytes(item.file_size)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={item.status === 'analyzed' ? 'success' : 'info'}>{item.status}</Badge>
                      <Button variant="ghost" size="sm" asChild>
                        <Link to="/evidence" aria-label="Open evidence vault">
                          <Download size={14} />
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Analysis results */}
          <Card>
            <CardHeader title="Analysis Results" subtitle={`${analyses.length} module run(s)`} />
            {analyses.length === 0 ? (
              <p className="text-sm text-text-secondary/60 py-4 text-center">
                No module has been run yet. Use the module pages above to analyse the evidence.
              </p>
            ) : (
              <div className="space-y-2">
                {analyses.map((a) => (
                  <div key={a.id} className="flex items-center justify-between gap-3 p-3 rounded-lg bg-secondary border border-border">
                    <div className="flex items-center gap-3 min-w-0">
                      <ScanLine size={16} className="text-primary-blue shrink-0" />
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-text-main uppercase tracking-wider">{a.module}</p>
                        <p className="text-[10px] text-text-secondary/60">{formatDateTime(a.completed_at ?? a.created_at)}</p>
                      </div>
                    </div>
                    <Badge variant={a.status === 'completed' ? 'success' : a.status === 'failed' ? 'error' : 'warning'}>
                      {a.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right rail */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader title="Case Actions" />
            <div className="space-y-3">
              <Button variant="primary" className="w-full" asChild>
                <Link to="/evidence/upload">
                  <FileScan size={16} className="mr-2" />
                  Upload Evidence
                </Link>
              </Button>
              <Button variant="cyan" className="w-full" asChild>
                <Link to="/deeptrace">
                  <ShieldCheck size={16} className="mr-2" />
                  Run DeepTrace AI
                </Link>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <Link to="/spytrace">
                  <Activity size={16} className="mr-2" />
                  Run SpyTrace AI
                </Link>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <Link to="/voiceproof">
                  <Activity size={16} className="mr-2" />
                  Run VoiceProof AI
                </Link>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <Link to="/cybersleuth">
                  <Activity size={16} className="mr-2" />
                  Run CyberSleuth AI
                </Link>
              </Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Quick Links" />
            <div className="space-y-3">
              <Button variant="ghost" className="w-full text-left justify-start" asChild>
                <Link to="/correlation">
                  <Activity size={16} className="mr-2" />
                  Run Correlation
                </Link>
              </Button>
              <Button variant="ghost" className="w-full text-left justify-start" asChild>
                <Link to="/reports">
                  <FileText size={16} className="mr-2" />
                  Generate Forensic Report
                </Link>
              </Button>
              <Button variant="ghost" className="w-full text-left justify-start" asChild>
                <Link to="/audit-logs">
                  <Users size={16} className="mr-2" />
                  Audit Logs
                </Link>
              </Button>
            </div>
          </Card>

          {members.length > 0 && (
            <Card>
              <CardHeader title="Members" subtitle={`${members.length} authorised user(s)`} />
              <div className="space-y-2">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-secondary border border-border">
                    <div className="min-w-0">
                      <p className="text-xs text-text-main truncate">{m.user_name ?? m.user_email}</p>
                      <p className="text-[10px] text-text-secondary/60">{m.user_email}</p>
                    </div>
                    <Badge variant="info" className="text-[10px]">{m.member_role}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
