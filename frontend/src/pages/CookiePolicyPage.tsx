// =============================================================================
// PROJECT NEXUS AI - Cookie Policy Page
// =============================================================================

export function CookiePolicyPage() {
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
            <h1 className="text-3xl font-bold text-white mb-2">Cookie Policy</h1>
            <p className="text-slate-400">
              Effective Date: <span className="font-mono">2026-11-13</span> | Version: <span className="font-mono">1.0.0</span>
            </p>
          </header>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">1. What Are Cookies</h2>
            <p className="text-slate-300 leading-relaxed">
              Cookies are small text files stored on your device when you visit our website. They help
              us provide functionality, remember preferences, and analyze usage.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">2. Cookie Categories</h2>
            <h3 className="text-md font-semibold text-slate-200 mb-2">Essential Cookies</h3>
            <p className="text-slate-300 leading-relaxed">
              These cookies are necessary for the application to function, including authentication
              session management and security. They do not require consent and cannot be disabled.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Analytics Cookies</h3>
            <p className="text-slate-300 leading-relaxed">
              Optional cookies that help us understand how the application is used. These are only
              activated with your explicit consent.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Functional Cookies</h3>
            <p className="text-slate-300 leading-relaxed">
              Optional cookies that remember your preferences and settings.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Marketing Cookies</h3>
            <p className="text-slate-300 leading-relaxed">
              PROJECT NEXUS AI does not currently use marketing cookies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">3. Consent</h2>
            <p className="text-slate-300 leading-relaxed">
              You may accept or reject non-essential cookies via our cookie consent banner. Your
              preferences are stored and can be changed at any time through
              Settings → Privacy → Cookie Preferences.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">4. Your Rights</h2>
            <p className="text-slate-300 leading-relaxed">
              You can withdraw consent for non-essential cookies at any time. Disabling cookies
              may affect some application functionality.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">5. Contact</h2>
            <p className="text-slate-300 leading-relaxed">
              privacy@example.com
            </p>
          </section>

          <footer className="mt-8 pt-6 border-t border-slate-700 text-xs text-slate-500">
            <p>PROJECT NEXUS AI - Academic Project. This policy uses placeholder information and requires legal review before public deployment.</p>
          </footer>
        </article>
      </div>
    </div>
  )
}
