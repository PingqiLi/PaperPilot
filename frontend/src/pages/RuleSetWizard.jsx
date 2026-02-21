import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Save, ArrowLeft, Loader2, X, Plus } from 'lucide-react'
import { generateDraft, createRuleset, createRun } from '../api/rulesets'
import { useTasks } from '../contexts/TaskContext'
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
  const queryClient = useQueryClient()
  const { addToast } = useTasks()
  const [step, setStep] = useState('topic')
  const [topicSentence, setTopicSentence] = useState('')
  const [draft, setDraft] = useState(null)

  const draftMutation = useMutation({
    mutationFn: () => generateDraft(topicSentence),
    onSuccess: (data) => {
      setDraft(data)
      setStep('review')
    },
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const rs = await createRuleset(draft)
      const run = await createRun(rs.id, 'initialize')
      return { rs, run }
    },
    onSuccess: ({ rs, run }) => {
      queryClient.invalidateQueries({ queryKey: ['rulesets'] })
      addToast({ id: run.task_id || Date.now(), title: `Initializing "${rs.name}"...`, taskId: run.task_id })
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
        Back
      </button>

      <h1
        className="text-2xl font-semibold tracking-tight mb-2"
        style={{ color: 'var(--text-strong)' }}
      >
        New Topic
      </h1>
      <p className="text-sm mb-8" style={{ color: 'var(--muted)' }}>
        Describe your research interest and we'll auto-generate search parameters
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
            What are you researching?
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
            Be specific — this helps generate better search queries and scoring criteria
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
              {draftMutation.isPending ? 'Generating...' : 'Generate Draft'}
            </button>
          </div>
          {draftMutation.isPending && (
            <div className="mt-4">
              <LlmLoadingBanner
                message="Generating topic configuration..."
                detail="LLM is analyzing your research interest. This typically takes 1-2 minutes."
              />
            </div>
          )}
          {draftMutation.isError && (
            <div
              className="flex items-center gap-3 p-4 rounded-xl border mt-4"
              style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
            >
              <span className="text-sm" style={{ color: 'var(--danger)' }}>
                Failed to generate draft. {draftMutation.error?.response?.data?.detail || draftMutation.error?.message || 'Please try again.'}
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
              Name
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
              Topic
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
              ArXiv Categories
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
              Include Keywords
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
              Exclude Keywords
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
              Search Queries
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
              论文来源
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
              <option value="all">不限来源</option>
              <option value="arxiv">仅 ArXiv（推荐 CS/AI/ML）</option>
              <option value="open_access">开放获取（ArXiv + PMC）</option>
            </select>
            <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
              选择"仅 ArXiv"可确保所有论文都能直接阅读全文
            </p>
          </div>

          <div className="flex items-center gap-3 justify-end">
            <button
              onClick={() => setStep('topic')}
              className="px-4 py-2 rounded-lg text-sm cursor-pointer"
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                color: 'var(--text)',
              }}
            >
              Back
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
              {saveMutation.isPending ? 'Creating & Initializing...' : 'Create Topic'}
            </button>
          </div>
          {saveMutation.isPending && (
            <div className="mt-4">
              <LlmLoadingBanner
                message="Creating topic and starting initialization..."
                detail="Setting up your topic and launching the paper discovery pipeline."
              />
            </div>
          )}
          {saveMutation.isError && (
            <div
              className="flex items-center gap-3 p-4 rounded-xl border mt-2"
              style={{ background: 'var(--danger-subtle)', borderColor: 'var(--danger)' }}
            >
              <span className="text-sm" style={{ color: 'var(--danger)' }}>
                Failed to create topic. {saveMutation.error?.response?.data?.detail || saveMutation.error?.message || 'Please try again.'}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RuleSetWizard
