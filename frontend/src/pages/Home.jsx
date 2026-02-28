import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen, TrendingUp, Star, ChevronRight, Plus, ExternalLink, GripVertical, Settings,
} from 'lucide-react'
import { getTopicOverview, reorderTopics } from '../api/rulesets'
import { qk } from '../api/queryKeys'
import { useLanguage } from '../contexts/LanguageContext'

function formatRelativeTime(dateStr, t) {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return t('home.time.justNow')
  if (diffMins < 60) return t('home.time.minAgo').replace('{n}', diffMins)
  if (diffHours < 24) return t('home.time.hourAgo').replace('{n}', diffHours)
  if (diffDays < 30) return t('home.time.dayAgo').replace('{n}', diffDays)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function ScoreBadge({ score }) {
  if (score == null) return null
  let bg, color
  if (score >= 7) { bg = 'var(--ok-subtle)'; color = 'var(--ok)' }
  else if (score >= 4) { bg = 'var(--warn-subtle)'; color = 'var(--warn)' }
  else { bg = 'var(--danger-subtle)'; color = 'var(--danger)' }
  return (
    <span
      className="inline-flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-semibold flex-shrink-0"
      style={{ background: bg, color }}
    >
      {score}
    </span>
  )
}

function Dot() {
  return <span className="text-[10px]" style={{ color: 'var(--border-strong)' }}>·</span>
}

function TopicCard({ topic }) {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const { paper_counts: counts, top_papers: papers } = topic
  const hasTracked = topic.last_track_at != null
  const delta = topic.track_latest_count ?? 0

  return (
    <div
      className="group p-5 rounded-xl border transition-all cursor-pointer"
      style={{
        background: 'var(--card)',
        borderColor: 'var(--border)',
      }}
      onClick={() => navigate(`/topics/${topic.id}`)}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-md)'
        e.currentTarget.style.borderColor = 'var(--border-hover)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h3
            className="text-base font-semibold truncate"
            style={{ color: 'var(--text-strong)' }}
          >
            {topic.name}
          </h3>
          <p
            className="text-xs mt-0.5 line-clamp-1"
            style={{ color: 'var(--muted)' }}
          >
            {topic.topic_sentence}
          </p>
        </div>
        <button
          className="ml-2 flex-shrink-0 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
          style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
          title={t('home.settings')}
          onClick={e => { e.stopPropagation(); navigate(`/topics/${topic.id}?tab=settings`) }}
        >
          <Settings size={14} />
        </button>
        <span
          className="ml-3 flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium"
          style={{
            background: topic.is_initialized ? 'var(--ok-subtle)' : 'var(--warn-subtle)',
            color: topic.is_initialized ? 'var(--ok)' : 'var(--warn)',
          }}
        >
          {topic.is_initialized ? t('home.initialized') : t('home.pending')}
        </span>
      </div>

      <div className="flex items-center gap-2 mt-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <BookOpen size={13} style={{ color: 'var(--accent)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
            {counts.initialize}
          </span>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('home.foundational')}</span>
        </div>

        <Dot />

        <div className="flex items-center gap-1.5">
          <TrendingUp size={13} style={{ color: 'var(--ok)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
            {counts.track}
          </span>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('home.tracked')}</span>
          {hasTracked && (
            <span
              className="text-xs font-medium"
              style={{ color: delta > 0 ? 'var(--ok)' : 'var(--muted)' }}
            >
              (+{delta})
            </span>
          )}
        </div>

        <Dot />

        <div className="flex items-center gap-1.5">
          <Star size={13} style={{ color: 'var(--warn)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
            {counts.favorited}
          </span>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('home.favorites')}</span>
        </div>
      </div>

      {papers.length > 0 && (
        <>
          <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
            <div className="flex flex-col gap-2">
              {papers.slice(0, 3).map(paper => {
                const arxivUrl = paper.arxiv_id?.startsWith('s2:')
                  ? `https://www.semanticscholar.org/paper/${paper.arxiv_id.slice(3)}`
                  : `https://arxiv.org/abs/${paper.arxiv_id}`
                return (
                  <div key={paper.id} className="flex items-center gap-2 min-w-0">
                    <ScoreBadge score={paper.llm_score} />
                    <a
                      href={arxivUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs truncate flex-1 hover:underline"
                      style={{ color: 'var(--text)' }}
                      onClick={e => e.stopPropagation()}
                    >
                      {paper.title}
                    </a>
                    {paper.is_survey && (
                      <span
                        className="flex-shrink-0 px-1 py-0.5 rounded text-[10px] font-medium"
                        style={{ background: 'var(--warn-subtle)', color: 'var(--warn)' }}
                      >
                        {t('home.survey')}
                      </span>
                    )}
                    {paper.year && (
                      <span className="flex-shrink-0 text-[10px]" style={{ color: 'var(--muted)' }}>
                        {paper.year}
                      </span>
                    )}
                    <ExternalLink
                      size={10}
                      className="flex-shrink-0"
                      style={{ color: 'var(--muted)' }}
                    />
                  </div>
                )
              })}
            </div>
            {counts.total > 3 && (
              <p className="text-xs mt-2" style={{ color: 'var(--accent)' }}>
                {t('home.morePapers').replace('{n}', counts.total - 3)}
              </p>
            )}
          </div>
        </>
      )}

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-1.5">
          <GripVertical
            size={14}
            className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ color: 'var(--muted)', cursor: 'grab' }}
          />
          <span className="text-[10px]" style={{ color: 'var(--muted)' }}>
            {hasTracked
              ? t('home.updated').replace('{time}', formatRelativeTime(topic.last_track_at, t))
              : t('home.created').replace('{date}', new Date(topic.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }))
            }
          </span>
        </div>
        <ChevronRight size={14} style={{ color: 'var(--muted)' }} />
      </div>
    </div>
  )
}

function Home() {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const queryClient = useQueryClient()
  const { data: topics, isLoading } = useQuery({
    queryKey: qk.topicOverview,
    queryFn: getTopicOverview,
  })

  const [orderedTopics, setOrderedTopics] = useState(null)
  const [dragId, setDragId] = useState(null)
  const [dragOverId, setDragOverId] = useState(null)

  useEffect(() => {
    if (topics) setOrderedTopics(topics)
  }, [topics])

  const reorderMutation = useMutation({
    mutationFn: reorderTopics,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.topicOverview }),
  })

  const handleDragStart = (e, topicId) => {
    setDragId(topicId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDrop = (e, targetId) => {
    e.preventDefault()
    setDragOverId(null)
    if (dragId == null || dragId === targetId || !orderedTopics) return
    const items = [...orderedTopics]
    const fromIdx = items.findIndex(t => t.id === dragId)
    const toIdx = items.findIndex(t => t.id === targetId)
    if (fromIdx === -1 || toIdx === -1) return
    const [moved] = items.splice(fromIdx, 1)
    items.splice(toIdx, 0, moved)
    setOrderedTopics(items)
    reorderMutation.mutate({ ids: items.map(t => t.id) })
    setDragId(null)
  }

  const displayTopics = orderedTopics || topics

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight mb-1"
          style={{ color: 'var(--text-strong)' }}
        >
            PaperPilot
        </h1>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          {t('home.subtitle')}
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[1, 2, 3, 4].map(i => (
            <div
              key={i}
              className="h-52 rounded-xl animate-pulse"
              style={{ background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      ) : displayTopics?.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {displayTopics.map(topic => (
            <div
              key={topic.id}
              draggable
              onDragStart={e => handleDragStart(e, topic.id)}
              onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOverId(topic.id) }}
              onDragLeave={() => setDragOverId(null)}
              onDrop={e => handleDrop(e, topic.id)}
              onDragEnd={() => { setDragId(null); setDragOverId(null) }}
              style={{
                opacity: dragId === topic.id ? 0.5 : 1,
                outline: dragOverId === topic.id && dragId !== topic.id ? '2px solid var(--accent)' : 'none',
                outlineOffset: 2,
                borderRadius: 12,
              }}
            >
              <TopicCard topic={topic} />
            </div>
          ))}
        </div>
      ) : (
        <div
          className="text-center py-20 rounded-xl border"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <div
            className="mx-auto w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
            style={{ background: 'var(--accent-subtle)' }}
          >
            <Plus size={28} style={{ color: 'var(--accent)' }} />
          </div>
          <p className="text-lg font-medium mb-2" style={{ color: 'var(--text-strong)' }}>
            {t('home.noTopics')}
          </p>
          <p className="text-sm mb-5" style={{ color: 'var(--muted)' }}>
            {t('home.createFirstTopic')}
          </p>
          <button
            onClick={() => navigate('/topics/new')}
            className="px-5 py-2 rounded-lg text-sm font-medium cursor-pointer"
            style={{
              background: 'var(--accent)',
              color: 'var(--accent-foreground)',
              border: 'none',
            }}
          >
            {t('home.newTopic')}
          </button>
        </div>
      )}
    </div>
  )
}

export default Home
