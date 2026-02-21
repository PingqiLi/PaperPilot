import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Loader2, CheckCircle2, XCircle, Clock, AlertCircle,
  ArrowRight, ChevronDown, ChevronUp, ListTodo,
} from 'lucide-react'
import { getTasks } from '../api/tasks'

const TYPE_LABELS = {
  topic_init: 'Topic Init',
  track: 'Track',
  digest: 'Digest',
  paper_analysis: 'Analysis',
}

const TYPE_COLORS = {
  topic_init: { bg: 'var(--accent-subtle)', color: 'var(--accent)' },
  track: { bg: 'var(--ok-subtle)', color: 'var(--ok)' },
  digest: { bg: 'var(--warn-subtle)', color: 'var(--warn)' },
  paper_analysis: { bg: 'var(--accent-subtle)', color: 'var(--accent)' },
}

function StatusIcon({ status }) {
  if (status === 'running') {
    return <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent)' }} />
  }
  if (status === 'awaiting_approval') {
    return <Clock size={14} style={{ color: 'var(--warn)' }} />
  }
  if (status === 'completed') {
    return <CheckCircle2 size={14} style={{ color: 'var(--ok)' }} />
  }
  if (status === 'failed') {
    return <XCircle size={14} style={{ color: 'var(--danger)' }} />
  }
  return <AlertCircle size={14} style={{ color: 'var(--muted)' }} />
}

function StatusLabel({ status }) {
  const labels = {
    running: 'Running',
    awaiting_approval: 'Awaiting Approval',
    completed: 'Completed',
    failed: 'Failed',
  }
  const colors = {
    running: 'var(--accent)',
    awaiting_approval: 'var(--warn)',
    completed: 'var(--ok)',
    failed: 'var(--danger)',
  }
  return (
    <span className="text-xs font-medium" style={{ color: colors[status] || 'var(--muted)' }}>
      {labels[status] || status}
    </span>
  )
}

function getNavTarget(task) {
  if (!task.ruleset_id) return null
  if (task.task_type === 'paper_analysis' && task.paper_id) {
    return `/topics/${task.ruleset_id}/papers/${task.paper_id}`
  }
  return `/topics/${task.ruleset_id}`
}

function formatElapsed(createdAt, completedAt) {
  const start = new Date(createdAt).getTime()
  const end = completedAt ? new Date(completedAt).getTime() : Date.now()
  const diff = Math.max(0, Math.floor((end - start) / 1000))
  if (diff < 60) return `${diff}s`
  const min = Math.floor(diff / 60)
  const sec = diff % 60
  if (min < 60) return `${min}m ${sec.toString().padStart(2, '0')}s`
  const hr = Math.floor(min / 60)
  return `${hr}h ${(min % 60).toString().padStart(2, '0')}m`
}

function formatTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function TaskRow({ task }) {
  const navigate = useNavigate()
  const [showError, setShowError] = useState(false)
  const navTarget = getNavTarget(task)
  const tc = TYPE_COLORS[task.task_type] || TYPE_COLORS.topic_init
  const isActive = task.status === 'running' || task.status === 'awaiting_approval'

  return (
    <div
      className="p-4 rounded-xl border transition-all"
      style={{
        background: 'var(--card)',
        borderColor: isActive ? 'var(--accent)' : 'var(--border)',
        borderLeftWidth: isActive ? 3 : 1,
        borderLeftColor: isActive ? 'var(--accent)' : undefined,
      }}
    >
      <div className="flex items-center gap-3">
        <StatusIcon status={task.status} />
        <span
          className="px-2 py-0.5 rounded-md text-[11px] font-medium"
          style={{ background: tc.bg, color: tc.color }}
        >
          {TYPE_LABELS[task.task_type] || task.task_type}
        </span>
        <span className="text-sm font-medium flex-1 min-w-0 truncate" style={{ color: 'var(--text-strong)' }}>
          {task.title}
        </span>
        <StatusLabel status={task.status} />
        <span className="text-xs font-mono tabular-nums" style={{ color: 'var(--muted)' }}>
          {isActive ? formatElapsed(task.created_at) : formatTime(task.created_at)}
        </span>
        {task.status === 'failed' && task.error && (
          <button
            onClick={() => setShowError(v => !v)}
            className="p-1 rounded cursor-pointer"
            style={{ background: 'none', border: 'none', color: 'var(--danger)' }}
          >
            {showError ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
        {navTarget && (
          <button
            onClick={() => navigate(navTarget)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs cursor-pointer"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            View <ArrowRight size={11} />
          </button>
        )}
      </div>
      {task.progress && task.status === 'running' && (
        <div className="mt-2.5 ml-[26px]">
          <div className="flex items-center gap-2 text-xs mb-1" style={{ color: 'var(--muted)' }}>
            <span>{task.progress.stage}</span>
            {task.progress.done != null && task.progress.total != null && (
              <span>{task.progress.done}/{task.progress.total}</span>
            )}
          </div>
          <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-hover)' }}>
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: task.progress.total > 0
                  ? `${Math.round((task.progress.done / task.progress.total) * 100)}%`
                  : '0%',
                background: 'var(--accent)',
              }}
            />
          </div>
        </div>
      )}
      {showError && task.error && (
        <div
          className="mt-2.5 ml-[26px] p-2.5 rounded-lg text-xs"
          style={{ background: 'var(--danger-subtle)', color: 'var(--danger)' }}
        >
          {task.error}
        </div>
      )}
    </div>
  )
}

function Tasks() {
  const { data, isLoading } = useQuery({
    queryKey: ['allTasks'],
    queryFn: () => getTasks({ limit: 100 }),
    refetchInterval: (query) => {
      const items = query.state.data?.items
      const hasActive = items?.some(t => t.status === 'running' || t.status === 'awaiting_approval')
      return hasActive ? 3000 : false
    },
  })

  const tasks = data?.items || []

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight" style={{ color: 'var(--text-strong)' }}>
          Tasks
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
          Track background operations
        </p>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map(i => (
            <div
              key={i}
              className="h-16 rounded-xl animate-pulse"
              style={{ background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      ) : tasks.length > 0 ? (
        <div className="flex flex-col gap-2.5">
          {tasks.map(task => (
            <TaskRow key={task.id} task={task} />
          ))}
        </div>
      ) : (
        <div
          className="text-center py-16 rounded-xl border"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <ListTodo size={40} className="mx-auto mb-3" style={{ color: 'var(--muted)', opacity: 0.5 }} />
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            No tasks yet
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--muted)', opacity: 0.7 }}>
            Background tasks will appear here when you initialize topics, track papers, or generate digests
          </p>
        </div>
      )}
    </div>
  )
}

export default Tasks
