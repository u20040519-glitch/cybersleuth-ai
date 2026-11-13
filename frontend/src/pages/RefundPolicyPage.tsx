// =============================================================================
// PROJECT NEXUS AI - Refund Policy Page
// =============================================================================

export function RefundPolicyPage() {
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
            <h1 className="text-3xl font-bold text-white mb-2">Refund Policy</h1>
            <p className="text-slate-400">
              Effective Date: <span className="font-mono">2026-11-13</span> | Version: <span className="font-mono">1.0.0</span>
            </p>
          </header>

          <section className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-slate-200 mb-3">Current Operating Model</h2>
            <p className="text-slate-300 leading-relaxed">
              PROJECT NEXUS AI is currently offered as a <strong>free academic project</strong>.
              There are no subscription fees, purchase charges, or paid services associated with
              this application at this time.
            </p>
            <p className="text-slate-300 leading-relaxed">
              Because no payments are accepted, there are no refunds applicable to the current
              operating model.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">1. Paid Services</h2>
            <p className="text-slate-300 leading-relaxed">
              No paid services, subscriptions, or purchases are currently offered. We do not
              advertise paid services that do not exist.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">2. Future Paid Services</h2>
            <p className="text-slate-300 leading-relaxed">
              If paid subscriptions or services are introduced in the future, this policy will be
              updated <strong>before</strong> any payments are accepted. The future policy will
              specify eligible purchases, refund request procedures, refund eligibility, applicable
              time limits, processing times, and cancellation processes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">3. Refund Guarantee</h2>
            <p className="text-slate-300 leading-relaxed">
              We do not invent or offer a refund guarantee. Any future refund policy will be
              consistent with applicable consumer law and payment provider functionality.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">4. Contact Information</h2>
            <p className="text-slate-300 leading-relaxed">
              For questions about this policy, contact: support@example.com
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
