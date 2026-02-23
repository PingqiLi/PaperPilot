import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'

function LlmLoadingBanner({ message, detail, startedAt }) {
  const parseUtc = (s) => {
    if (!s) return null
    return new Date(s.endsWith('Z') || s.includes('+') ? s : s + 'Z')
  }
  const [elapsed, setElapsed] = useState(() => {
    const start = parseUtc(startedAt)
    if (start) {
      return Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000))
    }
    return 0
  })
  useEffect(() => {
    const start = parseUtc(startedAt)
    const getElapsed = () => {
      if (start) {
        return Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000))
      }
      return 0
    }
    setElapsed(getElapsed())
    const timer = setInterval(() => setElapsed(getElapsed()), 1000)
    return () => clearInterval(timer)
  }, [startedAt])

  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  const timeStr = minutes > 0
    ? `${minutes}m ${seconds.toString().padStart(2, '0')}s`
    : `${seconds}s`

  return (
    <div
      className="flex items-center gap-3 p-4 rounded-xl border"
      style={{ background: 'var(--card)', borderColor: 'var(--accent)' }}
    >
      <Loader2 size={18} className="animate-spin flex-shrink-0" style={{ color: 'var(--accent)' }} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
          {message}
        </p>
        {detail && (
          <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>{detail}</p>
        )}
      </div>
      <span
        className="text-xs font-mono tabular-nums flex-shrink-0"
        style={{ color: 'var(--muted)' }}
      >
        {timeStr}
      </span>
    </div>
  )
}

export default LlmLoadingBanner
