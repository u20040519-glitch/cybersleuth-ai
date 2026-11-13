// =============================================================================
// PROJECT NEXUS AI - Settings Pages
// =============================================================================

import { Link } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { ShieldCheck, Mail, Bell, User as UserIcon } from 'lucide-react'

export function SettingsPage() {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Settings</h2>
          <p className="text-slate-400">Manage your account, security, and privacy preferences.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[{
            title: 'Account',
            desc: 'Profile, email, and personal information',
            icon: UserIcon,
            href: '/settings/account',
          }, {
            title: 'Security',
            desc: 'Password, MFA, and session management',
            icon: ShieldCheck,
            href: '/settings/security',
          }, {
            title: 'Privacy',
            desc: 'Consent, data deletion, cookie preferences',
            icon: Mail,
            href: '/settings/privacy',
          }, {
            title: 'Notifications',
            desc: 'Email and system notification settings',
            icon: Bell,
            href: '/settings/notifications',
          }].map((item) => (
            <div key={item.title} className="card hover:bg-slate-800/70 transition-colors cursor-pointer group">
              <div className="p-3 bg-slate-900/50 rounded-lg mb-3 group-hover:bg-nexus-accent/10 transition-colors">
                <item.icon size={20} className="text-slate-400 group-hover:text-nexus-accent" />
              </div>
              <h3 className="font-semibold text-slate-200 mb-1">{item.title}</h3>
              <p className="text-xs text-slate-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  )
}

export function SettingsAccountPage() {
  return (
    <Layout>
      <div className="max-w-xl">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white">Account Settings</h2>
            <Link to="/settings" className="text-sm text-nexus-accent hover:underline">← Back</Link>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Profile Information</h3>
            <div className="space-y-4">
              <div>
                <label className="label">Full Name</label>
                <input type="text" placeholder="Jane Investigator" className="input" defaultValue="Jane Investigator" />
              </div>
              <div>
                <label className="label">Email Address</label>
                <input type="email" placeholder="jane@example.com" className="input" defaultValue="jane@example.com" readOnly />
              </div>
              <div>
                <label className="label">Institution (optional)</label>
                <input type="text" placeholder="University or Lab" className="input" />
              </div>
              <div>
                <label className="label">Role</label>
                <input type="text" placeholder="Forensic Analyst" className="input" />
              </div>
              <div>
                <label className="label">Area of Forensic Interest (optional)</label>
                <input type="text" placeholder="e.g., Network Forensics" className="input" />
              </div>
            </div>
            <button className="btn-primary">Save Changes</button>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export function SettingsSecurityPage() {
  return (
    <Layout>
      <div className="max-w-xl">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white">Security Settings</h2>
            <Link to="/settings" className="text-sm text-nexus-accent hover:underline">← Back</Link>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Password</h3>
            <p className="text-sm text-slate-400 mb-4">Passwords are hashed with Argon2id and never stored in plain text.</p>
            <div className="space-y-3">
              <input type="password" placeholder="Current Password" className="input" />
              <input type="password" placeholder="New Password" className="input" />
              <input type="password" placeholder="Confirm New Password" className="input" />
              <button className="btn-primary w-auto">Change Password</button>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Multi-Factor Authentication</h3>
            <p className="text-sm text-slate-400 mb-4">Add an additional layer of security to your account.</p>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">MFA Enabled</span>
              <input type="checkbox" className="checkbox" />
            </div>
          </div>

          <div className="card border-red-500/20 bg-red-500/5">
            <h3 className="font-semibold text-red-400 mb-4">Delete Account</h3>
            <p className="text-sm text-slate-400 mb-4">
              Permanently delete your account and associated personal data. This action cannot be undone.
            </p>
            <button className="btn-danger w-auto">
              Request Account Deletion
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export function SettingsPrivacyPage() {
  return (
    <Layout>
      <div className="max-w-xl">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white">Privacy Settings</h2>
            <Link to="/settings" className="text-sm text-nexus-accent hover:underline">← Back</Link>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">External AI Processing</h3>
            <p className="text-sm text-slate-400 mb-4">
              Allow optional external AI processing (Gemini API) for forensic analysis. This is optional
              and not required for core application functionality.
            </p>
            <div className="flex items-start gap-3">
              <input id="ai-processing" type="checkbox" className="checkbox mt-0.5" />
              <label className="text-sm text-slate-300">Enable external AI processing</label>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Data Deletion</h3>
            <p className="text-sm text-slate-400 mb-4">
              Request deletion of your account and personal data. Evidence records may be retained
              under documented legal or institutional retention policies.
            </p>
            <button className="btn-secondary w-auto">
              Request My Data Deletion
            </button>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Cookie Preferences</h3>
            <p className="text-sm text-slate-400 mb-4">
              Manage your cookie consent preferences for analytics, functional, and marketing cookies.
            </p>
            <button className="btn-secondary w-auto">
              Manage Cookie Preferences
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export function SettingsNotificationsPage() {
  return (
    <Layout>
      <div className="max-w-xl">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white">Notification Settings</h2>
            <Link to="/settings" className="text-sm text-nexus-accent hover:underline">← Back</Link>
          </div>

          <div className="card">
            <h3 className="font-semibold text-slate-200 mb-4">Email Notifications</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Security Alerts</span>
                <input type="checkbox" className="checkbox" defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Case Updates</span>
                <input type="checkbox" className="checkbox" defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Marketing Communications</span>
                <input type="checkbox" className="checkbox mt-0.5" />
                <span className="text-xs text-slate-500 ml-2">Optional - requires consent</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
