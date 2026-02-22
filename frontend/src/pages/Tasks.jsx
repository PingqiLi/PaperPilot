import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Loader2, CheckCircle2, XCircle, AlertCircle,
  ArrowRight, ChevronDown, ChevronUp, ListTodo, Pencil,
} from 'lucide-react'
import { getTasks } from '../api/tasks'
import { useLanguage } from '../contexts/LanguageContext'

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
    return <Pencil size={14} style={{ color: 'var(--warn)' }} />
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
  const { t } = useLanguage()
  const labels = {
    running: t('tasks.status.running'),
    awaiting_approval: t('tasks.status.awaitingApproval'),
    completed: t('tasks.status.completed'),
    failed: t('tasks.status.failed'),
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
  if (task.task_type === 'topic_init' && !task.ruleset_id) {
    return `/topics/new?taskId=${task.id}`
  }
  if (!task.ruleset_id) return null
  if (task.task_type === 'paper_analysis' && task.paper_id) {
    return `/topics/${task.ruleset_id}/papers/${task.paper_id}`
  }
  return `/topics/${task.ruleset_id}`
}

function parseUTC(dateStr) {
  if (!dateStr) return null
  return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')
}

function formatElapsed(createdAt, completedAt) {
  const start = parseUTC(createdAt).getTime()
  const end = completedAt ? parseUTC(completedAt).getTime() : Date.now()
  const diff = Math.max(0, Math.floor((end - start) / 1000))
  if (diff < 60) return `${diff}s`
  const min = Math.floor(diff / 60)
  const sec = diff % 60
  if (min < 60) return `${min}m ${sec.toString().padStart(2, '0')}s`
  const hr = Math.floor(min / 60)
  return `${hr}h ${(min % 60).toString().padStart(2, '0')}m`
}

function formatTime(dateStr) {
  const d = parseUTC(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function ElapsedTicker({ createdAt }) {
  const [, setTick] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setTick(t => t + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <span className="text-xs font-mono tabular-nums" style={{ color: 'var(--muted)' }}>
      {formatElapsed(createdAt)}
    </span>
  )
}

function ProgressStage({ stage, t }) {
  const stageLabels = {
    searching: t('tasks.stage.searching'),
    scoring: t('tasks.stage.scoring'),
    method_search: t('tasks.stage.methodSearch'),
    arxiv_search: t('tasks.stage.arxivSearch'),
    ranking: t('tasks.stage.ranking'),
    citation_discovery: t('tasks.stage.citationDiscovery'),
    citation_scoring: t('tasks.stage.citationScoring'),
    auto_analysis: t('tasks.stage.autoAnalysis'),
    done: t('tasks.stage.done'),
  }
  return <span>{stageLabels[stage] || stage}</span>
}

function TaskRow({ task }) {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const [showError, setShowError] = useState(false)
  const navTarget = getNavTarget(task)
  const tc = TYPE_COLORS[task.task_type] || TYPE_COLORS.topic_init
  const typeLabels = {
    topic_init: t('tasks.type.topicInit'),
    track: t('tasks.type.track'),
    digest: t('tasks.type.digest'),
    paper_analysis: t('tasks.type.analysis'),
  }
  const isActive = task.status === 'running' || task.status === 'awaiting_approval'
  const isAwaiting = task.status === 'awaiting_approval'
  const accentColor = isAwaiting ? 'var(--warn)' : 'var(--accent)'

  return (
    <div
      className="p-4 rounded-xl border transition-all"
      style={{
        background: 'var(--card)',
        borderColor: isActive ? accentColor : 'var(--border)',
        borderLeftWidth: isActive ? 3 : 1,
        borderLeftColor: isActive ? accentColor : undefined,
      }}
    >
      <div className="flex items-center gap-3">
        <StatusIcon status={task.status} />
        <span
          className="px-2 py-0.5 rounded-md text-[11px] font-medium"
          style={{ background: tc.bg, color: tc.color }}
        >
          {typeLabels[task.task_type] || task.task_type}
        </span>
        <span className="text-sm font-medium flex-1 min-w-0 truncate" style={{ color: 'var(--text-strong)' }}>
          {task.title}
        </span>
        <StatusLabel status={task.status} />
        {isActive ? (
          <ElapsedTicker createdAt={task.created_at} />
        ) : task.completed_at ? (
          <span className="text-xs font-mono tabular-nums" style={{ color: 'var(--muted)' }}>
            {formatElapsed(task.created_at, task.completed_at)}
          </span>
        ) : (
          <span className="text-xs font-mono tabular-nums" style={{ color: 'var(--muted)' }}>
            {formatTime(task.created_at)}
          </span>
        )}
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
            {isAwaiting ? t('tasks.continue') : t('tasks.view')} <ArrowRight size={11} />
          </button>
        )}
      </div>

      {task.progress && task.status === 'running' && (
        <div className="mt-2.5 ml-[26px]">
          <div className="flex items-center gap-2 text-xs mb-1" style={{ color: 'var(--muted)' }}>
            <ProgressStage stage={task.progress.stage} t={t} />
            {task.progress.done != null && task.progress.total != null && (
              <span className="font-mono tabular-nums">{task.progress.done}/{task.progress.total}</span>
            )}
          </div>
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-hover)' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: task.progress.total > 0
                  ? `${Math.min(Math.round((task.progress.done / task.progress.total) * 100), 100)}%`
                  : '0%',
                background: 'var(--accent)',
              }}
            />
          </div>
        </div>
      )}

      {isAwaiting && (
        <div className="mt-2 ml-[26px]">
          <span className="text-xs" style={{ color: 'var(--warn)' }}>
            {t('tasks.awaitingHint')}
          </span>
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
  const { t } = useLanguage()
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
  const activeCount = tasks.filter(t => t.status === 'running' || t.status === 'awaiting_approval').length

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" style={{ color: 'var(--text-strong)' }}>
            {t('tasks.title')}
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
            {t('tasks.subtitle')}
          </p>
        </div>
        {activeCount > 0 && (
          <span
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
            style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}
          >
            <Loader2 size={12} className="animate-spin" />
            {t('tasks.activeCount').replace('{n}', activeCount)}
          </span>
        )}
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
            {t('tasks.emptyTitle')}
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--muted)', opacity: 0.7 }}>
            {t('tasks.emptyDesc')}
          </p>
        </div>
      )}
    </div>
  )
}

export default Tasks
