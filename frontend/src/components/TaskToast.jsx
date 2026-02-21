import { useNavigate } from 'react-router-dom'
import { Loader2, X, ArrowRight } from 'lucide-react'
import { useTasks } from '../contexts/TaskContext'

function TaskToast() {
  const { toasts, removeToast } = useTasks()
  const navigate = useNavigate()

  if (toasts.length === 0) return null

  return (
    <div
      className="fixed top-4 right-4 z-50 flex flex-col gap-2"
      style={{ maxWidth: 320 }}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg border shadow-lg"
          style={{
            background: 'var(--card)',
            borderColor: 'var(--border)',
            boxShadow: 'var(--shadow-lg)',
            animation: 'slide-in-right 0.25s var(--ease-out)',
          }}
        >
          <Loader2 size={14} className="animate-spin flex-shrink-0" style={{ color: 'var(--accent)' }} />
          <span className="text-xs font-medium flex-1 min-w-0 truncate" style={{ color: 'var(--text-strong)' }}>
            {toast.title}
          </span>
          <button
            onClick={() => { removeToast(toast.id); navigate('/tasks') }}
            className="flex items-center gap-0.5 text-[11px] font-medium flex-shrink-0 cursor-pointer"
            style={{ background: 'none', border: 'none', color: 'var(--accent)', whiteSpace: 'nowrap' }}
          >
            View <ArrowRight size={10} />
          </button>
          <button
            onClick={() => removeToast(toast.id)}
            className="p-0.5 flex-shrink-0 cursor-pointer"
            style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
          >
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default TaskToast
