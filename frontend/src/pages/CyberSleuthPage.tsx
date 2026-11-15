// =============================================================================
// CYBERSLEUTH AI - CyberSleuth AI (Artefact Extraction)
// =============================================================================

import { Code } from 'lucide-react'
import { ModuleAnalysisPage } from '@/components/ModuleAnalysisPage'

export function CyberSleuthPage() {
  return (
    <ModuleAnalysisPage
      module="cybersleuth"
      title="CyberSleuth AI"
      tagline="Digital evidence extraction. Timestamps, named entities, regex indicators and relationship candidates from text artefacts."
      purpose="Pull structured facts out of chat exports, logs and notes for correlation."
      outputs="Structured records with senders/timestamps, regex entities (emails, URLs, IPs, hashes, phones), spaCy NER counts, event timeline."
      misuseWarning="Extracted entities are observations, not identities. Person mentions are never treated as attribution of authorship or guilt."
      acceptedMimes={['application/json', 'text/', 'application/xml', 'application/csv', 'application/octet-stream']}
      acceptLabel="JSON, CSV, TXT, XML, LOG"
      accentIcon={Code}
      accentColor="text-primary-cyan"
      runButtonLabel="Run Forensic Analysis"
    />
  )
}
