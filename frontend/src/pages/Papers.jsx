import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ExternalLink, Star, Archive, Inbox, BookOpen, Sparkles,
} from 'lucide-react'
import { getGlobalPapers, getRulesets, updatePaperStatus } from '../api/rulesets'

const STATUS_FILTERS = [
  { key: 'highlighted', label: 'Highlights' },
  { key: null, label: 'All' },
  { key: 'favorited', label: 'Favorites' },
  { key: 'archived', label: 'Archived' },
]

const SORT_OPTIONS = [
  { key: 'llm_score', label: 'Score' },
  { key: 'impact_score', label: 'Impact' },
  { key: 'citation_count', label: 'Citations' },
  { key: 'published_date', label: 'Date' },
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
                综述
              </span>
            )}
            {paper.venue && <span>{paper.venue}</span>}
            {paper.year && <span>{paper.year}</span>}
            <span>{paper.citation_count || 0} cit.</span>
            <span>{(paper.impact_score || 0).toFixed(2)} impact</span>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {paper.status !== 'favorited' && (
            <button
              onClick={() => onStatusChange(paper, 'favorited')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title="Favorite"
            >
              <Star size={14} />
            </button>
          )}
          {paper.status !== 'archived' && (
            <button
              onClick={() => onStatusChange(paper, 'archived')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title="Archive"
            >
              <Archive size={14} />
            </button>
          )}
          {paper.status !== 'inbox' && (
            <button
              onClick={() => onStatusChange(paper, 'inbox')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title="Move to inbox"
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
          Highlights
        </h1>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          Top-scored papers across all topics
        </p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {STATUS_FILTERS.map(f => {
            const active = statusFilter === f.key
            return (
              <button
                key={f.label}
                onClick={() => { setStatusFilter(f.key); setPage(1) }}
                className="px-3 py-1.5 rounded-md text-xs cursor-pointer"
                style={{
                  background: active ? 'var(--accent-subtle)' : 'transparent',
                  color: active ? 'var(--accent)' : 'var(--muted)',
                  border: '1px solid var(--border)',
                }}
              >
                {f.label}
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
            <option key={s.key} value={s.key}>{s.label}</option>
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
                Previous
              </button>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-md text-sm cursor-pointer disabled:opacity-30"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                Next
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
            {statusFilter === 'highlighted' ? 'No highlights yet'
              : statusFilter === 'favorited' ? 'No favorites yet'
              : 'No papers found'}
          </p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            {statusFilter === 'highlighted'
              ? 'Create a topic to discover high-scoring papers'
              : statusFilter === 'favorited'
                ? 'Star papers to save them here'
                : 'Try a different filter or create a new topic'}
          </p>
        </div>
      )}
    </div>
  )
}

export default Papers
