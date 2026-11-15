// =============================================================================
// CYBERSLEUTH AI - VoiceProof AI (Audio Forensics)
// =============================================================================

import { Mic } from 'lucide-react'
import { ModuleAnalysisPage } from '@/components/ModuleAnalysisPage'

export function VoiceProofPage() {
  return (
    <ModuleAnalysisPage
      module="voiceproof"
      title="VoiceProof AI"
      tagline="Audio forensics. Segment/silence structure, splice seams, spectral anomaly indicators and level statistics."
      purpose="Detect splicing, editing or synthetic-voice indicators in recordings."
      outputs="Non-silent segments, silence map, splice-seam heuristics, waveform metrics, timeline of audio segments."
      misuseWarning="No calibrated synthetic-voice model is bundled; findings are heuristic measurements for investigator review, never a speaker identity claim."
      acceptedMimes={['audio/', 'video/']}
      acceptLabel="WAV, MP3, FLAC, M4A"
      accentIcon={Mic}
      accentColor="text-primary-blue"
      runButtonLabel="Run Forensic Analysis"
    />
  )
}
