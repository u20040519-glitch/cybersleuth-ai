// =============================================================================
// PROJECT NEXUS AI - Onboarding Page
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { Loader2, AlertCircle, CheckCircle, ArrowRight, Mail, ShieldCheck } from 'lucide-react'

const steps = [
  { id: 'welcome', title: 'Welcome', description: 'Introduction to PROJECT NEXUS AI' },
  { id: 'profile', title: 'Profile Setup', description: 'Your name, institution, and role' },
  { id: 'privacy', title: 'Privacy & Security', description: 'Evidence preservation and data handling' },
  { id: 'ai-prefs', title: 'AI Preferences', description: 'External AI processing consent' },
  { id: 'dashboard', title: 'Dashboard Tour', description: 'ECHO, MOSAIC, TIMEGLASS, AI Assistant' },
  { id: 'first-case', title: 'First Case', description: 'Create your first investigation case' },
  { id: 'complete', title: 'Complete', description: 'Onboarding finished' },
]

export function OnboardingPage() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    full_name: '',
    institution: '',
    role: '',
    forensic_interest: '',
    ai_processing_enabled: false,
  })

  const isLastStep = currentStep === steps.length - 1

  const nextStep = async () => {
    if (currentStep === 1) {
      // Save profile on step 2
      setLoading(true)
      try {
        // In production, call onboardingAPI.setupProfile
        setCurrentStep((prev) => prev + 1)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to save profile')
      } finally {
        setLoading(false)
      }
    } else if (isLastStep) {
      setLoading(true)
      try {
        // Complete onboarding
        navigate('/dashboard', { replace: true })
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to complete onboarding')
      } finally {
        setLoading(false)
      }
    } else {
      setCurrentStep((prev) => prev + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 0) setCurrentStep((prev) => prev - 1)
  }

  const step = steps[currentStep]

  return (
    <Layout>
      <div className="max-w-2xl mx-auto py-8">
        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm text-slate-400">
              Step {currentStep + 1} of {steps.length}
            </span>
          </div>
          <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-nexus-accent transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {isLastStep ? (
          <div className="card text-center py-12">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle size={32} className="text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Onboarding Complete</h2>
            <p className="text-slate-400 mb-6">
              You&rsquo;re ready to start using PROJECT NEXUS AI.
            </p>
            <button
              onClick={() => navigate('/dashboard', { replace: true })}
              className="btn-primary"
            >
              Go to Dashboard <ArrowRight size={18} />
            </button>
          </div>
        ) : (
          <div className="card p-8">
            <h2 className="text-xl font-bold text-white mb-2">{step.title}</h2>
            <p className="text-slate-400 mb-6">{step.description}</p>

            {/* Step Content */}
            {currentStep === 0 && (
              <div className="space-y-6">
                <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
                  <h3 className="font-semibold text-slate-200 mb-3">About PROJECT NEXUS AI</h3>
                  <p className="text-sm text-slate-300 mb-3">
                    PROJECT NEXUS AI is a secure, privacy-conscious AI-assisted digital forensic
                    investigation platform designed for academic demonstration and controlled development.
                  </p>
                  <ul className="text-sm text-slate-400 space-y-2 ml-6">
                    <li>• ECHO - Evidence Gap Discovery</li>
                    <li>• MOSAIC - Scenario Reconstruction</li>
                    <li>• TIMEGLASS - Temporal Analysis</li>
                    <li>• NEXUS AI Forensic Chatbot</li>
                    <li>• Evidence Repository with Chain of Custody</li>
                    <li>• Forensic Report Generation</li>
                  </ul>
                </div>
              </div>
            )}

            {currentStep === 1 && (
              <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                <div>
                  <label className="label">Full Name</label>
                  <input
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    placeholder="Jane Investigator"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Institution / Organization (optional)</label>
                  <input
                    value={formData.institution}
                    onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
                    placeholder="University or Lab"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Role</label>
                  <input
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    placeholder="e.g., Forensic Analyst"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Area of Forensic Interest (optional)</label>
                  <input
                    value={formData.forensic_interest}
                    onChange={(e) => setFormData({ ...formData, forensic_interest: e.target.value })}
                    placeholder="e.g., Network Forensics"
                    className="input"
                  />
                </div>
              </form>
            )}

            {currentStep === 2 && (
              <div className="space-y-6">
                <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
                  <h3 className="font-semibold text-slate-200 mb-3">Privacy & Security</h3>
                  <ul className="text-sm text-slate-300 space-y-3">
                    <li>
                      <ShieldCheck size={16} className="mr-2 text-green-400" />
                      Evidence is preserved with SHA-256 hashing and chain of custody records
                    </li>
                    <li>
                      <Mail size={16} className="mr-2 text-blue-400" />
                      AI processing may use external Gemini API - you control this consent
                    </li>
                    <li>
                      <span className="text-red-400">⚠</span>{' '}
                      Case data is private to you and authorized users only
                    </li>
                    <li>
                      <span className="text-yellow-400">ℹ</span>{' '}
                      You can delete your account and request data deletion at any time
                    </li>
                  </ul>
                </div>
              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-6">
                <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
                  <h3 className="font-semibold text-slate-200 mb-3">AI Processing Preferences</h3>
                  <p className="text-sm text-slate-400 mb-4">
                    Choose whether to enable optional external AI processing for forensic analysis.
                  </p>
                  <div className="flex items-start gap-3">
                    <input
                      id="ai-processing"
                      type="checkbox"
                      checked={formData.ai_processing_enabled}
                      onChange={(e) =>
                        setFormData({ ...formData, ai_processing_enabled: e.target.checked })
                      }
                      className="checkbox mt-0.5"
                    />
                    <label className="text-sm text-slate-300 leading-snug">
                      Enable external AI processing (Gemini API) for forensic analysis
                    </label>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    Optional. Core application functionality works without AI processing.
                  </p>
                </div>
              </div>
            )}

            {currentStep === 4 && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { name: 'ECHO', desc: 'Evidence Gap Discovery', icon: '🔍' },
                    { name: 'MOSAIC', desc: 'Scenario Reconstruction', icon: '🧩' },
                    { name: 'TIMEGLASS', desc: 'Temporal Analysis', icon: '⏱️' },
                    { name: 'NEXUS AI', desc: 'Forensic Chatbot', icon: '🤖' },
                  ].map((m) => (
                    <div key={m.name} className="p-4 bg-slate-900/50 border border-slate-700 rounded-lg">
                      <div className="text-2xl mb-2">{m.icon}</div>
                      <h4 className="font-semibold text-slate-200">{m.name}</h4>
                      <p className="text-xs text-slate-400">{m.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {currentStep === 5 && (
              <div className="space-y-6">
                <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
                  <h3 className="font-semibold text-slate-200 mb-3">Create Your First Case</h3>
                  <p className="text-sm text-slate-300 mb-4">
                    Create a sample or authorized investigation case to begin using the platform.
                  </p>
                  <div className="space-y-3">
                    <input
                      placeholder="Case Number (e.g., CASE-2026-001)"
                      className="input w-full"
                    />
                    <input placeholder="Case Title" className="input w-full" />
                    <button className="btn-primary w-full">Create Case</button>
                  </div>
                  <p className="text-xs text-slate-500 mt-3">
                    You can also skip this and create cases later from the dashboard.
                  </p>
                </div>
              </div>
            )}

            <div className="mt-8 flex justify-between items-center">
              {currentStep > 0 && (
                <button
                  onClick={prevStep}
                  className="btn-ghost"
                >
                  <ArrowRight size={16} className="-rotate-180 mr-2" />
                  Previous
                </button>
              )}
              <button
                onClick={nextStep}
                disabled={loading}
                className="btn-primary"
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="mr-2 animate-spin" />
                    Processing...
                  </>
                ) : isLastStep ? (
                  'Complete'
                ) : (
                  <>
                    Next <ArrowRight size={16} className="ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
