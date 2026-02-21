import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { DollarSign, Zap, ChevronLeft, ChevronRight } from 'lucide-react'
import { getCostStats, getDailyCosts, getRequestHistory } from '../api/stats'

const TIME_RANGES = [
  { label: '1d', days: 1 },
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
]

const CHART_MODES = [
  { label: 'Cost', key: 'cost' },
  { label: 'Tokens', key: 'tokens' },
]

const MODEL_COLORS = [
  '#6366f1',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
  '#06b6d4',
  '#a855f7',
  '#ec4899',
  '#14b8a6',
]

function PillToggle({ options, value, onChange }) {
  return (
    <div
      className="inline-flex rounded-lg p-0.5"
      style={{ background: 'var(--bg-muted)' }}
    >
      {options.map(opt => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className="px-3 py-1 text-xs font-medium rounded-md transition-all"
            style={{
              background: active ? 'var(--accent)' : 'transparent',
              color: active ? 'var(--accent-foreground)' : 'var(--muted)',
              cursor: 'pointer',
              border: 'none',
            }}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

function CustomTooltip({ active, payload, label, chartMode }) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      <p className="font-medium mb-1.5" style={{ color: 'var(--text-strong)' }}>
        {label}
      </p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: entry.color }}
          />
          <span style={{ color: 'var(--muted)' }}>{entry.name}:</span>
          <span style={{ color: 'var(--text-strong)' }}>
            {chartMode === 'cost'
              ? `¥${entry.value.toFixed(4)}`
              : entry.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

function aggregateChartData(rawData, mode) {
  const byDate = {}
  const modelSet = new Set()

  for (const row of rawData || []) {
    if (!byDate[row.date]) byDate[row.date] = { date: row.date }
    modelSet.add(row.model)
    byDate[row.date][row.model] = (byDate[row.date][row.model] || 0) + row[mode]
  }

  const models = [...modelSet]
  const chartData = Object.values(byDate).sort((a, b) =>
    a.date.localeCompare(b.date)
  )

  return { chartData, models }
}

function CostStats() {
  const [days, setDays] = useState(7)
  const [chartMode, setChartMode] = useState('cost')
  const [reqPage, setReqPage] = useState(1)
  const pageSize = 20

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['costStats'],
    queryFn: getCostStats,
  })

  const { data: dailyRaw, isLoading: dailyLoading } = useQuery({
    queryKey: ['dailyCosts', days],
    queryFn: () => getDailyCosts(days),
  })

  const { data: reqData, isLoading: reqLoading } = useQuery({
    queryKey: ['requestHistory', days, reqPage],
    queryFn: () => getRequestHistory({ page: reqPage, page_size: pageSize, days }),
  })

  const { chartData, models } = aggregateChartData(dailyRaw, chartMode)
  const totalPages = reqData ? Math.ceil(reqData.total / pageSize) : 0

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight mb-1"
          style={{ color: 'var(--text-strong)' }}
        >
          Cost Stats
        </h1>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          LLM API usage and cost tracking (CNY)
        </p>
      </div>

      {/* Summary cards */}
      {summaryLoading ? (
        <div className="flex gap-4 mb-6">
          {[1, 2].map(i => (
            <div
              key={i}
              className="h-16 flex-1 rounded-xl animate-pulse"
              style={{ background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      ) : (
        <div className="flex gap-4 mb-6">
          <div
            className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <div
              className="p-2 rounded-lg"
              style={{ background: 'var(--accent-subtle)' }}
            >
              <DollarSign size={16} style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>
                Total Cost
              </p>
              <p className="text-lg font-semibold" style={{ color: 'var(--text-strong)' }}>
                ¥{(summary?.total_cost || 0).toFixed(4)}
              </p>
            </div>
          </div>
          <div
            className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <div
              className="p-2 rounded-lg"
              style={{ background: 'var(--accent-subtle)' }}
            >
              <Zap size={16} style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>
                Total Tokens
              </p>
              <p className="text-lg font-semibold" style={{ color: 'var(--text-strong)' }}>
                {(summary?.total_tokens || 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Monthly budget */}
      {summary && summary.monthly_budget > 0 && (
        <div
          className="rounded-xl border p-4 mb-6"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium" style={{ color: 'var(--text-strong)' }}>
              Monthly Budget
            </span>
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              ¥{summary.monthly_cost.toFixed(2)} / ¥{summary.monthly_budget.toFixed(0)}
              <span className="ml-2" style={{
                color: summary.budget_usage_pct >= 90 ? 'var(--danger, #ef4444)' :
                       summary.budget_usage_pct >= 70 ? '#f59e0b' : 'var(--accent)'
              }}>
                ({summary.budget_usage_pct}%)
              </span>
            </span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-elevated)' }}>
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(summary.budget_usage_pct, 100)}%`,
                background: summary.budget_usage_pct >= 90 ? 'var(--danger, #ef4444)' :
                           summary.budget_usage_pct >= 70 ? '#f59e0b' : 'var(--accent)',
              }}
            />
          </div>
        </div>
      )}

      {/* Chart section */}
      <div
        className="rounded-xl border p-5 mb-6"
        style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
            Daily Usage
          </h2>
          <div className="flex items-center gap-3">
            <PillToggle
              options={CHART_MODES.map(m => ({ label: m.label, value: m.key }))}
              value={chartMode}
              onChange={setChartMode}
            />
            <PillToggle
              options={TIME_RANGES.map(r => ({ label: r.label, value: r.days }))}
              value={days}
              onChange={v => { setDays(v); setReqPage(1) }}
            />
          </div>
        </div>

        {dailyLoading ? (
          <div
            className="h-64 rounded-lg animate-pulse"
            style={{ background: 'var(--bg-elevated)' }}
          />
        ) : chartData.length === 0 ? (
          <div
            className="h-64 flex items-center justify-center rounded-lg"
            style={{ background: 'var(--bg-elevated)' }}
          >
            <p className="text-sm" style={{ color: 'var(--muted)' }}>
              No usage data yet
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                {models.map((model, i) => (
                  <linearGradient
                    key={model}
                    id={`grad-${i}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor={MODEL_COLORS[i % MODEL_COLORS.length]}
                      stopOpacity={0.3}
                    />
                    <stop
                      offset="100%"
                      stopColor={MODEL_COLORS[i % MODEL_COLORS.length]}
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border)"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: 'var(--muted)' }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
                tickFormatter={v => {
                  const parts = v.split('-')
                  return `${parts[1]}/${parts[2]}`
                }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'var(--muted)' }}
                axisLine={false}
                tickLine={false}
                width={50}
                tickFormatter={v =>
                  chartMode === 'cost'
                    ? `¥${v}`
                    : v >= 1000
                      ? `${(v / 1000).toFixed(0)}k`
                      : v
                }
              />
              <Tooltip content={<CustomTooltip chartMode={chartMode} />} />
              {models.map((model, i) => (
                <Area
                  key={model}
                  type="monotone"
                  dataKey={model}
                  name={model}
                  stackId="1"
                  stroke={MODEL_COLORS[i % MODEL_COLORS.length]}
                  strokeWidth={2}
                  fill={`url(#grad-${i})`}
                  dot={false}
                  activeDot={{ r: 3, strokeWidth: 0 }}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Request history table */}
      <div
        className="rounded-xl border overflow-hidden"
        style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <h2 className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
            Request History
          </h2>
          {reqData && (
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              {reqData.total} requests
            </span>
          )}
        </div>

        {reqLoading ? (
          <div className="p-5 space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div
                key={i}
                className="h-10 rounded-lg animate-pulse"
                style={{ background: 'var(--bg-elevated)' }}
              />
            ))}
          </div>
        ) : !reqData?.items?.length ? (
          <div className="py-12 text-center">
            <p className="text-sm" style={{ color: 'var(--muted)' }}>
              No requests yet
            </p>
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Date', 'Workflow', 'Model', 'Tokens', 'Cost'].map(col => (
                    <th
                      key={col}
                      className="text-left px-5 py-2.5 text-xs font-medium"
                      style={{ color: 'var(--muted)', background: 'var(--bg-elevated)' }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reqData.items.map(item => (
                  <tr
                    key={item.id}
                    className="transition-colors"
                    style={{ borderBottom: '1px solid var(--border)' }}
                    onMouseEnter={e =>
                      (e.currentTarget.style.background = 'var(--bg-hover)')
                    }
                    onMouseLeave={e =>
                      (e.currentTarget.style.background = 'transparent')
                    }
                  >
                    <td className="px-5 py-2.5" style={{ color: 'var(--text)' }}>
                      {item.timestamp
                        ? new Date(item.timestamp).toLocaleString('sv-SE', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : '—'}
                    </td>
                    <td className="px-5 py-2.5">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-xs"
                        style={{
                          background: 'var(--accent-subtle)',
                          color: 'var(--accent)',
                        }}
                      >
                        {item.workflow}
                      </span>
                    </td>
                    <td
                      className="px-5 py-2.5 font-mono text-xs"
                      style={{ color: 'var(--text)' }}
                    >
                      {item.model}
                    </td>
                    <td className="px-5 py-2.5" style={{ color: 'var(--text)' }}>
                      {item.tokens.toLocaleString()}
                    </td>
                    <td
                      className="px-5 py-2.5 font-mono"
                      style={{ color: 'var(--text-strong)' }}
                    >
                      ¥{item.cost.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div
                className="flex items-center justify-between px-5 py-3 border-t"
                style={{ borderColor: 'var(--border)' }}
              >
                <span className="text-xs" style={{ color: 'var(--muted)' }}>
                  Page {reqPage} of {totalPages}
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setReqPage(p => Math.max(1, p - 1))}
                    disabled={reqPage <= 1}
                    className="p-1.5 rounded-md transition-colors"
                    style={{
                      background: 'var(--bg-muted)',
                      color: reqPage <= 1 ? 'var(--muted-strong)' : 'var(--text)',
                      border: 'none',
                      cursor: reqPage <= 1 ? 'not-allowed' : 'pointer',
                      opacity: reqPage <= 1 ? 0.5 : 1,
                    }}
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    onClick={() => setReqPage(p => Math.min(totalPages, p + 1))}
                    disabled={reqPage >= totalPages}
                    className="p-1.5 rounded-md transition-colors"
                    style={{
                      background: 'var(--bg-muted)',
                      color: reqPage >= totalPages ? 'var(--muted-strong)' : 'var(--text)',
                      border: 'none',
                      cursor: reqPage >= totalPages ? 'not-allowed' : 'pointer',
                      opacity: reqPage >= totalPages ? 0.5 : 1,
                    }}
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default CostStats
