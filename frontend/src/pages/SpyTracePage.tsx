// =============================================================================
// CYBERSLEUTH AI - SpyTrace AI (Android Package Forensics)
// =============================================================================

import { Smartphone } from 'lucide-react'
import { ModuleAnalysisPage } from '@/components/ModuleAnalysisPage'

export function SpyTracePage() {
  return (
    <ModuleAnalysisPage
      module="spytrace"
      title="SpyTrace AI"
      tagline="Android package forensics. Static analysis only: manifest, permissions, signing certificate and embedded network endpoints."
      purpose="Identify stalkerware-like behaviour in sideloaded Android packages."
      outputs="Package identity, signature analysis, stalkerware risk band, exported components, embedded URLs/IPs, cert timeline."
      misuseWarning="The package is never executed or installed. Risk bands are heuristics for investigator review, not a verdict of malice."
      acceptedMimes={['application/vnd.android.package-archive', 'application/zip', 'application/octet-stream']}
      acceptLabel="APK"
      accentIcon={Smartphone}
      accentColor="text-primary-cyan"
      runButtonLabel="Run Forensic Analysis"
    />
  )
}
