// =============================================================================
// PROJECT NEXUS AI - Data Deletion Page
// =============================================================================

import { useState } from 'react'
import { Loader2, AlertCircle, ShieldCheck } from 'lucide-react'

export function DataDeletionPage() {
  const [step, setStep] = useState<'request' | 'confirm' | 'complete'>('request')
  const [loading, setLoading] = useState(false)
  const [trackingId, setTrackingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const requestDeletion = async () => {
    setLoading(true)
    try {
      // Simulate - in production call data deletion API
      setTrackingId('NDR-' + Math.random().toString(36).substr(2, 9).toUpperCase())
      setStep('complete')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit deletion request')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-nexus-deeper text-white">
      <header className="border-b border-slate-700 bg-slate-900/50 sticky top-0 z-10 backdrop-blur">
        <div className="flex items-center justify-between px-6 h-12">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-nexus-accent rounded flex items-center justify-center text-nexus-dark text-xs font-bold">N</div>
            <span className="font-bold text-lg">PROJECT NEXUS AI</span>
          </div>
          <a href="/settings/privacy" className="text-sm text-slate-400 hover:text-white">← Back to Settings</a>
        </div>
      </header>

      <div className="max-w-lg mx-auto py-8 px-4">
        {step === 'request' && (
          <article className="space-y-6">
            <header>
              <h1 className="text-2xl font-bold text-white mb-2">Request My Data Deletion</h1>
              <p className="text-slate-400">
                Submit a formal request to delete your account and personal data.
              </p>
            </header>

            <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
              <div className="flex items-start gap-3 mb-4">
                <ShieldCheck size={20} className="text-yellow-400 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-slate-200 mb-1">Important Information</h3>
                  <p className="text-sm text-slate-400">
                    Account deletion is permanent and cannot be undone. Evidence and chain-of-custody
                    records may be retained under documented legal or institutional retention policies.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <p className="text-sm text-slate-300">
                  What will be deleted or anonymized:
                </p>
                <ul className="text-sm text-slate-400 list-disc ml-6 space-y-2">
                  <li>Profile information and account preferences</li>
                  <li>Optional analytics identifiers</li>
                  <li>Application settings</li>
                </ul>
                <p className="text-sm text-slate-400 mt-4">
                  A tracking ID will be provided so you can check the status of your request.
                </p>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={requestDeletion}
              disabled={loading}
              className="btn-danger w-full py-3"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="mr-2 animate-spin" />
                  Submitting Request...
                </>
              ) : (
                'Submit Data Deletion Request'
              )}
            </button>
          </article>
        )}

        {step === 'complete' && trackingId && (
          <article className="text-center space-y-6 py-8">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <ShieldCheck size={32} className="text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Request Submitted</h2>
            <p className="text-slate-400 mb-4">
              Your data deletion request has been received.
            </p>
            <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4 inline-block">
              <p className="text-xs text-slate-500 mb-1">Tracking ID</p>
              <p className="font-mono text-slate-200">{trackingId}</p>
            </div>
            <p className="text-sm text-slate-400">
              You will receive a confirmation email and status updates at your registered email address.
            </p>
          </article>
        )}
      </div>
    </div>
  )
}
