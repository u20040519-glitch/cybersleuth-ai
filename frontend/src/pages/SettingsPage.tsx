// =============================================================================
// CYBERSLEUTH AI - Settings Page
// =============================================================================

import { useState } from 'react'
import { Card, CardHeader } from '@/ui/Card'

import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'
import { Users, Shield, Bell, RotateCcw } from 'lucide-react'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const [saving, setSaving] = useState(false)

  const tabs = [
    { id: 'profile', label: 'Profile', icon: Users },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ]

  const handleSave = async () => {
    setSaving(true)
    setTimeout(() => setSaving(false), 1000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">Settings</h2>
        <p className="text-text-secondary">
          Manage your account, security preferences, and notification settings.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-3">
          <div className="flex flex-col h-full">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cnTab(
                    activeTab === tab.id
                      ? 'bg-primary-blue/10 text-primary-blue border border-primary-blue/20'
                      : 'text-text-secondary hover:text-text-main hover:bg-secondary',
                  )}
                >
                  <tab.icon size={16} className="mr-2" />
                  {tab.label}
                </button>
              ))}
            </nav>
            <div className="mt-auto p-4 rounded-lg bg-secondary/50 border border-border/50">
              <p className="text-xs text-text-secondary/60">Role: Investigator</p>
              <p className="text-xs text-text-secondary">Platform: CyberSleuth AI v1.0.0</p>
            </div>
          </div>
        </div>

        <div className="lg:col-span-9">
          <Card>
            <CardHeader title={activeTab === 'profile' ? 'Profile' : activeTab === 'security' ? 'Security' : 'Notifications'} />
            <form onSubmit={(e) => { e.preventDefault(); handleSave() }} className="space-y-5">
              {activeTab === 'profile' && (
                <>
                  <div className="space-y-2">
                    <label className="label">Full Name</label>
                    <Input label="" placeholder="Jane Investigator" defaultValue="Lead Investigator" />
                  </div>
                  <div className="space-y-2">
                    <label className="label">Email Address</label>
                    <Input label="" type="email" placeholder="investigator@cybersleuth.ai" defaultValue="investigator@cybersleuth.ai" />
                  </div>
                  <div className="space-y-2">
                    <label className="label">Role</label>
                    <select className="input">
                      <option>Investigator</option>
                      <option>Supervisor</option>
                    </select>
                  </div>
                </>
              )}
              {activeTab === 'security' && (
                <>
                  <div className="space-y-2">
                    <label className="label">Current Password</label>
                    <Input label="" type="password" placeholder="••••••••" />
                  </div>
                  <div className="space-y-2">
                    <label className="label">New Password</label>
                    <Input label="" type="password" placeholder="••••••••" />
                  </div>
                  <div className="space-y-2">
                    <label className="label">Confirm New Password</label>
                    <Input label="" type="password" placeholder="••••••••" />
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      id="mfa"
                      type="checkbox"
                      className="checkbox"
                      defaultChecked
                    />
                    <label htmlFor="mfa" className="text-sm text-text-main">
                      Enable two-factor authentication
                    </label>
                  </div>
                </>
              )}
              {activeTab === 'notifications' && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-main">Email notifications</span>
                    <input type="checkbox" className="checkbox" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-main">Analysis completion alerts</span>
                    <input type="checkbox" className="checkbox" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-main">Security alerts</span>
                    <input type="checkbox" className="checkbox" defaultChecked />
                  </div>
                </>
              )}
              <Button variant="primary" type="submit" disabled={saving} className="w-auto">
                {saving ? (
                  <span className="flex items-center gap-2">
                    <RotateCcw size={16} className="animate-spin" />
                    Saving...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Shield size={16} /> Save Changes
                  </span>
                )}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  )
}

function cnTab(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}
