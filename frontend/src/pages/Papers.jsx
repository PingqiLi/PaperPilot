import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ExternalLink, Star, Archive, Inbox, BookOpen, Sparkles,
} from 'lucide-react'
import { getGlobalPapers, getRulesets, updatePaperStatus } from '../api/rulesets'
import { useLanguage } from '../contexts/LanguageContext'

const STATUS_FILTERS = [
  { key: 'highlighted', labelKey: 'papers.filter.highlights' },
  { key: null, labelKey: 'papers.filter.all' },
  { key: 'favorited', labelKey: 'papers.filter.favorites' },
  { key: 'archived', labelKey: 'papers.filter.archived' },
]

const SORT_OPTIONS = [
  { key: 'llm_score', labelKey: 'papers.sort.score' },
  { key: 'impact_score', labelKey: 'papers.sort.impact' },
  { key: 'citation_count', labelKey: 'papers.sort.citations' },
  { key: 'published_date', labelKey: 'papers.sort.date' },
]

function ScoreBadge({ score }) {
  if (score == null) return null
  let bg, color
  if (score >= 7) { bg = 'var(--ok-subtle)'; color = 'var(--ok)' }
  else if (score >= 4) { bg = 'var(--warn-subtle)'; color = 'var(--warn)' }
  else { bg = 'var(--danger-subtle)'; color = 'var(--danger)' }
  return (
    <span
      className="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold flex-shrink-0"
      style={{ background: bg, color }}
    >
      {score}
    </span>
  )
}

function PaperCard({ paper, topicName, onStatusChange }) {
  const { t } = useLanguage()
  const arxivUrl = paper.arxiv_id?.startsWith('s2:')
    ? `https://www.semanticscholar.org/paper/${paper.arxiv_id.slice(3)}`
    : `https://arxiv.org/abs/${paper.arxiv_id}`

  return (
    <div
      className="p-4 rounded-xl border transition-all"
      style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-start gap-3">
        <ScoreBadge score={paper.llm_score} />
        <div className="flex-1 min-w-0">
          <a
            href={arxivUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium hover:underline inline-flex items-center gap-1"
            style={{ color: 'var(--text-strong)' }}
          >
            {paper.title}
            <ExternalLink size={12} style={{ color: 'var(--muted)' }} />
          </a>
          <p className="text-xs mt-1 line-clamp-1" style={{ color: 'var(--muted)' }}>
            {paper.authors?.slice(0, 3).join(', ')}
            {paper.authors?.length > 3 && ' et al.'}
          </p>
          {paper.llm_reason && (
            <p className="text-xs mt-2 line-clamp-2" style={{ color: 'var(--text)' }}>
              {paper.llm_reason}
            </p>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: 'var(--muted)' }}>
            {topicName && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
                {topicName}
              </span>
            )}
            {paper.is_survey && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--warning-subtle, #fef3c7)', color: 'var(--warning, #d97706)' }}>
                {t('papers.survey')}
              </span>
            )}
            {paper.venue && <span>{paper.venue}</span>}
            {paper.year && <span>{paper.year}</span>}
            <span>{paper.citation_count || 0} {t('papers.cit')}</span>
            <span>{(paper.impact_score || 0).toFixed(2)} {t('papers.impactWord')}</span>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {paper.status !== 'favorited' && (
            <button
              onClick={() => onStatusChange(paper, 'favorited')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title={t('papers.favorite')}
            >
              <Star size={14} />
            </button>
          )}
          {paper.status !== 'archived' && (
            <button
              onClick={() => onStatusChange(paper, 'archived')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title={t('papers.archive')}
            >
              <Archive size={14} />
            </button>
          )}
          {paper.status !== 'inbox' && (
            <button
              onClick={() => onStatusChange(paper, 'inbox')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title={t('papers.moveToInbox')}
            >
              <Inbox size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function Papers() {
  const { t } = useLanguage()
  const queryClient = useQueryClient()

  const [statusFilter, setStatusFilter] = useState('highlighted')
  const [sortBy, setSortBy] = useState('llm_score')
  const [page, setPage] = useState(1)

  const { data: topics } = useQuery({
    queryKey: ['rulesets'],
    queryFn: getRulesets,
  })

  const topicMap = {}
  for (const t of topics || []) {
    topicMap[t.id] = t.name
  }

  const { data: papersData, isLoading } = useQuery({
    queryKey: ['globalPapers', statusFilter, sortBy, page],
    queryFn: () => getGlobalPapers({
      page,
      status: statusFilter || undefined,
      sort_by: sortBy,
      sort_order: 'desc',
    }),
  })

  const statusMutation = useMutation({
    mutationFn: ({ topicId, paperId, status }) => updatePaperStatus(topicId, paperId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['globalPapers'] })
    },
  })

  const handleStatusChange = useCallback((paper, status) => {
    statusMutation.mutate({ topicId: paper.topic_id, paperId: paper.id, status })
  }, [statusMutation])

  const totalPages = papersData ? Math.ceil(papersData.total / papersData.page_size) : 0

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight mb-1"
          style={{ color: 'var(--text-strong)' }}
        >
          {t('papers.title')}
        </h1>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          {t('papers.subtitle')}
        </p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {STATUS_FILTERS.map(f => {
            const active = statusFilter === f.key
            return (
              <button
                key={f.labelKey}
                onClick={() => { setStatusFilter(f.key); setPage(1) }}
                className="px-3 py-1.5 rounded-md text-xs cursor-pointer"
                style={{
                  background: active ? 'var(--accent-subtle)' : 'transparent',
                  color: active ? 'var(--accent)' : 'var(--muted)',
                  border: '1px solid var(--border)',
                }}
              >
                {t(f.labelKey)}
              </button>
            )
          })}
        </div>
        <select
          value={sortBy}
          onChange={e => { setSortBy(e.target.value); setPage(1) }}
          className="px-3 py-1.5 rounded-md text-xs cursor-pointer"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
          }}
        >
          {SORT_OPTIONS.map(s => (
            <option key={s.key} value={s.key}>{t(s.labelKey)}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[1, 2, 3, 4].map(i => (
            <div
              key={i}
              className="h-24 rounded-xl animate-pulse"
              style={{ background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      ) : papersData?.items?.length > 0 ? (
        <>
          <div className="flex flex-col gap-3">
            {papersData.items.map(paper => (
              <PaperCard
                key={`${paper.id}-${paper.topic_id}`}
                paper={paper}
                topicName={topicMap[paper.topic_id]}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded-md text-sm cursor-pointer disabled:opacity-30"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                {t('papers.previous')}
              </button>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>
                {t('papers.pageOf').replace('{page}', page).replace('{total}', totalPages)}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-md text-sm cursor-pointer disabled:opacity-30"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                {t('papers.next')}
              </button>
            </div>
          )}
        </>
      ) : (
        <div
          className="text-center py-16 rounded-xl border"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          {statusFilter === 'highlighted'
            ? <Sparkles size={48} className="mx-auto mb-4" style={{ color: 'var(--muted)' }} />
            : <BookOpen size={48} className="mx-auto mb-4" style={{ color: 'var(--muted)' }} />
          }
          <p className="text-lg font-medium mb-2" style={{ color: 'var(--text-strong)' }}>
            {statusFilter === 'highlighted' ? t('papers.noHighlights')
              : statusFilter === 'favorited' ? t('papers.noFavorites')
              : t('papers.noPapers')}
          </p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            {statusFilter === 'highlighted'
              ? t('papers.emptyHighlights')
              : statusFilter === 'favorited'
                ? t('papers.emptyFavorites')
                : t('papers.emptyDefault')}
          </p>
        </div>
      )}
    </div>
  )
}

export default Papers
