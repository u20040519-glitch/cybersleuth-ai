// =============================================================================
// PROJECT NEXUS AI - Terms of Service Page
// =============================================================================

export function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-nexus-deeper text-white">
      <header className="border-b border-slate-700 bg-slate-900/50 sticky top-0 z-10 backdrop-blur">
        <div className="flex items-center justify-between px-6 h-12">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-nexus-accent rounded flex items-center justify-center text-nexus-dark text-xs font-bold">N</div>
            <span className="font-bold text-lg">PROJECT NEXUS AI</span>
          </div>
          <a href="/" className="text-sm text-slate-400 hover:text-white">← Back to Home</a>
        </div>
      </header>

      <div className="max-w-3xl mx-auto py-8 px-4">
        <article className="space-y-6">
          <header className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Terms of Service</h1>
            <p className="text-slate-400">
              Effective Date: <span className="font-mono">2026-11-13</span> | Version: <span className="font-mono">1.0.0</span>
            </p>
          </header>

          <section className="bg-slate-900/50 border border-slate-700 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-red-400 mb-3">Important Disclaimer</h2>
            <p className="text-slate-300 leading-relaxed">
              <strong>PROJECT NEXUS AI is an AI-assisted forensic research and investigation support application.</strong>
              It does <strong>not</strong> replace qualified forensic examiners, independent evidence verification,
              professional judgment, legal advice, or validated forensic acquisition procedures.
            </p>
            <p className="text-slate-300 leading-relaxed">
              AI-generated findings must be independently reviewed. We do not guarantee that AI analysis
              is accurate, legally admissible, or conclusive.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">1. Acceptance of Terms</h2>
            <p className="text-slate-300 leading-relaxed">
              By accessing or using PROJECT NEXUS AI, you agree to these Terms of Service. If you do not
              agree, you may not use the application.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">2. Eligibility</h2>
            <p className="text-slate-300 leading-relaxed">
              You must be at least 13 years old to use this application. For academic use, institutional
              sponsorship may be required.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">3. Account Responsibilities</h2>
            <p className="text-slate-300 leading-relaxed">
              You are responsible for maintaining the confidentiality of your account credentials and for
              all activities that occur under your account.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">4. Authorized Use</h2>
            <p className="text-slate-300 leading-relaxed">
              You may use PROJECT NEXUS AI only for legitimate forensic research and investigation purposes.
              You must have proper authorization for all evidence you upload and analyze.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">5. Prohibited Activities</h2>
            <p className="text-slate-300 leading-relaxed">
              You may not use the application to: upload evidence without authorization, attempt to
              circumvent security measures, use AI-generated findings as sole evidence in legal proceedings
              without independent verification, or use the application for unlawful purposes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">6. Evidence Upload Responsibilities</h2>
            <p className="text-slate-300 leading-relaxed">
              You are solely responsible for ensuring that all evidence you upload was obtained legally
              and with proper authorization. Chain of custody records are maintained but do not establish
              legal admissibility.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">7. Intellectual Property</h2>
            <p className="text-slate-300 leading-relaxed">
              You retain all rights to evidence and content you upload. PROJECT NEXUS AI does not claim
              ownership of your forensic data.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">8. AI-Generated Output Limitations</h2>
            <p className="text-slate-300 leading-relaxed">
              All AI-generated output is provided &ldquo;as is&rdquo; without warranties of accuracy,
              completeness, or admissibility. AI findings are investigative aids only.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">9. Third-Party Service Limitations</h2>
            <p className="text-slate-300 leading-relaxed">
              We may use third-party services (e.g., Gemini API for AI processing). These services have
              their own terms and privacy policies. We are not responsible for their practices.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">10. Account Suspension and Termination</h2>
            <p className="text-slate-300 leading-relaxed">
              We may suspend or terminate accounts that violate these Terms or engage in prohibited activities.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">11. Limitation of Liability</h2>
            <p className="text-slate-300 leading-relaxed">
              PROJECT NEXUS AI is provided on an &ldquo;as is&rdquo; basis. To the maximum extent
              permitted by law, we are not liable for any damages arising from use of the application
              or reliance on AI-generated findings.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">12. Changes to Terms</h2>
            <p className="text-slate-300 leading-relaxed">
              We may update these terms. Continued use constitutes acceptance of the revised terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">13. Governing Law</h2>
            <p className="text-slate-300 leading-relaxed">
              These terms are governed by the laws of the applicable jurisdiction where the academic
              project is based.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">14. Contact Information</h2>
            <p className="text-slate-300 leading-relaxed">
              support@example.com
            </p>
          </section>

          <footer className="mt-8 pt-6 border-t border-slate-700 text-xs text-slate-500">
            <p>PROJECT NEXUS AI - Academic Project. These terms use placeholder information and require legal review before public deployment.</p>
          </footer>
        </article>
      </div>
    </div>
  )
}
