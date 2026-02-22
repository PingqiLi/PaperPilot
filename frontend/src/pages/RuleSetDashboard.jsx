import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Play, RefreshCw, Loader2, Star, Archive, Inbox, Search,
  ExternalLink, ChevronDown, ChevronUp, Settings, BookOpen, Zap, FileText,
  Map, CalendarDays, TrendingUp, Pencil, Save, X, Plus, Download, Trash2, History, Radio,
  Sparkles,
} from 'lucide-react'
import LlmLoadingBanner from '../components/LlmLoadingBanner'
import { useTasks } from '../contexts/TaskContext'
import { useLanguage } from '../contexts/LanguageContext'
import {
  getRuleset, getRulesetPapers, createRun, getRuns, getRun, updatePaperStatus,
  getDigests, createDigest, updateRuleset, exportDigestMarkdown, getReinitPreview,
  deleteRuleset, bulkUpdatePaperStatus, exportBibtex, addPaperToTopic, getTopicOverview,
} from '../api/rulesets'

function ScoreBadge({ score }) {
  if (score == null) return null
  let bg, color
  if (score >= 7) { bg = 'var(--ok-subtle)'; color = 'var(--ok)' }
  else if (score >= 4) { bg = 'var(--warn-subtle)'; color = 'var(--warn)' }
  else { bg = 'var(--danger-subtle)'; color = 'var(--danger)' }
  return (
    <span
      className="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold"
      style={{ background: bg, color }}
    >
      {score}
    </span>
  )
}

function PaperCard({ paper, rulesetId, onStatusChange, selected, onToggleSelect }) {
  const { t } = useLanguage()
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()
  const arxivUrl = paper.arxiv_id?.startsWith('s2:')
    ? `https://www.semanticscholar.org/paper/${paper.arxiv_id.slice(3)}`
    : `https://arxiv.org/abs/${paper.arxiv_id}`

  return (
    <div
      className="p-4 rounded-xl border transition-all"
      style={{
        background: 'var(--card)',
        borderColor: selected ? 'var(--accent)' : 'var(--border)',
        borderLeft: paper.is_new ? '3px solid var(--accent)' : undefined,
      }}
    >
      <div className="flex items-start gap-3">
        {onToggleSelect && (
          <input
            type="checkbox"
            checked={selected || false}
            onChange={() => onToggleSelect(paper.id)}
            className="mt-2 cursor-pointer accent-[var(--accent)]"
            style={{ width: 16, height: 16 }}
          />
        )}
        <ScoreBadge score={paper.llm_score} />
        <div
          className="flex-1 min-w-0 cursor-pointer"
          onClick={() => setExpanded(v => !v)}
        >
          <div className="inline-flex items-center gap-1.5">
            <span
              className="text-sm font-medium hover:underline cursor-pointer"
              style={{ color: 'var(--text-strong)' }}
              onClick={e => { e.stopPropagation(); navigate(`/topics/${rulesetId}/papers/${paper.id}`) }}
            >
              {paper.title}
            </span>
            <a
              href={arxivUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              title={t('paperDetail.viewOnArxiv')}
            >
              <ExternalLink size={12} style={{ color: 'var(--muted)' }} />
            </a>
          </div>
          <p className="text-xs mt-1 line-clamp-2" style={{ color: 'var(--muted)' }}>
            {paper.authors?.slice(0, 3).join(', ')}
            {paper.authors?.length > 3 && ' et al.'}
          </p>
          {paper.llm_reason && (
            <p className={`text-xs mt-2 ${expanded ? '' : 'line-clamp-2'}`} style={{ color: 'var(--text)' }}>
              {paper.llm_reason}
            </p>
          )}
          {expanded && paper.abstract && (
            <div
              className="mt-3 pt-3 text-xs leading-relaxed"
              style={{ color: 'var(--text)', borderTop: '1px solid var(--border)' }}
            >
              {paper.abstract}
            </div>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: 'var(--muted)' }}>
            {paper.is_new && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
                <Radio size={10} />
                {t('ruleSet.settings.tracked')}
              </span>
            )}
            {paper.is_survey && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--warn-subtle)', color: 'var(--warn)' }}>
                <FileText size={10} />
                {t('ruleSet.settings.survey')}
              </span>
            )}
            {paper.analyzed_at && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--ok-subtle)', color: 'var(--ok)' }}>
                <Sparkles size={10} />
                {t('ruleSet.settings.aiAnalyzed')}
              </span>
            )}
            {paper.venue && <span>{paper.venue}</span>}
            {paper.year && <span>{paper.year}</span>}
            <span>{paper.citation_count || 0} {t('paperDetail.citations')}</span>
            <span>{(paper.impact_score || 0).toFixed(2)} {t('paperDetail.impact')}</span>
            {paper.abstract && (
              <span className="ml-auto flex items-center gap-0.5" style={{ color: 'var(--accent)' }}>
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {paper.status !== 'favorited' && (
            <button
              onClick={() => onStatusChange(paper.id, 'favorited')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title={t('papers.favorite')}
            >
              <Star size={14} />
            </button>
          )}
          {paper.status !== 'archived' && (
            <button
              onClick={() => onStatusChange(paper.id, 'archived')}
              className="p-1.5 rounded-md cursor-pointer"
              style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
              title={t('papers.archive')}
            >
              <Archive size={14} />
            </button>
          )}
          {paper.status !== 'inbox' && (
            <button
              onClick={() => onStatusChange(paper.id, 'inbox')}
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

function RunProgress({ rulesetId, runId, onComplete }) {
  const { t } = useLanguage()
  const { data: run, dataUpdatedAt } = useQuery({
    queryKey: ['run', rulesetId, runId],
    queryFn: () => getRun(rulesetId, runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return (status === 'pending' || status === 'running') ? 2000 : false
    },
  })

  useEffect(() => {
    if (run && (run.status === 'completed' || run.status === 'failed') && onComplete) {
      onComplete(run)
    }
  }, [run?.status, dataUpdatedAt])

  if (!run) return null

  const { stage, done, total } = run.progress || {}
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  const STAGE_STEPS = { searching: 1, scoring: 2, done: 2 }
  const STAGE_LABELS = { searching: t('ruleSet.run.searching'), scoring: t('ruleSet.run.scoring'), done: t('ruleSet.run.done') }
  const TOTAL_STEPS = 2
  const stepNum = STAGE_STEPS[stage] || 1
  const stageLabel = STAGE_LABELS[stage] || stage || run.status

  return (
    <div
      className="p-4 rounded-xl border"
      style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
          {run.run_type === 'initialize' ? t('ruleSet.initialize') : t('ruleSet.track')} — {stageLabel}
        </span>
        <span className="text-xs" style={{ color: 'var(--muted)' }}>
          {run.status === 'completed' ? t('ruleSet.run.completed') : run.status === 'failed' ? t('ruleSet.run.failed') : `${pct}%`}
        </span>
      </div>
      {run.status === 'running' && stage && stage !== 'done' && (
        <p className="text-xs mb-2" style={{ color: 'var(--muted)' }}>
          {t('ruleSet.run.step').replace('{step}', stepNum).replace('{total}', TOTAL_STEPS)} · {done != null && total != null ? `${done}/${total}` : ''}
        </p>
      )}
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ background: 'var(--bg-hover)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: run.status === 'completed' ? '100%' : `${pct}%`,
            background: run.status === 'failed' ? 'var(--danger)' : 'var(--accent)',
          }}
        />
      </div>
      {run.error && (
        <p className="text-xs mt-2" style={{ color: 'var(--danger)' }}>{run.error}</p>
      )}
    </div>
  )
}

const DIGEST_TYPES = [
  {
    key: 'field_overview',
    labelKey: 'ruleSet.digest.fieldOverview',
    descriptionKey: 'ruleSet.digest.fieldOverviewDesc',
    icon: Map,
  },
  {
    key: 'weekly',
    labelKey: 'ruleSet.digest.weekly',
    descriptionKey: 'ruleSet.digest.weeklyDesc',
    icon: CalendarDays,
  },
  {
    key: 'monthly',
    labelKey: 'ruleSet.digest.monthly',
    descriptionKey: 'ruleSet.digest.monthlyDesc',
    icon: TrendingUp,
  },
]

function DigestTypeBadge({ type }) {
  const { t } = useLanguage()
  const styles = {
    field_overview: { bg: 'var(--accent-subtle)', color: 'var(--accent)' },
    weekly: { bg: 'var(--ok-subtle)', color: 'var(--ok)' },
    monthly: { bg: 'var(--warn-subtle)', color: 'var(--warn)' },
  }
  const s = styles[type] || styles.field_overview
  const labels = { field_overview: t('ruleSet.digest.fieldOverview'), weekly: t('ruleSet.digest.badgeWeekly'), monthly: t('ruleSet.digest.badgeMonthly') }
  return (
    <span
      className="px-2 py-0.5 rounded-md text-xs font-medium"
      style={{ background: s.bg, color: s.color }}
    >
      {labels[type] || type}
    </span>
  )
}

function PaperLink({ arxivId, children }) {
  if (!arxivId) return children
  return (
    <a
      href={`https://arxiv.org/abs/${arxivId}`}
      target="_blank"
      rel="noopener noreferrer"
      className="hover:underline"
      style={{ color: 'var(--accent)' }}
    >
      {children} <ExternalLink size={10} className="inline ml-0.5" />
    </a>
  )
}

function resolveRef(refs, index) {
  if (!refs || index == null) return null
  return refs.find(r => r.index === index)
}

function SectionList({ items, ordered, paperRefs }) {
  if (!items || items.length === 0) return null
  const Tag = ordered ? 'ol' : 'ul'
  return (
    <Tag className={`${ordered ? 'list-decimal' : 'list-disc'} pl-5 flex flex-col gap-1`}>
      {items.map((item, i) => {
        if (typeof item === 'string') {
          return <li key={i} className="text-sm" style={{ color: 'var(--text)' }}>{item}</li>
        }
        if (typeof item === 'number') {
          const ref = resolveRef(paperRefs, item)
          if (ref) {
            return (
              <li key={i} className="text-sm" style={{ color: 'var(--text)' }}>
                <PaperLink arxivId={ref.arxiv_id}>{ref.title}</PaperLink>
              </li>
            )
          }
          return <li key={i} className="text-sm" style={{ color: 'var(--text)' }}>Paper #{item}</li>
        }
        const ref = resolveRef(paperRefs, item.index)
        const title = ref?.title || item.title
        const arxivId = ref?.arxiv_id
        return (
          <li key={i} className="text-sm" style={{ color: 'var(--text)' }}>
            {title && <PaperLink arxivId={arxivId}><strong>{title}</strong></PaperLink>}
            {title && (item.reason || item.description || item.why || item.one_liner || item.significance) && ' — '}
            {item.why || item.one_liner || item.significance || item.reason || item.description || item.summary || (!title && JSON.stringify(item))}
          </li>
        )
      })}
    </Tag>
  )
}

function DigestSection({ title, children }) {
  if (!children) return null
  return (
    <div className="mb-4">
      <h4 className="text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>
        {title}
      </h4>
      {children}
    </div>
  )
}

function DigestContent({ digestType, content }) {
  const { t } = useLanguage()
  if (!content) return null
  const refs = content.paper_references || []

  if (digestType === 'field_overview') {
    const readingStages = content.reading_path ? [
      { key: 'start_with', reasonKey: 'start_reason', label: '入门必读', icon: '📖' },
      { key: 'then_read', reasonKey: 'then_reason', label: t('ruleSet.reading.then'), icon: '🔬' },
      { key: 'deep_dive', reasonKey: 'deep_reason', label: t('ruleSet.reading.deep'), icon: '🚀' },
    ].filter(s => content.reading_path[s.key]) : []
    if (readingStages.length > 0) readingStages[0].label = t('ruleSet.reading.start')

    const maturityColors = {
      emerging: { bg: 'var(--warn-subtle)', color: 'var(--warn)' },
      active: { bg: 'var(--ok-subtle)', color: 'var(--ok)' },
      mature: { bg: 'var(--accent-subtle, rgba(99,102,241,0.1))', color: 'var(--accent)' },
    }

    return (
      <div className="flex flex-col gap-1">
        <DigestSection title={t('ruleSet.digest.summary')}>
          <p className="text-sm" style={{ color: 'var(--text)' }}>{content.summary}</p>
        </DigestSection>
        <DigestSection title={t('ruleSet.digest.researchPillars')}>
          {content.pillars?.map((pillar, i) => (
            <div key={i} className="mb-3 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>{pillar.name}</span>
                {pillar.maturity && (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                    style={maturityColors[pillar.maturity] || { color: 'var(--muted)' }}
                  >
                    {pillar.maturity}
                  </span>
                )}
              </div>
              <p className="text-sm mb-2" style={{ color: 'var(--text)' }}>{pillar.description}</p>
              {pillar.key_papers?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {pillar.key_papers.map((idx, j) => {
                    const ref = resolveRef(refs, idx)
                    return ref ? (
                      <PaperLink key={j} arxivId={ref.arxiv_id}>
                        <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-md" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                          {ref.title.length > 50 ? ref.title.slice(0, 50) + '…' : ref.title}
                        </span>
                      </PaperLink>
                    ) : (
                      <span key={j} className="text-xs px-2 py-0.5 rounded-md" style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
                        Paper #{idx}
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </DigestSection>
        {readingStages.length > 0 && (
          <DigestSection title={t('ruleSet.digest.readingPath')}>
            <div className="flex flex-col gap-3">
              {readingStages.map(stage => {
                const papers = content.reading_path[stage.key]
                const reason = content.reading_path[stage.reasonKey]
                const paperList = Array.isArray(papers) ? papers : [papers]
                return (
                  <div key={stage.key} className="p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <span>{stage.icon}</span>
                      <span className="text-xs font-semibold" style={{ color: 'var(--text-strong)' }}>{stage.label}</span>
                    </div>
                    <SectionList items={paperList} paperRefs={refs} />
                    {reason && (
                      <p className="text-xs mt-1.5" style={{ color: 'var(--muted)' }}>{reason}</p>
                    )}
                  </div>
                )
              })}
            </div>
          </DigestSection>
        )}
        <DigestSection title={t('ruleSet.digest.openProblems')}>
          <SectionList items={content.open_problems} />
        </DigestSection>
      </div>
    )
  }

  if (digestType === 'weekly') {
    return (
      <div className="flex flex-col gap-1">
        <DigestSection title={t('ruleSet.digest.weekSummary')}>
          <p className="text-sm" style={{ color: 'var(--text)' }}>{content.week_summary}</p>
        </DigestSection>
        <DigestSection title={t('ruleSet.digest.mustRead')}>
          <SectionList items={content.must_read} paperRefs={refs} />
        </DigestSection>
        <DigestSection title={t('ruleSet.digest.worthNoting')}>
          <SectionList items={content.worth_noting} paperRefs={refs} />
        </DigestSection>
        {content.trend_signal && (
          <DigestSection title={t('ruleSet.digest.trendSignal')}>
            <p className="text-sm" style={{ color: 'var(--text)' }}>{content.trend_signal}</p>
          </DigestSection>
        )}
        {content.skip_reason && (
          <DigestSection title={t('ruleSet.digest.papersSkipped')}>
            <p className="text-sm" style={{ color: 'var(--muted)' }}>{content.skip_reason}</p>
          </DigestSection>
        )}
      </div>
    )
  }

  if (digestType === 'monthly') {
    return (
      <div className="flex flex-col gap-1">
        <DigestSection title={t('ruleSet.digest.monthSummary')}>
          <p className="text-sm" style={{ color: 'var(--text)' }}>{content.month_summary}</p>
        </DigestSection>
        <DigestSection title={t('ruleSet.digest.highlights')}>
          <SectionList items={content.highlights} paperRefs={refs} />
        </DigestSection>
        {content.clusters && Array.isArray(content.clusters) && (
          <DigestSection title={t('ruleSet.digest.paperClusters')}>
            {content.clusters.map((cluster, i) => (
              <div key={i} className="mb-2 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
                    {cluster.theme || cluster.name}
                  </span>
                  {(cluster.paper_indices || cluster.papers) && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'var(--card)', color: 'var(--muted)' }}>
                      {(cluster.paper_indices || cluster.papers).length} papers
                    </span>
                  )}
                </div>
                {cluster.insight && (
                  <p className="text-sm mb-2" style={{ color: 'var(--text)' }}>{cluster.insight}</p>
                )}
                {(cluster.paper_indices || cluster.papers)?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {(cluster.paper_indices || cluster.papers).map((idx, j) => {
                      const ref = resolveRef(refs, idx)
                      return ref ? (
                        <PaperLink key={j} arxivId={ref.arxiv_id}>
                          <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-md" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            {ref.title.length > 40 ? ref.title.slice(0, 40) + '…' : ref.title}
                          </span>
                        </PaperLink>
                      ) : (
                        <span key={j} className="text-xs px-2 py-0.5 rounded-md" style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
                          Paper #{idx}
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </DigestSection>
        )}
        {content.momentum && typeof content.momentum === 'object' && (
          <DigestSection title={t('ruleSet.digest.momentum')}>
            {[
              { key: 'accelerating', label: t('ruleSet.digest.accelerating'), icon: '🔥' },
              { key: 'emerging', label: t('ruleSet.digest.emerging'), icon: '🌱' },
              { key: 'declining', label: t('ruleSet.digest.declining'), icon: '📉' },
            ].map(({ key, label, icon }) => {
              const items = content.momentum[key]
              if (!items || (Array.isArray(items) && items.length === 0)) return null
              const list = Array.isArray(items) ? items : [items]
              return (
                <div key={key} className="mb-2">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-xs">{icon}</span>
                    <span className="text-xs font-medium" style={{ color: 'var(--text-strong)' }}>{label}</span>
                  </div>
                  <SectionList items={list} />
                </div>
              )
            })}
          </DigestSection>
        )}
        {content.next_month_watch && (
          <DigestSection title={t('ruleSet.digest.nextMonthWatch')}>
            {typeof content.next_month_watch === 'string' ? (
              <p className="text-sm" style={{ color: 'var(--text)' }}>{content.next_month_watch}</p>
            ) : (
              <SectionList items={Array.isArray(content.next_month_watch) ? content.next_month_watch : [content.next_month_watch]} />
            )}
          </DigestSection>
        )}
      </div>
    )
  }

  // Fallback: render raw JSON
  return (
    <pre className="text-xs p-3 rounded-lg overflow-auto" style={{ background: 'var(--bg-elevated)', color: 'var(--text)' }}>
      {JSON.stringify(content, null, 2)}
    </pre>
  )
}

function DigestCard({ digest, rulesetId }) {
  const { t } = useLanguage()
  const [expanded, setExpanded] = useState(false)
  const date = new Date(digest.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })

  const handleDownload = async (e) => {
    e.stopPropagation()
    try {
      const blob = await exportDigestMarkdown(rulesetId, digest.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const typeLabels = { field_overview: t('ruleSet.dl.fieldOverview'), weekly: t('ruleSet.dl.weekly'), monthly: t('ruleSet.dl.monthly') }
      const label = typeLabels[digest.digest_type] || digest.digest_type
      a.download = `${label}_${new Date(digest.created_at).toISOString().slice(0, 10)}.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
    >
      <div
        className="w-full flex items-center justify-between p-4"
        style={{ textAlign: 'left' }}
      >
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-3 flex-1 cursor-pointer"
          style={{ background: 'none', border: 'none', textAlign: 'left' }}
        >
          <DigestTypeBadge type={digest.digest_type} />
          <span className="text-sm" style={{ color: 'var(--text-strong)' }}>{date}</span>
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              {digest.paper_count} papers
            </span>
        </button>
        <div className="flex items-center gap-1">
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-md cursor-pointer"
            style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
            title={t('ruleSet.digest.exportMarkdown')}
          >
            <Download size={14} />
          </button>
          <button
            onClick={() => setExpanded(v => !v)}
            className="p-1.5 cursor-pointer"
            style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <div className="pt-4">
            <DigestContent digestType={digest.digest_type} content={digest.content} />
          </div>
        </div>
      )}
    </div>
  )
}

function SettingsTagInput({ tags, onChange, placeholder }) {
  const [input, setInput] = useState('')
  const addTag = () => {
    const val = input.trim()
    if (val && !tags.includes(val)) onChange([...tags, val])
    setInput('')
  }
  const removeTag = (idx) => onChange(tags.filter((_, i) => i !== idx))

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map((tag, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs"
            style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}
          >
            {tag}
            <button
              onClick={() => removeTag(idx)}
              className="cursor-pointer hover:opacity-70"
              style={{ background: 'none', border: 'none', color: 'inherit', padding: 0 }}
            >
              <X size={12} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }}
          placeholder={placeholder}
          className="flex-1 px-3 py-2 rounded-lg border text-sm"
          style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)', color: 'var(--text)' }}
        />
        <button
          type="button"
          onClick={addTag}
          className="px-3 py-2 rounded-lg text-sm cursor-pointer"
          style={{ background: 'var(--bg-hover)', color: 'var(--text)', border: '1px solid var(--border)' }}
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  )
}

function ReinitDialog({ onConfirm, onDismiss, isPending, preview }) {
  const { t } = useLanguage()
  return (
    <div
      className="p-5 rounded-xl border mb-4"
      style={{ background: 'var(--card)', borderColor: 'var(--accent)' }}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ background: 'var(--accent-subtle)' }}
        >
          <RefreshCw size={14} style={{ color: 'var(--accent)' }} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-strong)' }}>
            {t('ruleSet.reinit.updated')}
          </p>
          <p className="text-xs mb-3" style={{ color: 'var(--muted)' }}>
            {t('ruleSet.reinit.detected')}
          </p>
          {preview && (
            <div
              className="flex gap-4 text-xs mb-4 p-3 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <span style={{ color: 'var(--muted)' }}>
                {t('ruleSet.reinit.currentTotal').replace('{n}', preview.total)}
              </span>
              <span style={{ color: 'var(--muted)' }}>
                {t('ruleSet.reinit.favoritedKept').replace('{n}', preview.favorited)}
              </span>
              <span style={{ color: 'var(--danger, #ef4444)' }}>
                {t('ruleSet.reinit.willRemove').replace('{n}', preview.will_remove)}
              </span>
            </div>
          )}
          <div className="flex items-center gap-3">
            <button
              onClick={onConfirm}
              disabled={isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
              style={{ background: 'var(--accent)', color: 'var(--accent-foreground)', border: 'none' }}
            >
              {isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {t('ruleSet.reinit.confirm')}
            </button>
            <button
              onClick={onDismiss}
              className="px-4 py-2 rounded-lg text-sm cursor-pointer"
              style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text)' }}
            >
              {t('ruleSet.reinit.later')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function AddPaperForm({ rulesetId, onAdded }) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [successMsg, setSuccessMsg] = useState(null)

  const mutation = useMutation({
    mutationFn: (identifier) => addPaperToTopic(rulesetId, identifier),
    onSuccess: (data) => {
      setInput('')
      setOpen(false)
      setSuccessMsg(data.title ? t('ruleSet.addPaper.success').replace('{title}', data.title) : data.message)
      onAdded()
      setTimeout(() => setSuccessMsg(null), 3000)
    },
  })

  if (!open && !successMsg) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs cursor-pointer mb-4"
        style={{ background: 'transparent', border: '1px dashed var(--border)', color: 'var(--muted)' }}
      >
        <Plus size={12} />
        {t('ruleSet.settings.addPaper')}
      </button>
    )
  }

  return (
    <div className="mb-4 flex flex-col gap-2">
      {successMsg && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
          style={{ background: 'var(--ok-subtle)', color: 'var(--ok)' }}
        >
          <Star size={12} />
          {successMsg}
        </div>
      )}
      {open && (
        <div
          className="flex items-center gap-2"
        >
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && input.trim()) mutation.mutate(input.trim()) }}
            placeholder="Enter ArXiv ID or URL (e.g., 2501.12345)"
            className="flex-1 px-3 py-2 rounded-lg border text-sm"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)', color: 'var(--text)' }}
            disabled={mutation.isPending}
            autoFocus
          />
          <button
            onClick={() => { if (input.trim()) mutation.mutate(input.trim()) }}
            disabled={!input.trim() || mutation.isPending}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
            style={{ background: 'var(--accent)', color: 'var(--accent-foreground)', border: 'none' }}
          >
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            {t('ruleSet.addPaper.add')}
          </button>
          <button
            onClick={() => { setOpen(false); setInput(''); mutation.reset() }}
            className="p-2 rounded-lg cursor-pointer"
            style={{ background: 'transparent', border: 'none', color: 'var(--muted)' }}
          >
            <X size={14} />
          </button>
        </div>
      )}
      {mutation.isError && (
        <p className="text-xs" style={{ color: 'var(--danger)' }}>
          {mutation.error?.response?.data?.detail || t('ruleSet.addPaper.failed')}
        </p>
      )}
    </div>
  )
}

function hasSignificantChanges(oldRuleset, newForm) {
  const fields = ['topic_sentence', 'categories', 'keywords_include', 'keywords_exclude', 'search_queries', 'source_filter']
  for (const f of fields) {
    const oldVal = JSON.stringify(oldRuleset[f] || '')
    const newVal = JSON.stringify(newForm[f] || '')
    if (oldVal !== newVal) return true
  }
  return false
}

function EditableSettings({ ruleset, onSaved, onReinit, onDeleted }) {
  const { t } = useLanguage()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [showReinitDialog, setShowReinitDialog] = useState(false)
  const [savedRuleset, setSavedRuleset] = useState(null)
  const [reinitPreview, setReinitPreview] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const startEditing = () => {
    setForm({
      name: ruleset.name,
      topic_sentence: ruleset.topic_sentence,
      categories: [...(ruleset.categories || [])],
      keywords_include: [...(ruleset.keywords_include || [])],
      keywords_exclude: [...(ruleset.keywords_exclude || [])],
      search_queries: [...(ruleset.search_queries || [])],
      source_filter: ruleset.source_filter || 'all',
    })
    setEditing(true)
    setShowReinitDialog(false)
    setReinitPreview(null)
  }

  const saveMutation = useMutation({
    mutationFn: () => updateRuleset(ruleset.id, form),
    onSuccess: async () => {
      const needsReinit = ruleset.is_initialized && hasSignificantChanges(ruleset, form)
      setSavedRuleset({ ...ruleset })
      setEditing(false)
      onSaved()
      if (needsReinit) {
        try {
          const preview = await getReinitPreview(ruleset.id)
          setReinitPreview(preview)
        } catch { /* ignore */ }
        setShowReinitDialog(true)
      }
    },
  })

  const reinitMutation = useMutation({
    mutationFn: () => createRun(ruleset.id, 'initialize', { reinit: true }),
    onSuccess: (data) => {
      setShowReinitDialog(false)
      onReinit(data)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteRuleset(ruleset.id),
    onSuccess: () => onDeleted(),
  })

  const update = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  if (!editing) {
    return (
      <div className="flex flex-col gap-4">
        {showReinitDialog && (
          <ReinitDialog
            onConfirm={() => reinitMutation.mutate()}
            onDismiss={() => setShowReinitDialog(false)}
            isPending={reinitMutation.isPending}
            preview={reinitPreview}
          />
        )}
        {reinitMutation.isError && (
          <div
            className="flex items-center gap-3 p-4 rounded-xl border"
            style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
          >
              <span className="text-sm" style={{ color: 'var(--danger)' }}>
                {reinitMutation.error?.response?.data?.detail || t('settings.failedToSave')}
              </span>
            </div>
        )}
        <div className="flex justify-end">
          <button
            onClick={startEditing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            <Pencil size={12} />
            {t('ruleSet.settings.edit')}
          </button>
        </div>
        <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.categories')}</h3>
          <div className="flex flex-wrap gap-1.5">
            {(ruleset.categories || []).map((c, i) => (
              <span key={i} className="px-2 py-0.5 rounded-md text-xs" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>{c}</span>
            ))}
          </div>
        </div>
        <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.searchQueries')}</h3>
          <div className="flex flex-col gap-1.5">
            {(ruleset.search_queries || []).map((q, i) => (
              <span key={i} className="text-sm" style={{ color: 'var(--text)' }}>{i + 1}. {q}</span>
            ))}
          </div>
        </div>
        <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.keywords')}</h3>
          <div className="mb-3">
            <span className="text-xs font-medium" style={{ color: 'var(--muted)' }}>{t('ruleSet.settings.include')}</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {(ruleset.keywords_include || []).map((k, i) => (
                <span key={i} className="px-2 py-0.5 rounded-md text-xs" style={{ background: 'var(--ok-subtle)', color: 'var(--ok)' }}>{k}</span>
              ))}
            </div>
          </div>
          <div>
            <span className="text-xs font-medium" style={{ color: 'var(--muted)' }}>{t('ruleSet.settings.exclude')}</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {(ruleset.keywords_exclude || []).map((k, i) => (
                <span key={i} className="px-2 py-0.5 rounded-md text-xs" style={{ background: 'var(--danger-subtle)', color: 'var(--danger)' }}>{k}</span>
              ))}
            </div>
          </div>
        </div>
        <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.source')}</h3>
          <span className="text-sm" style={{ color: 'var(--text)' }}>
            {{ all: t('ruleSet.settings.sourceAll'), arxiv: t('ruleSet.settings.sourceArxiv'), open_access: t('ruleSet.settings.sourceOpenAccess') }[ruleset.source_filter || 'all']}
          </span>
        </div>

        <div
          className="p-5 rounded-xl border mt-4"
          style={{ borderColor: 'var(--danger, #ef4444)', background: 'var(--card)' }}
        >
          <h3 className="text-sm font-medium mb-1" style={{ color: 'var(--danger, #ef4444)' }}>
            {t('ruleSet.settings.dangerZone')}
          </h3>
          <p className="text-xs mb-3" style={{ color: 'var(--muted)' }}>
            {t('ruleSet.settings.deleteDesc')}
          </p>
          {showDeleteConfirm ? (
            <div className="flex items-center gap-3">
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
                style={{ background: 'var(--danger, #ef4444)', color: '#fff', border: 'none' }}
              >
                {deleteMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                {t('ruleSet.settings.confirmDelete')}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 rounded-lg text-sm cursor-pointer"
                style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                {t('ruleSet.settings.cancel')}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm cursor-pointer"
              style={{ background: 'transparent', border: '1px solid var(--danger, #ef4444)', color: 'var(--danger, #ef4444)' }}
            >
              <Trash2 size={14} />
              {t('ruleSet.settings.deleteTopic')}
            </button>
          )}
          {deleteMutation.isError && (
            <p className="text-xs mt-2" style={{ color: 'var(--danger, #ef4444)' }}>
              {deleteMutation.error?.response?.data?.detail || t('settings.failedToSave')}
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.wizard.name')}</label>
        <input
          value={form.name}
          onChange={e => update('name', e.target.value)}
          className="w-full px-3 py-2 rounded-lg border text-sm"
          style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)', color: 'var(--text)' }}
        />
      </div>
      <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.wizard.topic')}</label>
        <textarea
          value={form.topic_sentence}
          onChange={e => update('topic_sentence', e.target.value)}
          rows={3}
          className="w-full px-3 py-2 rounded-lg border text-sm resize-none"
          style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)', color: 'var(--text)' }}
        />
      </div>
      <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.categories')}</label>
        <SettingsTagInput tags={form.categories} onChange={val => update('categories', val)} placeholder="e.g. cs.AI" />
      </div>
      <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.searchQueries')}</label>
        <SettingsTagInput tags={form.search_queries} onChange={val => update('search_queries', val)} placeholder="Add search query" />
      </div>
      <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.wizard.includeKeywords')}</label>
        <SettingsTagInput tags={form.keywords_include} onChange={val => update('keywords_include', val)} placeholder="Add keyword" />
      </div>
      <div className="p-5 rounded-xl border" style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.wizard.excludeKeywords')}</label>
        <SettingsTagInput tags={form.keywords_exclude} onChange={val => update('keywords_exclude', val)} placeholder="Add keyword to exclude" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-strong)' }}>{t('ruleSet.settings.source')}</label>
        <select
          value={form.source_filter || 'all'}
          onChange={e => update('source_filter', e.target.value)}
          className="w-full px-3 py-2 rounded-lg border text-sm"
          style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)', color: 'var(--text)' }}
        >
          <option value="all">{t('ruleSet.settings.sourceAll')}</option>
          <option value="arxiv">{t('ruleSet.wizard.sourceArxiv')}</option>
          <option value="open_access">{t('ruleSet.settings.sourceOpenAccess')}</option>
        </select>
      </div>
      <div className="flex items-center gap-3 justify-end">
        <button
          onClick={() => setEditing(false)}
          className="px-4 py-2 rounded-lg text-sm cursor-pointer"
          style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text)' }}
        >
          {t('ruleSet.settings.cancel')}
        </button>
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
          style={{ background: 'var(--accent)', color: 'var(--accent-foreground)', border: 'none' }}
        >
          {saveMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {saveMutation.isPending ? t('ruleSet.settings.saving') : t('ruleSet.settings.saveChanges')}
        </button>
      </div>
      {saveMutation.isError && (
        <p className="text-sm" style={{ color: 'var(--danger)' }}>
          {saveMutation.error?.response?.data?.detail || t('settings.failedToSave')}
        </p>
      )}
    </div>
  )
}

function RuleSetDashboard() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useTasks()
  const { t } = useLanguage()
  const [tab, setTab] = useState('papers')
  const [statusFilter, setStatusFilter] = useState(null)
  const [sourceFilter, setSourceFilter] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeRunId, setActiveRunId] = useState(null)
  const [page, setPage] = useState(1)
  const [generatingDigest, setGeneratingDigest] = useState(null)
  const [digestTab, setDigestTab] = useState('field_overview')
  const [showDigestHistory, setShowDigestHistory] = useState(false)
  const [selectedPapers, setSelectedPapers] = useState(new Set())

  const { data: ruleset } = useQuery({
    queryKey: ['ruleset', id],
    queryFn: () => getRuleset(id),
  })

  const { data: overviewData } = useQuery({
    queryKey: ['topicOverview'],
    queryFn: getTopicOverview,
  })
  const topicOverview = overviewData?.find(t => t.id === parseInt(id))

  useEffect(() => {
    let cancelled = false
    getRuns(id).then(runs => {
      if (cancelled) return
      const active = runs.find(r => r.status === 'pending' || r.status === 'running')
      if (active) setActiveRunId(active.id)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [id])

  const [debouncedSearch, setDebouncedSearch] = useState('')
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const { data: papersData, isLoading: papersLoading } = useQuery({
    queryKey: ['rulesetPapers', id, page, statusFilter, sourceFilter, debouncedSearch],
    queryFn: () => getRulesetPapers(id, {
      page,
      status: statusFilter,
      source: sourceFilter,
      search: debouncedSearch || undefined,
      sort_by: 'llm_score',
      sort_order: 'desc',
    }),
    enabled: tab === 'papers',
  })

  const runMutation = useMutation({
    mutationFn: (runType) => createRun(id, runType),
    onSuccess: (data) => {
      setActiveRunId(data.id)
      if (data.task_id) {
        addToast({ id: data.task_id, title: `Running ${data.run_type || 'operation'}...`, taskId: data.task_id })
      }
    },
    onError: (error) => {
      if (error?.response?.status === 409) {
        getRuns(id).then(runs => {
          const active = runs.find(r => r.status === 'pending' || r.status === 'running')
          if (active) setActiveRunId(active.id)
        }).catch(() => {})
      }
    },
  })

  const { data: digestsData, isLoading: digestsLoading } = useQuery({
    queryKey: ['digests', id],
    queryFn: () => getDigests(id),
    enabled: tab === 'digests',
    refetchInterval: tab === 'digests' ? 10000 : false,
  })

  const digestMutation = useMutation({
    mutationFn: (digestType) => createDigest(id, digestType),
    onMutate: (digestType) => setGeneratingDigest(digestType),
    onSuccess: (data) => {
      setGeneratingDigest(null)
      if (data.task_id) {
        addToast({ id: data.task_id, title: `Generating ${digestTab} digest...`, taskId: data.task_id })
      }
    },
    onError: () => setGeneratingDigest(null),
  })

  const statusMutation = useMutation({
    mutationFn: ({ paperId, status }) => updatePaperStatus(id, paperId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rulesetPapers', id] })
    },
  })

  const handleStatusChange = useCallback((paperId, status) => {
    statusMutation.mutate({ paperId, status })
  }, [statusMutation])

  const bulkMutation = useMutation({
    mutationFn: ({ paperIds, status }) => bulkUpdatePaperStatus(id, paperIds, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rulesetPapers', id] })
      setSelectedPapers(new Set())
    },
  })

  const toggleSelect = useCallback((paperId) => {
    setSelectedPapers(prev => {
      const next = new Set(prev)
      next.has(paperId) ? next.delete(paperId) : next.add(paperId)
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(() => {
    if (!papersData?.items) return
    const allIds = papersData.items.map(p => p.id)
    const allSelected = allIds.every(id => selectedPapers.has(id))
    setSelectedPapers(allSelected ? new Set() : new Set(allIds))
  }, [papersData, selectedPapers])

  const handleBibtexExport = async () => {
    try {
      const blob = await exportBibtex(id, statusFilter)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${ruleset?.name || 'papers'}.bib`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  if (!ruleset) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 w-64 rounded-lg mb-4" style={{ background: 'var(--bg-elevated)' }} />
          <div className="h-4 w-96 rounded-lg" style={{ background: 'var(--bg-elevated)' }} />
        </div>
      </div>
    )
  }

  const TABS = [
    { key: 'papers', label: t('ruleSet.tab.papers'), icon: BookOpen },
    { key: 'digests', label: t('ruleSet.tab.digests'), icon: FileText },
    { key: 'settings', label: t('ruleSet.tab.settings'), icon: Settings },
  ]

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1.5 text-sm mb-4 cursor-pointer"
        style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
      >
        <ArrowLeft size={16} />
        {t('ruleSet.allTopics')}
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-semibold tracking-tight"
            style={{ color: 'var(--text-strong)' }}
          >
            {ruleset.name}
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
            {ruleset.topic_sentence}
          </p>
          {topicOverview && (
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <div className="flex items-center gap-1.5">
                <BookOpen size={13} style={{ color: 'var(--accent)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
                  {topicOverview.paper_counts.initialize}
                </span>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('ruleSet.paperCount.foundational')}</span>
              </div>
              <span className="text-[10px]" style={{ color: 'var(--border-strong)' }}>·</span>
              <div className="flex items-center gap-1.5">
                <TrendingUp size={13} style={{ color: 'var(--ok)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
                  {topicOverview.paper_counts.track}
                </span>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('ruleSet.paperCount.tracked')}</span>
                {topicOverview.last_track_at && (
                  <span
                    className="text-xs font-medium"
                    style={{ color: topicOverview.track_latest_count > 0 ? 'var(--ok)' : 'var(--muted)' }}
                  >
                    (+{topicOverview.track_latest_count})
                  </span>
                )}
              </div>
              <span className="text-[10px]" style={{ color: 'var(--border-strong)' }}>·</span>
              <div className="flex items-center gap-1.5">
                <Star size={13} style={{ color: 'var(--warn)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
                  {topicOverview.paper_counts.favorited}
                </span>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('ruleSet.paperCount.favorites')}</span>
              </div>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {!ruleset.is_initialized && !activeRunId && (
            <button
              onClick={() => runMutation.mutate('initialize')}
              disabled={runMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
              style={{
                background: 'var(--accent)',
                color: 'var(--accent-foreground)',
                border: 'none',
              }}
            >
              {runMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {t('ruleSet.initialize')}
            </button>
          )}
          {ruleset.is_initialized && !activeRunId && (
            <button
              onClick={() => runMutation.mutate('track')}
              disabled={runMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text)',
                border: '1px solid var(--border)',
              }}
            >
              {runMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {t('ruleSet.track')}
            </button>
          )}
        </div>
      </div>

      {activeRunId && (
        <div className="mb-4">
          <RunProgress
            rulesetId={id}
            runId={activeRunId}
            onComplete={() => {
              queryClient.invalidateQueries({ queryKey: ['ruleset', id] })
              queryClient.invalidateQueries({ queryKey: ['rulesetPapers', id] })
            }}
          />
        </div>
      )}

      <div
        className="flex gap-1 p-1 rounded-lg mb-6"
        style={{ background: 'var(--bg-elevated)' }}
      >
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className="flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors cursor-pointer"
            style={{
              background: tab === key ? 'var(--card)' : 'transparent',
              color: tab === key ? 'var(--text-strong)' : 'var(--muted)',
              border: 'none',
              boxShadow: tab === key ? 'var(--shadow-sm)' : 'none',
            }}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'papers' && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            {[
               { key: 'All', label: t('ruleSet.filter.all'), icon: null },
               { key: 'inbox', label: t('ruleSet.filter.inbox'), icon: Inbox },
               { key: 'favorited', label: t('ruleSet.filter.favorited'), icon: Star },
               { key: 'archived', label: t('ruleSet.filter.archived'), icon: Archive },
            ].map(({ key: s, label, icon: Icon }) => (
              <button
                key={s}
                onClick={() => { setStatusFilter(s === 'All' ? null : s); setPage(1) }}
                className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs cursor-pointer"
                style={{
                  background: (s === 'All' ? !statusFilter : statusFilter === s)
                    ? 'var(--accent-subtle)' : 'transparent',
                  color: (s === 'All' ? !statusFilter : statusFilter === s)
                    ? 'var(--accent)' : 'var(--muted)',
                  border: '1px solid var(--border)',
                }}
              >
                {Icon && <Icon size={12} />}
                {label}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={handleBibtexExport}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs cursor-pointer"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--muted)' }}
                title={t('ruleSet.exportBibtex')}
              >
                <Download size={12} />
                BibTeX
              </button>
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-2.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--muted)' }}
                />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Search papers..."
                  className="pl-8 pr-3 py-1.5 rounded-md text-xs w-48"
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    color: 'var(--text)',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
          </div>

          {selectedPapers.size > 0 && (
            <div
              className="flex items-center gap-3 p-3 rounded-lg mb-4"
              style={{ background: 'var(--accent-subtle)' }}
            >
                <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>
                  {t('ruleSet.bulk.selected').replace('{n}', selectedPapers.size)}
                </span>
              <button
                onClick={() => bulkMutation.mutate({ paperIds: [...selectedPapers], status: 'favorited' })}
                disabled={bulkMutation.isPending}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs cursor-pointer"
                style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                 <Star size={12} /> {t('ruleSet.bulk.favorite')}
              </button>
              <button
                onClick={() => bulkMutation.mutate({ paperIds: [...selectedPapers], status: 'archived' })}
                disabled={bulkMutation.isPending}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs cursor-pointer"
                style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                 <Archive size={12} /> {t('ruleSet.bulk.archive')}
              </button>
              <button
                onClick={() => bulkMutation.mutate({ paperIds: [...selectedPapers], status: 'inbox' })}
                disabled={bulkMutation.isPending}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs cursor-pointer"
                style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                 <Inbox size={12} /> {t('ruleSet.bulk.inbox')}
              </button>
              <button
                onClick={() => setSelectedPapers(new Set())}
                className="ml-auto px-2.5 py-1 rounded-md text-xs cursor-pointer"
                style={{ background: 'transparent', border: 'none', color: 'var(--muted)' }}
              >
                 {t('ruleSet.bulk.clear')}
               </button>
            </div>
          )}

          <AddPaperForm
            rulesetId={id}
            onAdded={() => queryClient.invalidateQueries({ queryKey: ['rulesetPapers', id] })}
          />

          {papersLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map(i => (
                <div
                  key={i}
                  className="h-24 rounded-xl animate-pulse"
                  style={{ background: 'var(--bg-elevated)' }}
                />
              ))}
            </div>
          ) : papersData?.items?.length > 0 ? (
            <>
              <div className="flex items-center gap-2 mb-2">
                <input
                  type="checkbox"
                  checked={papersData.items.length > 0 && papersData.items.every(p => selectedPapers.has(p.id))}
                  onChange={toggleSelectAll}
                  className="cursor-pointer accent-[var(--accent)]"
                  style={{ width: 16, height: 16 }}
                />
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('ruleSet.selectAllPage')}</span>
              </div>
              <div className="flex flex-col gap-3">
                {papersData.items.map(paper => (
                  <PaperCard
                    key={paper.id}
                    paper={paper}
                    rulesetId={id}
                    onStatusChange={handleStatusChange}
                    selected={selectedPapers.has(paper.id)}
                    onToggleSelect={toggleSelect}
                  />
                ))}
              </div>
              {papersData.total > papersData.page_size && (
                <div className="flex items-center justify-center gap-2 mt-6">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1.5 rounded-md text-sm cursor-pointer disabled:opacity-30"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
                  >
                    {t('ruleSet.previous')}
                  </button>
                  <span className="text-xs" style={{ color: 'var(--muted)' }}>
                    {t('ruleSet.pageOf').replace('{page}', page).replace('{total}', Math.ceil(papersData.total / papersData.page_size))}
                  </span>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= Math.ceil(papersData.total / papersData.page_size)}
                    className="px-3 py-1.5 rounded-md text-sm cursor-pointer disabled:opacity-30"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
                  >
                    {t('ruleSet.next')}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div
              className="text-center py-12 rounded-xl border"
              style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
            >
              <BookOpen size={40} className="mx-auto mb-3" style={{ color: 'var(--muted)' }} />
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                {ruleset.is_initialized
                  ? t('ruleSet.empty.noMatch')
                  : t('ruleSet.empty.runInitialize')}
              </p>
            </div>
          )}
        </div>
      )}

      {tab === 'digests' && (() => {
        const allDigests = digestsData?.items || []
        const filtered = allDigests.filter(d => d.digest_type === digestTab)
        const latest = filtered[0] || null
        const older = filtered.slice(1)
        const activeType = DIGEST_TYPES.find(t => t.key === digestTab)
        const genLabel = {
          field_overview: t('ruleSet.digest.fieldOverview').toLowerCase(),
          weekly: t('ruleSet.digest.weekly').toLowerCase(),
          monthly: t('ruleSet.digest.monthly').toLowerCase(),
        }

        return (
          <div>
            <div className="flex items-center gap-1 mb-5" style={{ borderBottom: '1px solid var(--border)' }}>
              <div className="flex items-center gap-0.5 flex-1">
                {DIGEST_TYPES.map(({ key, labelKey, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => { setDigestTab(key); setShowDigestHistory(false) }}
                    className="flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium cursor-pointer transition-colors relative"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: digestTab === key ? 'var(--accent)' : 'var(--muted)',
                    }}
                  >
                    <Icon size={14} />
                    {t(labelKey)}
                    {digestTab === key && (
                      <span
                        className="absolute bottom-0 left-2 right-2 rounded-full"
                        style={{ height: 2, background: 'var(--accent)' }}
                      />
                    )}
                  </button>
                ))}
              </div>
              <button
                onClick={() => digestMutation.mutate(digestTab)}
                disabled={generatingDigest != null}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer disabled:opacity-40 mb-1.5"
                style={{
                  background: 'var(--accent)',
                  color: 'var(--accent-foreground)',
                  border: 'none',
                }}
              >
                {generatingDigest === digestTab
                  ? <Loader2 size={12} className="animate-spin" />
                  : <RefreshCw size={12} />
                }
                {latest ? t('ruleSet.digest.regenerate') : t('ruleSet.digest.generate')}
              </button>
            </div>

            {generatingDigest && (
              <div
                className="flex items-center gap-2.5 p-3 rounded-lg mb-4"
                style={{ background: 'var(--accent-subtle)' }}
              >
                <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent)' }} />
                <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>
                  {t('ruleSet.digest.generating').replace('{type}', genLabel[generatingDigest] || generatingDigest)}
                </span>
              </div>
            )}

            {digestMutation.isError && (
              <div
                className="flex items-center gap-3 p-4 rounded-xl border mb-4"
                style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
              >
                <span className="text-sm" style={{ color: 'var(--danger)' }}>
                  {t('ruleSet.digest.failed').replace('{error}', digestMutation.error?.response?.data?.detail || t('settings.failedToSave'))}
                </span>
              </div>
            )}

            {digestsLoading ? (
              <div className="flex flex-col gap-3">
                {[1, 2].map(i => (
                  <div
                    key={i}
                    className="h-24 rounded-xl animate-pulse"
                    style={{ background: 'var(--bg-elevated)' }}
                  />
                ))}
              </div>
            ) : latest ? (
              <div className="flex flex-col gap-3">
                <div
                  className="rounded-xl border overflow-hidden"
                  style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
                >
                  <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
                        {new Date(latest.created_at).toLocaleDateString('en-US', {
                          month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--muted)' }}>
                        {latest.paper_count} papers
                      </span>
                    </div>
                    <button
                      onClick={async () => {
                        try {
                          const blob = await exportDigestMarkdown(id, latest.id)
                          const url = URL.createObjectURL(blob)
                          const a = document.createElement('a')
                          a.href = url
                          const typeLabels = { field_overview: t('ruleSet.dl.fieldOverview'), weekly: t('ruleSet.dl.weekly'), monthly: t('ruleSet.dl.monthly') }
                          a.download = `${typeLabels[latest.digest_type] || latest.digest_type}_${new Date(latest.created_at).toISOString().slice(0, 10)}.md`
                          a.click()
                          URL.revokeObjectURL(url)
                        } catch {}
                      }}
                      className="p-1.5 rounded-md cursor-pointer"
                      style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
                      title={t('ruleSet.digest.exportMarkdown')}
                    >
                      <Download size={14} />
                    </button>
                  </div>
                  <div className="p-4">
                    <DigestContent digestType={latest.digest_type} content={latest.content} />
                  </div>
                </div>

                {digestTab !== 'field_overview' && older.length > 0 && (
                  <div>
                    <button
                      onClick={() => setShowDigestHistory(v => !v)}
                      className="flex items-center gap-1.5 text-xs cursor-pointer mb-2"
                      style={{ background: 'none', border: 'none', color: 'var(--muted)', padding: 0 }}
                    >
                      <History size={12} />
                      {t('ruleSet.digest.past').replace('{label}', activeType ? t(activeType.labelKey) : t('ruleSet.tab.digests')).replace('{count}', older.length)}
                      {showDigestHistory ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                    {showDigestHistory && (
                      <div className="flex flex-col gap-2">
                        {older.map(digest => (
                          <DigestCard key={digest.id} digest={digest} rulesetId={id} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : !generatingDigest ? (
              <div
                className="text-center py-16 rounded-xl border"
                style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
              >
                {activeType && <activeType.icon size={36} className="mx-auto mb-3" style={{ color: 'var(--muted)', opacity: 0.5 }} />}
                <p className="text-sm mb-1" style={{ color: 'var(--muted)' }}>
                  {t('ruleSet.digest.none').replace('{type}', activeType ? t(activeType.labelKey).toLowerCase() : t('ruleSet.tab.digests').toLowerCase())}
                </p>
                <p className="text-xs" style={{ color: 'var(--muted)', opacity: 0.7 }}>
                  {t('ruleSet.digest.clickGenerate').replace('{action}', latest ? t('ruleSet.digest.regenerate') : t('ruleSet.digest.generate'))}
                </p>
              </div>
            ) : null}
          </div>
        )
      })()}

      {tab === 'settings' && (
        <EditableSettings
          ruleset={ruleset}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['ruleset', id] })}
          onReinit={(runData) => {
            setActiveRunId(runData.id)
            setTab('papers')
            queryClient.invalidateQueries({ queryKey: ['ruleset', id] })
            queryClient.invalidateQueries({ queryKey: ['rulesetPapers', id] })
          }}
          onDeleted={() => {
            queryClient.invalidateQueries({ queryKey: ['rulesets'] })
            queryClient.invalidateQueries({ queryKey: ['topicOverview'] })
            navigate('/')
          }}
        />
      )}
    </div>
  )
}

export default RuleSetDashboard
