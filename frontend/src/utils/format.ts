// =============================================================================
// CYBERSLEUTH AI - Formatting Utilities
// =============================================================================

export function formatBytes(bytes: number | undefined | null): string {
  if (!bytes || bytes < 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(i === 0 ? 0 : 2)} ${units[i]}`
}

export function formatDate(iso: string | undefined | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  })
}

export function formatDateTime(iso: string | undefined | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function truncateHash(hash: string | undefined | null, length = 16): string {
  if (!hash) return '—'
  return hash.length > length ? `${hash.slice(0, length)}…` : hash
}

export function getFileExtension(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx === -1 ? '' : filename.slice(idx + 1).toLowerCase()
}

export function getFileCategory(filename: string): string {
  const ext = getFileExtension(filename)
  if (['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tif', 'tiff'].includes(ext)) return 'image'
  if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv'].includes(ext)) return 'video'
  if (['wav', 'mp3', 'flac', 'm4a', 'aac', 'ogg', 'wma'].includes(ext)) return 'audio'
  if (['pdf', 'docx', 'doc', 'txt', 'rtf'].includes(ext)) return 'document'
  if (['json', 'csv', 'xml', 'eml', 'log', 'yml', 'yaml'].includes(ext)) return 'data'
  if (ext === 'apk') return 'android'
  return 'other'
}
