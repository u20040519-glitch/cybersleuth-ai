// =============================================================================
// PROJECT NEXUS AI - App Router
// =============================================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { CasesPage } from '@/pages/CasesPage'
import { EvidencePage } from '@/pages/EvidencePage'
import { EchoPage } from '@/pages/EchoPage'
import { MosaicPage } from '@/pages/MosaicPage'
import { TimeglassPage } from '@/pages/TimeglassPage'
import { ChatbotPage } from '@/pages/ChatbotPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { PrivacyPolicyPage } from '@/pages/PrivacyPolicyPage'
import { TermsOfServicePage } from '@/pages/TermsOfServicePage'
import { RefundPolicyPage } from '@/pages/RefundPolicyPage'
import { CookiePolicyPage } from '@/pages/CookiePolicyPage'
import { DataDeletionPage } from '@/pages/DataDeletionPage'
import { SettingsPage, SettingsAccountPage, SettingsSecurityPage, SettingsPrivacyPage, SettingsNotificationsPage } from '@/pages/SettingsPages'
import { CookieConsentBanner } from '@/components/CookieConsentBanner'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-nexus-accent" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-nexus-accent" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <CookieConsentBanner />
        <Routes>
          {/* Guest routes */}
          <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
          <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />

          {/* Public legal pages */}
          <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
          <Route path="/terms-of-service" element={<TermsOfServicePage />} />
          <Route path="/refund-policy" element={<RefundPolicyPage />} />
          <Route path="/cookie-policy" element={<CookiePolicyPage />} />

          {/* Protected routes */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/cases" element={<ProtectedRoute><CasesPage /></ProtectedRoute>} />
          <Route path="/evidence" element={<ProtectedRoute><EvidencePage /></ProtectedRoute>} />
          <Route path="/echo" element={<ProtectedRoute><EchoPage /></ProtectedRoute>} />
          <Route path="/mosaic" element={<ProtectedRoute><MosaicPage /></ProtectedRoute>} />
          <Route path="/timeglass" element={<ProtectedRoute><TimeglassPage /></ProtectedRoute>} />
          <Route path="/chatbot" element={<ProtectedRoute><ChatbotPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
          <Route path="/data-deletion" element={<ProtectedRoute><DataDeletionPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/settings/account" element={<ProtectedRoute><SettingsAccountPage /></ProtectedRoute>} />
          <Route path="/settings/security" element={<ProtectedRoute><SettingsSecurityPage /></ProtectedRoute>} />
          <Route path="/settings/privacy" element={<ProtectedRoute><SettingsPrivacyPage /></ProtectedRoute>} />
          <Route path="/settings/notifications" element={<ProtectedRoute><SettingsNotificationsPage /></ProtectedRoute>} />

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
