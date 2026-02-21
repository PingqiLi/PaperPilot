import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, ExternalLink, Star, Archive, Inbox, Sparkles,
  Loader2, BookOpen, FlaskConical, Lightbulb, AlertTriangle,
  Users, Calendar, Building2, Quote, RefreshCw,
} from 'lucide-react'
import { getPaperDetail, analyzePaper, updatePaperStatus } from '../api/rulesets'
import { useTasks } from '../contexts/TaskContext'
import LlmLoadingBanner from '../components/LlmLoadingBanner'

function Badge({ children, color }) {
  const colors = {
    blue: { bg: 'var(--accent-subtle)', text: 'var(--accent)' },
    green: { bg: 'var(--ok-subtle)', text: 'var(--ok)' },
    yellow: { bg: 'var(--warn-subtle)', text: 'var(--warn)' },
    red: { bg: 'var(--danger-subtle)', text: 'var(--danger)' },
  }
  const c = colors[color] || colors.blue
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium"
      style={{ background: c.bg, color: c.text }}
    >
      {children}
    </span>
  )
}

function ScoreRing({ score }) {
  if (score == null) return null
  let color
  if (score >= 7) color = 'var(--ok)'
  else if (score >= 4) color = 'var(--warn)'
  else color = 'var(--danger)'
  return (
    <div
      className="flex items-center justify-center rounded-full text-2xl font-bold shrink-0"
      style={{
        width: 64, height: 64,
        border: `3px solid ${color}`,
        color,
        background: 'var(--card)',
      }}
    >
      {score}
    </div>
  )
}

function AnalysisSection({ icon: Icon, title, children, color }) {
  if (!children) return null
  const colors = {
    blue: 'var(--accent)',
    green: 'var(--ok)',
    yellow: 'var(--warn)',
    red: 'var(--danger)',
    purple: '#a855f7',
  }
  return (
    <div className="mb-5">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={15} style={{ color: colors[color] || 'var(--accent)' }} />
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>{title}</h3>
      </div>
      {children}
    </div>
  )
}

function AnalysisPanel({ analysis, analyzedAt, onReanalyze, isAnalyzing }) {
  if (isAnalyzing) {
    return (
      <LlmLoadingBanner
        message="正在分析论文..."
        detail="LLM 正在读取论文内容并生成深度分析报告，通常需要 30-90 秒。"
      />
    )
  }

  if (!analysis) {
    return (
      <div
        className="text-center py-12 rounded-xl border"
        style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
      >
        <Sparkles size={36} className="mx-auto mb-3" style={{ color: 'var(--muted)' }} />
        <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-strong)' }}>
          尚未生成分析报告
        </p>
        <p className="text-xs mb-4" style={{ color: 'var(--muted)' }}>
          点击下方按钮，AI 将读取论文全文并生成结构化深度分析
        </p>
        <button
          onClick={onReanalyze}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer mx-auto"
          style={{ background: 'var(--accent)', color: 'var(--accent-foreground)', border: 'none' }}
        >
          <Sparkles size={14} />
          生成分析报告
        </button>
      </div>
    )
  }

  return (
    <div
      className="rounded-xl border p-5"
      style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles size={16} style={{ color: 'var(--accent)' }} />
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
            AI 深度分析
          </h2>
          {analysis._source === 'full_text' && (
            <Badge color="green">全文分析</Badge>
          )}
          {analysis._source === 'abstract_only' && (
            <Badge color="yellow">摘要分析</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {analyzedAt && (
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              {new Date(analyzedAt).toLocaleDateString('zh-CN')}
            </span>
          )}
          <button
            onClick={onReanalyze}
            className="p-1.5 rounded-md cursor-pointer"
            style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
            title="重新分析"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {analysis.one_liner && (
        <div
          className="p-3 rounded-lg mb-4 text-sm font-medium italic"
          style={{ background: 'var(--accent-subtle)', color: 'var(--accent)', borderLeft: '3px solid var(--accent)' }}
        >
          {analysis.one_liner}
        </div>
      )}

      <AnalysisSection icon={Lightbulb} title="核心问题" color="blue">
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>{analysis.problem}</p>
      </AnalysisSection>

      {analysis.innovations?.length > 0 && (
        <AnalysisSection icon={Sparkles} title="创新点" color="purple">
          <ul className="space-y-1.5">
            {analysis.innovations.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm" style={{ color: 'var(--text)' }}>
                <span className="mt-1 shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold"
                  style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
                  {i + 1}
                </span>
                {item}
              </li>
            ))}
          </ul>
        </AnalysisSection>
      )}

      {analysis.method_summary && (
        <AnalysisSection icon={BookOpen} title="方法概述" color="blue">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>{analysis.method_summary}</p>
        </AnalysisSection>
      )}

      {analysis.experiments && (
        <AnalysisSection icon={FlaskConical} title="实验效果" color="green">
          {analysis.experiments.datasets?.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {analysis.experiments.datasets.map((d, i) => (
                <Badge key={i} color="green">{d}</Badge>
              ))}
            </div>
          )}
          {analysis.experiments.key_results?.length > 0 && (
            <ul className="space-y-1 mb-2">
              {analysis.experiments.key_results.map((r, i) => (
                <li key={i} className="text-sm flex items-start gap-1.5" style={{ color: 'var(--text)' }}>
                  <span style={{ color: 'var(--ok)' }}>✓</span> {r}
                </li>
              ))}
            </ul>
          )}
          {analysis.experiments.comparison && (
            <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{analysis.experiments.comparison}</p>
          )}
        </AnalysisSection>
      )}

      {analysis.limitations?.length > 0 && (
        <AnalysisSection icon={AlertTriangle} title="局限性" color="yellow">
          <ul className="space-y-1">
            {analysis.limitations.map((l, i) => (
              <li key={i} className="text-sm flex items-start gap-1.5" style={{ color: 'var(--text)' }}>
                <span style={{ color: 'var(--warn)' }}>⚠</span> {l}
              </li>
            ))}
          </ul>
        </AnalysisSection>
      )}

      {analysis.conclusion && (
        <AnalysisSection icon={Quote} title="结论与影响" color="blue">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>{analysis.conclusion}</p>
        </AnalysisSection>
      )}

      {analysis.reading_notes && (
        <div
          className="mt-4 p-3 rounded-lg text-xs"
          style={{ background: 'var(--bg-elevated)', color: 'var(--muted)' }}
        >
          <span className="font-medium" style={{ color: 'var(--text)' }}>阅读建议：</span>
          {analysis.reading_notes}
        </div>
      )}
    </div>
  )
}

function PaperDetail() {
  const { id: rulesetId, paperId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useTasks()
  const [analyzing, setAnalyzing] = useState(false)

  const { data: paper, isLoading, refetch } = useQuery({
    queryKey: ['paperDetail', rulesetId, paperId],
    queryFn: () => getPaperDetail(rulesetId, paperId),
    refetchInterval: analyzing ? 3000 : false,
  })

  useEffect(() => {
    if (analyzing && paper?.analyzed_at) {
      setAnalyzing(false)
    }
  }, [analyzing, paper?.analyzed_at])

  const statusMutation = useMutation({
    mutationFn: (status) => updatePaperStatus(rulesetId, paperId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paperDetail', rulesetId, paperId] })
      queryClient.invalidateQueries({ queryKey: ['rulesetPapers', rulesetId] })
    },
  })

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const data = await analyzePaper(rulesetId, paperId)
      if (data?.task_id) {
        addToast({ id: data.task_id, title: 'Analyzing paper...', taskId: data.task_id })
      }
    } catch {
      setAnalyzing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-48 rounded-lg" style={{ background: 'var(--bg-elevated)' }} />
          <div className="h-10 w-3/4 rounded-lg" style={{ background: 'var(--bg-elevated)' }} />
          <div className="h-40 rounded-xl" style={{ background: 'var(--bg-elevated)' }} />
        </div>
      </div>
    )
  }

  if (!paper) return null

  const arxivUrl = paper.arxiv_id?.startsWith('s2:')
    ? `https://www.semanticscholar.org/paper/${paper.arxiv_id.slice(3)}`
    : `https://arxiv.org/abs/${paper.arxiv_id}`
  const pdfUrl = paper.pdf_url || (paper.arxiv_id && !paper.arxiv_id.startsWith('s2:')
    ? `https://arxiv.org/pdf/${paper.arxiv_id}`
    : null)

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <button
        onClick={() => navigate(`/topics/${rulesetId}`)}
        className="flex items-center gap-1.5 text-sm mb-5 cursor-pointer"
        style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
      >
        <ArrowLeft size={16} />
        Back to topic
      </button>

      <div
        className="rounded-xl border p-6 mb-5"
        style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-start gap-4">
          <ScoreRing score={paper.llm_score} />
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-semibold leading-snug mb-2" style={{ color: 'var(--text-strong)' }}>
              {paper.title}
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-xs mb-3" style={{ color: 'var(--muted)' }}>
              {paper.year && (
                <span className="flex items-center gap-1">
                  <Calendar size={12} /> {paper.year}
                </span>
              )}
              {paper.venue && (
                <span className="flex items-center gap-1">
                  <Building2 size={12} /> {paper.venue}
                </span>
              )}
              <span>{paper.citation_count} citations</span>
              {paper.influential_citation_count > 0 && (
                <span>{paper.influential_citation_count} influential</span>
              )}
              <span>{(paper.impact_score || 0).toFixed(2)} impact</span>
               {paper.is_survey && <Badge color="yellow">Survey</Badge>}
               {paper.source === 'track' && <Badge color="green">New</Badge>}
            </div>
            {paper.authors?.length > 0 && (
              <div className="flex items-start gap-1.5 text-xs mb-3" style={{ color: 'var(--muted)' }}>
                <Users size={12} className="mt-0.5 shrink-0" />
                <span>{paper.authors.slice(0, 8).join(', ')}{paper.authors.length > 8 ? ` et al. (+${paper.authors.length - 8})` : ''}</span>
              </div>
            )}
            {paper.categories?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {paper.categories.map((c, i) => <Badge key={i} color="blue">{c}</Badge>)}
              </div>
            )}
            <div className="flex items-center gap-2 flex-wrap">
              <a
                href={arxivUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
                style={{ background: 'var(--accent)', color: 'var(--accent-foreground)', textDecoration: 'none' }}
              >
                <ExternalLink size={12} /> View on ArXiv
              </a>
              {pdfUrl && (
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
                  style={{ background: 'var(--bg-elevated)', color: 'var(--text)', border: '1px solid var(--border)', textDecoration: 'none' }}
                >
                  <BookOpen size={12} /> PDF
                </a>
              )}
              <div style={{ borderLeft: '1px solid var(--border)', height: 20 }} className="mx-1" />
              {paper.status !== 'favorited' && (
                <button
                  onClick={() => statusMutation.mutate('favorited')}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs cursor-pointer"
                  style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--muted)' }}
                >
                  <Star size={12} /> Favorite
                </button>
              )}
              {paper.status !== 'archived' && (
                <button
                  onClick={() => statusMutation.mutate('archived')}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs cursor-pointer"
                  style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--muted)' }}
                >
                  <Archive size={12} /> Archive
                </button>
              )}
              {paper.status !== 'inbox' && (
                <button
                  onClick={() => statusMutation.mutate('inbox')}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs cursor-pointer"
                  style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--muted)' }}
                >
                  <Inbox size={12} /> Inbox
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {paper.llm_reason && (
        <div
          className="rounded-xl border p-5 mb-5"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <h2 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-strong)' }}>
            Relevance Assessment
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>{paper.llm_reason}</p>
        </div>
      )}

      {paper.abstract && (
        <div
          className="rounded-xl border p-5 mb-5"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <h2 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-strong)' }}>Abstract</h2>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>{paper.abstract}</p>
        </div>
      )}

      <AnalysisPanel
        analysis={paper.analysis}
        analyzedAt={paper.analyzed_at}
        onReanalyze={handleAnalyze}
        isAnalyzing={analyzing}
      />
    </div>
  )
}

export default PaperDetail
