import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Save, ArrowLeft, Loader2, X, Plus, CheckCircle2 } from 'lucide-react'
import { generateDraft, createRuleset, createRun } from '../api/rulesets'
import { getTask } from '../api/tasks'
import { qk, invalidate } from '../api/queryKeys'
import { useTasks } from '../contexts/TaskContext'
import { useLanguage } from '../contexts/LanguageContext'
import LlmLoadingBanner from '../components/LlmLoadingBanner'

function TagInput({ tags, onChange, placeholder }) {
  const [input, setInput] = useState('')

  const addTag = () => {
    const val = input.trim()
    if (val && !tags.includes(val)) {
      onChange([...tags, val])
    }
    setInput('')
  }

  const removeTag = (idx) => {
    onChange(tags.filter((_, i) => i !== idx))
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map((tag, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs"
            style={{
              background: 'var(--accent-subtle)',
              color: 'var(--accent)',
            }}
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
          style={{
            background: 'var(--bg-elevated)',
            borderColor: 'var(--border)',
            color: 'var(--text)',
          }}
        />
        <button
          type="button"
          onClick={addTag}
          className="px-3 py-2 rounded-lg text-sm cursor-pointer"
          style={{
            background: 'var(--bg-hover)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
          }}
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  )
}

function RuleSetWizard() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { t } = useLanguage()
  const queryClient = useQueryClient()
  const { addToast } = useTasks()

  const reviewTaskId = searchParams.get('taskId') ? Number(searchParams.get('taskId')) : null
  const [step, setStep] = useState(reviewTaskId ? 'loading' : 'topic')
  const [topicSentence, setTopicSentence] = useState('')
  const [draft, setDraft] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  const { data: taskData } = useQuery({
    queryKey: qk.draftTask(reviewTaskId),
    queryFn: () => getTask(reviewTaskId),
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'running' ? 2000 : false
    },
    enabled: !!reviewTaskId,
  })

  useEffect(() => {
    if (!taskData || !reviewTaskId) return
    if (taskData.status === 'awaiting_approval' && taskData.result) {
      setDraft(taskData.result)
      setStep('review')
    } else if (taskData.status === 'running') {
      setStep('loading')
    } else if (taskData.status === 'failed') {
      if (taskData.result?.topic_sentence) {
        setTopicSentence(taskData.result.topic_sentence)
      }
      setStep('topic')
      setSearchParams({}, { replace: true })
    }
  }, [taskData, reviewTaskId, setSearchParams])

  const draftMutation = useMutation({
    mutationFn: () => generateDraft(topicSentence),
    onSuccess: (data) => {
      setSubmitted(true)
      setTopicSentence('')
      invalidate.tasksChanged(queryClient)
      addToast({ id: data.task_id, title: t('ruleSet.wizard.draftSubmitted') })
      setTimeout(() => setSubmitted(false), 3000)
    },
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const rs = await createRuleset(draft)
      const run = await createRun(rs.id, 'initialize', { taskId: draft.task_id })
      return { rs, run }
    },
    onSuccess: ({ rs }) => {
      setSearchParams({}, { replace: true })
      invalidate.topicCreated(queryClient)
      navigate(`/topics/${rs.id}`)
    },
  })

  const updateDraft = (field, value) => {
    setDraft(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-sm mb-6 cursor-pointer"
        style={{ background: 'none', border: 'none', color: 'var(--muted)' }}
      >
        <ArrowLeft size={16} />
        {t('ruleSet.wizard.back')}
      </button>

      <h1
        className="text-2xl font-semibold tracking-tight mb-2"
        style={{ color: 'var(--text-strong)' }}
      >
        {t('ruleSet.wizard.newTopic')}
      </h1>
      <p className="text-sm mb-8" style={{ color: 'var(--muted)' }}>
        {t('ruleSet.wizard.subtitle')}
      </p>

      {step === 'topic' && (
        <div
          className="p-6 rounded-xl border"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-strong)' }}
          >
            {t('ruleSet.wizard.whatResearch')}
          </label>
          <textarea
            value={topicSentence}
            onChange={e => setTopicSentence(e.target.value)}
            placeholder="e.g. I'm interested in efficient inference techniques for large language models, including quantization, pruning, speculative decoding, and KV-cache optimization."
            rows={4}
            className="w-full px-4 py-3 rounded-lg border text-sm resize-none"
            style={{
              background: 'var(--bg-elevated)',
              borderColor: 'var(--border)',
              color: 'var(--text)',
            }}
          />
          <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
            {t('ruleSet.wizard.topicTip')}
          </p>
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => draftMutation.mutate()}
              disabled={topicSentence.length < 10 || draftMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
              style={{
                background: 'var(--accent)',
                color: 'var(--accent-foreground)',
                border: 'none',
              }}
            >
              {draftMutation.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Sparkles size={16} />
              )}
              {draftMutation.isPending ? t('ruleSet.wizard.generating') : t('ruleSet.wizard.generateDraft')}
            </button>
          </div>
          {submitted && (
            <div
              className="flex items-center gap-2 p-3 rounded-lg mt-4"
              style={{ background: 'var(--ok-subtle)', color: 'var(--ok)' }}
            >
              <CheckCircle2 size={16} />
              <span className="text-sm">{t('ruleSet.wizard.draftSubmitted')}</span>
            </div>
          )}
          {draftMutation.isError && (
            <div
              className="flex items-center gap-3 p-4 rounded-xl border mt-4"
              style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
            >
              <span className="text-sm" style={{ color: 'var(--danger)' }}>
                {t('ruleSet.wizard.failedGenerate').replace('{error}', draftMutation.error?.response?.data?.detail || draftMutation.error?.message || 'Please try again.')}
              </span>
            </div>
          )}
        </div>
      )}

      {step === 'loading' && (
        <div
          className="p-6 rounded-xl border"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <LlmLoadingBanner
            message={t('ruleSet.wizard.loadingGenerateMsg')}
            detail={t('ruleSet.wizard.loadingGenerateDetail')}
            startedAt={taskData?.created_at}
          />
          {taskData?.status === 'failed' && (
            <div
              className="flex items-center gap-3 p-4 rounded-xl border mt-4"
              style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
            >
              <span className="text-sm" style={{ color: 'var(--danger)' }}>
                {t('ruleSet.wizard.failedGenerate').replace('{error}', taskData.error || '')}
              </span>
            </div>
          )}
        </div>
      )}

      {step === 'review' && draft && (
        <div className="flex flex-col gap-5">
          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.name')}
            </label>
            <input
              value={draft.name}
              onChange={e => updateDraft('name', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border text-sm"
              style={{
                background: 'var(--bg-elevated)',
                borderColor: 'var(--border)',
                color: 'var(--text)',
              }}
            />
          </div>

          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.topic')}
            </label>
            <textarea
              value={draft.topic_sentence}
              onChange={e => updateDraft('topic_sentence', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border text-sm resize-none"
              style={{
                background: 'var(--bg-elevated)',
                borderColor: 'var(--border)',
                color: 'var(--text)',
              }}
            />
          </div>

          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.arxivCategories')}
            </label>
            <TagInput
              tags={draft.categories || []}
              onChange={val => updateDraft('categories', val)}
              placeholder="e.g. cs.CL"
            />
          </div>

          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.includeKeywords')}
            </label>
            <TagInput
              tags={draft.keywords_include || []}
              onChange={val => updateDraft('keywords_include', val)}
              placeholder="Add keyword"
            />
          </div>

          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.excludeKeywords')}
            </label>
            <TagInput
              tags={draft.keywords_exclude || []}
              onChange={val => updateDraft('keywords_exclude', val)}
              placeholder="Add keyword to exclude"
            />
          </div>

          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.searchQueries')}
            </label>
            <TagInput
              tags={draft.search_queries || []}
              onChange={val => updateDraft('search_queries', val)}
              placeholder="Add search query"
            />
          </div>

          <div
            className="p-6 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-strong)' }}
            >
              {t('ruleSet.wizard.source')}
            </label>
            <select
              value={draft.source_filter || 'all'}
              onChange={e => updateDraft('source_filter', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border text-sm"
              style={{
                background: 'var(--bg-elevated)',
                borderColor: 'var(--border)',
                color: 'var(--text)',
              }}
            >
              <option value="all">{t('ruleSet.wizard.sourceAll')}</option>
              <option value="arxiv">{t('ruleSet.wizard.sourceArxiv')}</option>
              <option value="open_access">{t('ruleSet.wizard.sourceOpenAccess')}</option>
            </select>
            <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
              {t('ruleSet.wizard.sourceTip')}
            </p>
          </div>

          <div className="flex items-center gap-3 justify-end">
            <button
              onClick={() => { setStep('topic'); setDraft(null); setSearchParams({}, { replace: true }) }}
              className="px-4 py-2 rounded-lg text-sm cursor-pointer"
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                color: 'var(--text)',
              }}
            >
              {t('ruleSet.wizard.back')}
            </button>
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-50"
              style={{
                background: 'var(--accent)',
                color: 'var(--accent-foreground)',
                border: 'none',
              }}
            >
              {saveMutation.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Save size={16} />
              )}
              {saveMutation.isPending ? t('ruleSet.wizard.creating') : t('ruleSet.wizard.createTopic')}
            </button>
          </div>
          {saveMutation.isPending && (
            <div className="mt-4">
              <LlmLoadingBanner
                message={t('ruleSet.wizard.loadingCreateMsg')}
                detail={t('ruleSet.wizard.loadingCreateDetail')}
              />
            </div>
          )}
          {saveMutation.isError && (
            <div
              className="flex items-center gap-3 p-4 rounded-xl border mt-2"
              style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
            >
              <span className="text-sm" style={{ color: 'var(--danger)' }}>
                {t('ruleSet.wizard.failedCreate').replace('{error}', saveMutation.error?.response?.data?.detail || saveMutation.error?.message || 'Please try again.')}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RuleSetWizard
