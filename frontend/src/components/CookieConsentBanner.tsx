// =============================================================================
// PROJECT NEXUS AI - Cookie Consent Banner
// =============================================================================

import { useState, useEffect } from 'react'
import { ShieldCheck } from 'lucide-react'

interface CookiePreferences {
  essential: boolean
  analytics: boolean
  functional: boolean
  marketing: boolean
  consentVersion: string
}

export function CookieConsentBanner() {
  const [showBanner, setShowBanner] = useState(true)
  const [showPreferences, setShowPreferences] = useState(false)

  useEffect(() => {
    // Check if user has already made cookie preferences
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('nexus_cookie_preferences')
      if (!stored) {
        setShowBanner(true)
      }
    }
  }, [])

  const CONSENT_VERSION = '1.0.0'

  const acceptAll = () => {
    const prefs: CookiePreferences = {
      essential: true,
      analytics: true,
      functional: true,
      marketing: false,
      consentVersion: CONSENT_VERSION,
    }
    savePreferences(prefs)
    setShowBanner(false)
    setShowPreferences(false)
  }

  const rejectNonEssential = () => {
    const prefs: CookiePreferences = {
      essential: true,
      analytics: false,
      functional: false,
      marketing: false,
      consentVersion: CONSENT_VERSION,
    }
    savePreferences(prefs)
    setShowBanner(false)
    setShowPreferences(false)
  }

  const savePreferences = (prefs: CookiePreferences) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('nexus_cookie_preferences', JSON.stringify({
        ...prefs,
        consentTimestamp: new Date().toISOString(),
      }))
    }
  }

  const updatePreferences = (prefs: CookiePreferences) => {
    savePreferences(prefs)
    setShowBanner(false)
    setShowPreferences(false)
  }

  if (!showBanner && !showPreferences) return null

  if (showPreferences) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={(e) => {
        if (e.target === e.currentTarget) setShowPreferences(false)
      }}>
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl">
          <h2 className="text-xl font-bold text-white mb-6">Cookie Preferences</h2>
          
          <div className="space-y-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-slate-200">Essential Cookies</h3>
                <p className="text-xs text-slate-500">Required for authentication and security.</p>
              </div>
              <span className="text-xs text-green-400">Always active</span>
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-slate-200">Analytics Cookies</h3>
                <p className="text-xs text-slate-500">Help us improve the application.</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="checkbox sr-only peer" defaultChecked={false} onChange={() => {}} />
                <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-nexus-accent"></div>
              </label>
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-slate-200">Functional Cookies</h3>
                <p className="text-xs text-slate-500">Remember your preferences.</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="checkbox sr-only peer" defaultChecked={false} onChange={() => {}} />
                <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-nexus-accent"></div>
              </label>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-slate-700">
            <button onClick={() => updatePreferences({ essential: true, analytics: false, functional: false, marketing: false, consentVersion: CONSENT_VERSION })} className="btn-ghost w-full">Reject Non-Essential</button>
            <button onClick={() => updatePreferences({ essential: true, analytics: true, functional: true, marketing: false, consentVersion: CONSENT_VERSION })} className="btn-primary w-full">Accept All</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-700 p-6 shadow-2xl">
      <div className="max-w-2xl mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-3">
            <ShieldCheck size={20} className="text-nexus-accent" />
            <div>
              <h3 className="font-semibold text-white">Cookie Consent</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                We use cookies to enhance security, remember preferences, and analyze usage.
                Essential cookies are required for the application to function.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <button onClick={rejectNonEssential} className="btn-secondary text-sm py-2 px-6">
              Reject Non-Essential
            </button>
            <button onClick={acceptAll} className="btn-primary text-sm py-2 px-6">
              Accept All
            </button>
            <button onClick={() => setShowPreferences(true)} className="btn-ghost text-sm py-2 px-6">
              Customize
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
