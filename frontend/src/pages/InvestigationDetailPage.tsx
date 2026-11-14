// =============================================================================
// CYBERSLEUTH AI - Investigation Detail Page
// =============================================================================

import { useParams } from 'react-router-dom'
import { Card, CardHeader } from '@/ui/Card'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { FileText, ChevronLeft, ShieldCheck, FileScan, Activity, Users } from 'lucide-react'
export function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>()

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
          <h2 className="text-2xl font-bold text-text-main">Investigation Details</h2>
          <p className="text-text-secondary">
            Case ID: <span className="font-mono text-text-secondary/60">{id}</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <Card>
            <CardHeader title="Overview" />
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                <div>
                  <p className="text-xs text-text-secondary/60">Case ID</p>
                  <p className="text-sm font-mono text-text-main">{id}</p>
                </div>
                <Badge variant="info">Active</Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                <div>
                  <p className="text-xs text-text-secondary/60">Title</p>
                  <p className="text-sm text-text-main">Digital Evidence Analysis</p>
                </div>
                <Badge variant={['high', 'critical'].includes('high') ? 'error' : 'info'}>High</Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border">
                <div>
                  <p className="text-xs text-text-secondary/60">Category</p>
                  <p className="text-sm text-text-main">Cyber Intrusion</p>
                </div>
                <span className="text-xs text-text-secondary">Malware</span>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Evidence" />
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border group hover:bg-secondary/50 cursor-pointer">
                <div className="flex items-center gap-3">
                  <FileScan size={18} className="text-primary-cyan" />
                  <div>
                    <p className="text-sm text-text-main">Surveillance Footage.mp4</p>
                    <p className="text-xs text-text-secondary/60">Video • 2.4 GB • SHA-256 verified</p>
                  </div>
                </div>
                <Badge variant="success">Analyzed</Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border group hover:bg-secondary/50 cursor-pointer">
                <div className="flex items-center gap-3">
                  <FileText size={18} className="text-primary-blue" />
                  <div>
                    <p className="text-sm text-text-main">Chat_Export.json</p>
                    <p className="text-xs text-text-secondary/60">JSON • 452 KB • Pending analysis</p>
                  </div>
                </div>
                <Badge variant="warning">Pending</Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary border border-border group hover:bg-secondary/50 cursor-pointer">
                <div className="flex items-center gap-3">
                  <ShieldCheck size={18} className="text-primary-blue" />
                  <div>
                    <p className="text-sm text-text-main">Mobile_App.apk</p>
                    <p className="text-xs text-text-secondary/60">Android APK • 18 MB • Queued</p>
                  </div>
                </div>
                <Badge variant="info">Queued</Badge>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="Case Actions" />
            <div className="space-y-3">
              <Button variant="primary" className="w-full" asChild>
                <a href="/evidence/upload">
                  <FileScan size={16} className="mr-2" />
                  Upload Evidence
                </a>
              </Button>
              <Button variant="cyan" className="w-full" asChild>
                <a href="/deeptrace">
                  <ShieldCheck size={16} className="mr-2" />
                  Run DeepTrace AI
                </a>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <a href="/spytrace">
                  <Activity size={16} className="mr-2" />
                  Run SpyTrace AI
                </a>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <a href="/voiceproof">
                  <FileText size={16} className="mr-2" />
                  Run VoiceProof AI
                </a>
              </Button>
              <Button variant="secondary" className="w-full" asChild>
                <a href="/cybersleuth">
                  <Users size={16} className="mr-2" />
                  Run CyberSleuth AI
                </a>
              </Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Quick Links" />
            <div className="space-y-3">
              <Button variant="ghost" className="w-full text-left" asChild>
                <a href="/correlation">
                  <Activity size={16} className="mr-2" />
                  View Correlation Timeline
                </a>
              </Button>
              <Button variant="ghost" className="w-full text-left" asChild>
                <a href="/reports">
                  <FileText size={16} className="mr-2" />
                  Generate Forensic Report
                </a>
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
