// =============================================================================
// CYBERSLEUTH AI - API status indicator
// =============================================================================
// Shows whether the backend actually answers, and which address it is
// reached at. Without it a failing login looks like a wrong password, while
// the real problem is that the demo backend is offline or that its tunnel
// address changed.
// =============================================================================

import { useCallback, useEffect, useState } from 'react'
import { Activity, Loader2 } from 'lucide-react'
import { currentApiBase, resolveApiBase } from '@/services/runtimeConfig'

type Status = 'checking' | 'online' | 'offline'

export function ApiStatus() {
  const [status, setStatus] = useState<Status>('checking')
  const [base, setBase] = useState<string | null>(null)

  const check = useCallback(async () => {
    setStatus('checking')
    try {
      const resolved = await resolveApiBase()
      // The resolver falls back to the first candidate when nothing answers,
      // so the health request is repeated here to be certain.
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), 6000)
      const response = await fetch(`${resolved}/health`, {
        cache: 'no-store',
        signal: controller.signal,
      })
      clearTimeout(timer)
      setStatus(response.ok ? 'online' : 'offline')
      setBase(response.ok ? resolved : null)
    } catch {
      setStatus('offline')
      setBase(null)
    }
  }, [])

  useEffect(() => {
    check()
    const timer = setInterval(check, 20000)
    return () => clearInterval(timer)
  }, [check])

  const tone =
    status === 'online'
      ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
      : status === 'offline'
        ? 'text-error border-error/30 bg-error/10'
        : 'text-text-secondary/70 border-white/10 bg-white/5'

  return (
    <div
      className={`mb-4 flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${tone}`}
      role="status"
    >
      {status === 'checking' ? (
        <Loader2 size={14} className="mt-0.5 animate-spin" />
      ) : (
        <Activity size={14} className="mt-0.5" />
      )}
      <div className="min-w-0 flex-1">
        <div className="font-medium">
          {status === 'online'
            ? 'API online'
            : status === 'offline'
              ? 'API unreachable'
              : 'Checking the API ...'}
        </div>
        {status === 'offline' && (
          <div className="mt-0.5 opacity-80">
            The demo backend is not answering at the moment. The supervisor restarts it
            automatically - retry in a few seconds.
          </div>
        )}
        {status === 'online' && base && (
          <div className="mt-0.5 truncate opacity-70">{base}</div>
        )}
      </div>
      <button
        type="button"
        onClick={check}
        className="shrink-0 underline underline-offset-2 opacity-70 hover:opacity-100"
      >
        retry
      </button>
    </div>
  )
}

export function useApiBase() {
  return currentApiBase()
}
