// =============================================================================
// CYBERSLEUTH AI - TypeScript Type Definitions
// =============================================================================

export type UserRole = 'investigator' | 'supervisor'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  avatar_url?: string
  created_at: string
  updated_at: string
}

export interface Investigation {
  id: string
  case_id: string
  title: string
  description?: string
  category: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'draft' | 'active' | 'review' | 'closed' | 'archived'
  owner_id: string
  assigned_users?: string[]
  notes?: string
  created_at: string
  updated_at: string
  evidence_count?: number
  analysis_count?: number
}

export interface EvidenceFile {
  id: string
  investigation_id: string
  original_filename: string
  file_size: number
  mime_type: string
  sha256_hash: string
  storage_path: string
  status: 'uploaded' | 'processing' | 'analyzed' | 'error'
  uploaded_by: string
  uploaded_at: string
  processed_at?: string
  thumbnail_url?: string
}

export interface AnalysisResult {
  id: string
  evidence_id: string
  module: 'deeptrace' | 'spytrace' | 'voiceproof' | 'cybersleuth'
  status: 'pending' | 'running' | 'completed' | 'failed'
  result_data?: any
  confidence_score?: number
  created_at: string
  completed_at?: string
}

export interface ChainOfCustodyEvent {
  id: string
  evidence_id: string
  event_type: 'upload' | 'access' | 'process' | 'export' | 'share'
  actor_id: string
  actor_name: string
  timestamp: string
  details?: string
}

export interface CorrelationResult {
  id: string
  investigation_id: string
  source_evidence_id: string
  finding_id?: string
  correlation_type: string
  description: string
  confidence?: number
  timestamp?: string
  verified: boolean
  created_at: string
}

export interface GeneratedReport {
  id: string
  investigation_id: string
  title: string
  status: 'generating' | 'ready' | 'failed'
  pdf_url?: string
  generated_by: string
  generated_at: string
}

export interface AuditLog {
  id: string
  user_id: string
  user_name: string
  action: string
  resource: string
  resource_id?: string
  ip_address?: string
  timestamp: string
}

export interface NavItem {
  name: string
  href: string
  icon: React.ElementType
  module?: string
}

export interface StatCard {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  color: string
  trend?: { value: number; label: string; positive: boolean }
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}
