// =============================================================================
// CYBERSLEUTH AI - DeepTrace AI (Image Forensics)
// =============================================================================

import { Image } from 'lucide-react'
import { ModuleAnalysisPage } from '@/components/ModuleAnalysisPage'

export function DeepTracePage() {
  return (
    <ModuleAnalysisPage
      module="deeptrace"
      title="DeepTrace AI"
      tagline="Image forensics. Error Level Analysis, noise residual analysis, copy-move detection and EXIF review."
      purpose="Detect manipulation in photographs and screen captures."
      outputs="EXIF findings, ELA/noise/copy-move heuristics, geometry checks, timeline of EXIF capture times."
      misuseWarning="Unusual metadata does not mean a deepfake. Every finding states whether it is measured or heuristic; model predictions are never presented as verdicts."
      acceptedMimes={['image/']}
      acceptLabel="JPG, PNG, TIFF, WEBP, BMP"
      accentIcon={Image}
      accentColor="text-primary-blue"
      runButtonLabel="Run Forensic Analysis"
    />
  )
}
