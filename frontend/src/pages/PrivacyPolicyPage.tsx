// =============================================================================
// PROJECT NEXUS AI - Privacy Policy Page
// =============================================================================

import { Link } from 'react-router-dom'

export function PrivacyPolicyPage() {
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
            <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
            <p className="text-slate-400">
              Effective Date: <span className="font-mono">2026-11-13</span> | Version: <span className="font-mono">1.0.0</span>
            </p>
          </header>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">1. Introduction</h2>
            <p className="text-slate-300 leading-relaxed">
              PROJECT NEXUS AI (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;) is committed to protecting your privacy.
              This Privacy Policy explains how we collect, use, store, and protect your information
              when you use our AI-assisted digital forensic investigation platform.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">2. Organization and Contact</h2>
            <p className="text-slate-300 leading-relaxed">
              Organization: PROJECT NEXUS AI (Academic Project)<br />
              Support Email: support@example.com<br />
              Privacy Contact: privacy@example.com<br />
              Website: https://example.com
            </p>
            <p className="text-sm text-slate-500 mt-2">
              <em>These are placeholder details. Replace with actual organization information before production deployment.</em>
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">3. Information We Collect</h2>
            <h3 className="text-md font-semibold text-slate-200 mb-2">Account Information</h3>
            <p className="text-slate-300 leading-relaxed">
              We collect your full name, email address, and password hash when you register.
              Passwords are hashed using Argon2id and are never stored in plain text.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Uploaded Evidence Information</h3>
            <p className="text-slate-300 leading-relaxed">
              When you upload evidence files, we store the filename, file size, MIME type,
              SHA-256 hash, and a reference to the stored file. Evidence contents are processed
              for forensic analysis but are not shared without your authorization.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Chatbot and AI Processing</h3>
            <p className="text-slate-300 leading-relaxed">
              Conversations with the NEXUS AI Forensic Chatbot are stored to provide continuity.
              If you enable external AI processing, selected information may be transmitted to
              Google's Gemini API for analysis. You control this consent and can disable it at
              any time.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Gemini API Integration</h3>
            <p className="text-slate-300 leading-relaxed">
              When external AI processing is enabled, your queries and associated case context
              may be sent to Google's Gemini API. This data is processed by Google according to
              their own privacy terms. We do not control Google's data handling practices.
            </p>

            <h3 className="text-md font-semibold text-slate-200 mb-2">Analytics</h3>
            <p className="text-slate-300 leading-relaxed">
              We use privacy-conscious analytics that do not collect raw evidence, conversation
              content, passwords, or sensitive personal information. Analytics respect your
              cookie consent preferences.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">4. Data Storage and Security</h2>
            <p className="text-slate-300 leading-relaxed">
              All data is stored on our application infrastructure using industry-standard
              encryption. Evidence files are stored with SHA-256 integrity hashing. Access is
              restricted by case-level authorization and database Row Level Security.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">5. Data Retention</h2>
            <p className="text-slate-300 leading-relaxed">
              Account data is retained until you request deletion. Evidence records may be
              retained longer under documented legal or institutional retention policies.
              Chain-of-custody records are never automatically destroyed.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">6. Data Deletion Requests</h2>
            <p className="text-slate-300 leading-relaxed">
              You may request deletion of your account and personal data at any time via
              Settings → Account → Delete Account, or our dedicated
              <Link to="/data-deletion">Request My Data Deletion</Link> page.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">7. Children's Privacy</h2>
            <p className="text-slate-300 leading-relaxed">
              PROJECT NEXUS AI is an academic project and does not intentionally collect
              personal information from children under the age of 13.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">8. Policy Updates</h2>
            <p className="text-slate-300 leading-relaxed">
              We may update this policy from time to time. Changes will be posted with an
              updated effective date. Continued use constitutes acceptance of the revised policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-3">9. Contact Information</h2>
            <p className="text-slate-300 leading-relaxed">
              For privacy questions or requests, contact: privacy@example.com
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
