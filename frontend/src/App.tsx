// =============================================================================
// CYBERSLEUTH AI - App Router
// =============================================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute, GuestRoute } from '@/components/RouteGuard'

// Auth pages (guest)
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'

// Protected pages (layout)
import { DashboardPage } from '@/pages/DashboardPage'
import { InvestigationsPage } from '@/pages/InvestigationsPage'
import { CreateInvestigationPage } from '@/pages/CreateInvestigationPage'
import { InvestigationDetailPage } from '@/pages/InvestigationDetailPage'
import { EvidenceVaultPage } from '@/pages/EvidenceVaultPage'
import { UploadEvidencePage } from '@/pages/UploadEvidencePage'
import { DeepTracePage } from '@/pages/DeepTracePage'
import { SpyTracePage } from '@/pages/SpyTracePage'
import { VoiceProofPage } from '@/pages/VoiceProofPage'
import { CyberSleuthPage } from '@/pages/CyberSleuthPage'
import { CorrelationEnginePage } from '@/pages/CorrelationEnginePage'
import { ReportsPage } from '@/pages/ReportsPage'
import { AuditLogsPage } from '@/pages/AuditLogsPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  // The basename follows the public base path of the build (the root on
  // Netlify, /<repo>/ on GitHub Pages), so the client-side routes keep
  // working on every host.
  const basename = import.meta.env.BASE_URL.replace(/\/+$/, '') || '/'

  return (
    <AuthProvider>
      <BrowserRouter basename={basename}>
        <Routes>
          {/* Guest routes */}
          <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
          <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />

          {/* Protected routes (with layout) */}
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="investigations" element={<InvestigationsPage />} />
            <Route path="investigations/create" element={<CreateInvestigationPage />} />
            <Route path="investigations/:id" element={<InvestigationDetailPage />} />
            <Route path="evidence" element={<EvidenceVaultPage />} />
            <Route path="evidence/upload" element={<UploadEvidencePage />} />
            <Route path="deeptrace" element={<DeepTracePage />} />
            <Route path="spytrace" element={<SpyTracePage />} />
            <Route path="voiceproof" element={<VoiceProofPage />} />
            <Route path="cybersleuth" element={<CyberSleuthPage />} />
            <Route path="correlation" element={<CorrelationEnginePage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="audit-logs" element={<AuditLogsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
