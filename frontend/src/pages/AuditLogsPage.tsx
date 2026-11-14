// =============================================================================
// CYBERSLEUTH AI - Audit Logs Page
// =============================================================================

import { Activity, Search } from 'lucide-react'

const demoLogs = [
  { user: 'Lead Investigator', action: 'Evidence uploaded', resource: 'Surveillance Footage.mp4', time: '10:14:22', type: 'upload' },
  { user: 'Lead Investigator', action: 'Analysis started', resource: 'DeepTrace AI', time: '10:15:01', type: 'process' },
  { user: 'Case Supervisor', action: 'Report generated', resource: 'CASE-2026-001', time: '10:18:09', type: 'export' },
  { user: 'Lead Investigator', action: 'Evidence accessed', resource: 'Chat_Export.json', time: '10:20:15', type: 'access' },
  { user: 'Case Supervisor', action: 'Finding reviewed', resource: 'SpyTrace AI', time: '10:22:44', type: 'review' },
]

export function AuditLogsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-main">Audit Logs</h2>
        <p className="text-text-secondary">
          Immutable record of all user actions, evidence access, and system events.
        </p>
      </div>

      <div className="relative w-72">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary/50" />
        <input
          type="text"
          placeholder="Search audit logs..."
          className="input pl-9"
        />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse border-border">
          <thead>
            <tr className="border-b border-border">
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Timestamp</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">User</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Action</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Resource</th>
              <th className="pb-3 text-xs font-semibold text-text-secondary/60 uppercase">Type</th>
            </tr>
          </thead>
          <tbody>
            {demoLogs.map((log, i) => (
              <tr key={i} className="border-b border-border/50 hover:bg-secondary/30 transition-colors">
                <td className="py-4 text-xs font-mono text-text-secondary">{log.time}</td>
                <td className="py-4 text-sm text-text-main">{log.user}</td>
                <td className="py-4 text-sm text-text-main">{log.action}</td>
                <td className="py-4 text-xs text-text-secondary font-mono truncate">{log.resource}</td>
                <td className="py-4">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${
                      log.type === 'upload'
                        ? 'bg-primary-blue/10 text-primary-blue border-primary-blue/20'
                        : log.type === 'process'
                          ? 'bg-warning/10 text-warning border-warning/20'
                          : log.type === 'export'
                            ? 'bg-success/10 text-success border-success/20'
                            : 'bg-secondary text-text-secondary border-border'
                    }`}
                  >
                    {log.type}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-4 rounded-lg bg-secondary border border-border">
        <p className="text-xs text-text-secondary/60">
          <Activity size={14} className="mr-1 inline" /> Audit logs are write-once and tamper-evident. Phase 2 connects these to the backend audit_logs table with RLS.
        </p>
      </div>
    </div>
  )
}
