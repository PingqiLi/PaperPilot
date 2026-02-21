import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, BookOpen, Clock, Zap } from 'lucide-react'
import { getRulesets } from '../api/rulesets'

function RuleSetList() {
  const { data: rulesets, isLoading } = useQuery({
    queryKey: ['rulesets'],
    queryFn: getRulesets,
  })

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse flex flex-col gap-4">
          {[1, 2, 3].map(i => (
            <div
              key={i}
              className="h-24 rounded-xl"
              style={{ background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1
            className="text-2xl font-semibold tracking-tight"
            style={{ color: 'var(--text-strong)' }}
          >
            Rule Sets
          </h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--muted)' }}>
            Manage your paper discovery topics
          </p>
        </div>
        <Link
          to="/rulesets/new"
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium no-underline transition-colors"
          style={{
            background: 'var(--accent)',
            color: 'var(--accent-foreground)',
          }}
        >
          <Plus size={16} />
          New Rule Set
        </Link>
      </div>

      {(!rulesets || rulesets.length === 0) ? (
        <div
          className="text-center py-16 rounded-xl border"
          style={{
            background: 'var(--card)',
            borderColor: 'var(--border)',
          }}
        >
          <BookOpen size={48} className="mx-auto mb-4" style={{ color: 'var(--muted)' }} />
          <p className="text-lg font-medium mb-2" style={{ color: 'var(--text-strong)' }}>
            No rule sets yet
          </p>
          <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>
            Create your first rule set to start discovering papers
          </p>
          <Link
            to="/rulesets/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium no-underline"
            style={{
              background: 'var(--accent)',
              color: 'var(--accent-foreground)',
            }}
          >
            <Plus size={16} />
            Create Rule Set
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {rulesets.map(rs => (
            <Link
              key={rs.id}
              to={`/rulesets/${rs.id}`}
              className="block p-5 rounded-xl border transition-all no-underline"
              style={{
                background: 'var(--card)',
                borderColor: 'var(--border)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--border-strong)'
                e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3
                    className="text-base font-medium"
                    style={{ color: 'var(--text-strong)' }}
                  >
                    {rs.name}
                  </h3>
                  <p className="text-sm mt-1 line-clamp-2" style={{ color: 'var(--muted)' }}>
                    {rs.topic_sentence}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                  {rs.is_initialized && (
                    <span
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{
                        background: 'var(--ok-subtle)',
                        color: 'var(--ok)',
                      }}
                    >
                      Initialized
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 mt-3 text-xs" style={{ color: 'var(--muted)' }}>
                <span className="flex items-center gap-1">
                  <Zap size={12} />
                  {rs.search_queries?.length || 0} queries
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {new Date(rs.created_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default RuleSetList
