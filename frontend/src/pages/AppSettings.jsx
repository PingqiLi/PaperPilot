import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Key, Mail, Sliders, Clock, Check, AlertCircle, ChevronDown, ChevronRight, Bot, GraduationCap, Send, Loader2, History, XCircle, CheckCircle2, FlaskConical, Globe } from 'lucide-react'
import { getSettings, updateSettings, getEmailLogs, sendTestEmail } from '../api/settings'
import { useLanguage } from '../contexts/LanguageContext'

const SECTIONS = [
  { key: 'api', labelKey: 'settings.api', icon: Key },
  { key: 'email', labelKey: 'settings.email', icon: Mail },
  { key: 'pipeline', labelKey: 'settings.pipeline', icon: Sliders },
  { key: 'language', labelKey: 'settings.language', icon: Globe },
  { key: 'schedule', labelKey: 'settings.schedule', icon: Clock },
]

const LANGUAGES = [
  { value: '中文', label: '中文' },
  { value: 'English', label: 'English' },
  { value: '日本語', label: '日本語' },
  { value: '한국어', label: '한국어' },
  { value: 'Français', label: 'Français' },
  { value: 'Español', label: 'Español' },
]

const inputStyle = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  color: 'var(--text-strong)',
  borderRadius: '8px',
  padding: '8px 12px',
  fontSize: '13px',
  width: '100%',
  outline: 'none',
}

const selectStyle = {
  ...inputStyle,
  appearance: 'none',
  WebkitAppearance: 'none',
  cursor: 'pointer',
  paddingRight: '32px',
}

const SYSTEM_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone

const KNOWN_TIMEZONES = [
  'Asia/Shanghai', 'Asia/Tokyo', 'Asia/Kolkata', 'Asia/Singapore',
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'Europe/London', 'Europe/Berlin', 'Europe/Paris',
  'Australia/Sydney', 'Pacific/Auckland', 'UTC',
]

const TIMEZONES = [...new Set([...KNOWN_TIMEZONES, ...(KNOWN_TIMEZONES.includes(SYSTEM_TZ) ? [] : [SYSTEM_TZ])])]
  .map(tz => ({ value: tz, label: tz }))

const WEEKDAYS = [
  { value: 0, labelKey: 'settings.schedule.sunday' },
  { value: 1, labelKey: 'settings.schedule.monday' },
  { value: 2, labelKey: 'settings.schedule.tuesday' },
  { value: 3, labelKey: 'settings.schedule.wednesday' },
  { value: 4, labelKey: 'settings.schedule.thursday' },
  { value: 5, labelKey: 'settings.schedule.friday' },
  { value: 6, labelKey: 'settings.schedule.saturday' },
]

function parseCron(expr) {
  const parts = (expr || '').trim().split(/\s+/)
  if (parts.length !== 5) return { minute: 0, hour: 8, dayOfMonth: null, dayOfWeek: null }
  return {
    minute: parts[0] !== '*' ? parseInt(parts[0], 10) : 0,
    hour: parts[1] !== '*' ? parseInt(parts[1], 10) : 0,
    dayOfMonth: parts[2] !== '*' ? parseInt(parts[2], 10) : null,
    dayOfWeek: parts[4] !== '*' ? parseInt(parts[4], 10) : null,
  }
}

function buildCron({ minute, hour, dayOfMonth, dayOfWeek }) {
  const m = minute ?? 0
  const h = hour ?? 0
  const dom = dayOfMonth != null ? dayOfMonth : '*'
  const dow = dayOfWeek != null ? dayOfWeek : '*'
  return `${m} ${h} ${dom} * ${dow}`
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

function SelectWrap({ value, onChange, children, style: extraStyle }) {
  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{ ...selectStyle, ...extraStyle }}
        onFocus={e => e.target.style.boxShadow = '0 0 0 2px var(--accent-subtle)'}
        onBlur={e => e.target.style.boxShadow = 'none'}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        style={{
          position: 'absolute',
          right: 10,
          top: '50%',
          transform: 'translateY(-50%)',
          pointerEvents: 'none',
          color: 'var(--muted)',
        }}
      />
    </div>
  )
}

const API_PROVIDERS = [
  {
    id: 'llm',
    nameKey: 'settings.api.llmProvider',
    descKey: 'settings.api.llmProviderDesc',
    icon: Bot,
    keyField: 'llm_api_key',
    fields: ['llm_api_key', 'llm_base_url', 'llm_model', 'llm_price_input', 'llm_price_output'],
  },
  {
    id: 's2',
    nameKey: 'settings.api.s2',
    descKey: 'settings.api.s2Desc',
    icon: GraduationCap,
    keyField: 's2_api_key',
    fields: ['s2_api_key'],
  },
]

function ApiProviderEditor({ fields, changes, handleChange }) {
  const { t } = useLanguage()
  const [expanded, setExpanded] = useState(null)

  const getVal = (key) => key in changes ? changes[key] : (fields[key]?.value ?? '')
  const isConfigured = (keyField) => {
    const val = getVal(keyField)
    return val && val !== '' && !val.match(/^\*+$/)
  }

  return (
    <div className="space-y-2">
      {API_PROVIDERS.map(provider => {
        const open = expanded === provider.id
        const configured = isConfigured(provider.keyField)
        const Icon = provider.icon
        const maskedKey = fields[provider.keyField]?.value || ''

        return (
          <div
            key={provider.id}
            className="rounded-lg border overflow-hidden"
            style={{
              borderColor: open ? 'var(--accent)' : 'var(--border)',
              background: 'var(--bg-elevated)',
              transition: 'border-color 0.15s',
            }}
          >
            <button
              type="button"
              onClick={() => setExpanded(open ? null : provider.id)}
              className="w-full flex items-center gap-3 p-4 cursor-pointer"
              style={{ background: 'transparent', border: 'none', textAlign: 'left' }}
            >
              <div
                className="flex items-center justify-center rounded-lg shrink-0"
                style={{
                  width: 36, height: 36,
                  background: configured ? 'var(--accent-subtle)' : 'var(--bg-muted)',
                }}
              >
                <Icon size={18} style={{ color: configured ? 'var(--accent)' : 'var(--muted)' }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
                    {t(provider.nameKey)}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                    style={{
                      background: configured ? 'var(--ok-subtle)' : 'var(--bg-muted)',
                      color: configured ? 'var(--ok)' : 'var(--muted)',
                    }}
                  >
                    {configured ? t('settings.configured') : t('settings.notSet')}
                  </span>
                </div>
                <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--muted)' }}>
                  {maskedKey && !maskedKey.match(/^\*+$/)
                    ? maskedKey
                    : t(provider.descKey)}
                </div>
              </div>
              {open
                ? <ChevronDown size={16} style={{ color: 'var(--muted)', shrink: 0 }} />
                : <ChevronRight size={16} style={{ color: 'var(--muted)', shrink: 0 }} />
              }
            </button>

            {open && (
              <div
                className="px-4 pb-4 pt-1 grid grid-cols-1 md:grid-cols-2 gap-3"
                style={{ borderTop: '1px solid var(--border)' }}
              >
                {provider.fields.map(fieldKey => {
                  const meta = fields[fieldKey]
                  if (!meta) return null
                  return (
                    <FieldInput
                      key={fieldKey}
                      fieldKey={fieldKey}
                      meta={meta}
                      value={fieldKey in changes ? changes[fieldKey] : (meta.secret ? undefined : meta.value)}
                      onChange={handleChange}
                    />
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function CronTimePicker({ cronValue, onChange, minutePresets }) {
  const parsed = parseCron(cronValue)
  const presets = minutePresets || [0, 15, 30, 45]
  const minuteOptions = presets.includes(parsed.minute) ? presets : [...presets, parsed.minute].sort((a, b) => a - b)

  const update = (field, val) => {
    const next = { ...parsed, [field]: parseInt(val, 10) }
    onChange(buildCron(next))
  }

  return (
    <div className="flex items-center gap-1.5">
      <SelectWrap value={parsed.hour} onChange={v => update('hour', v)} style={{ width: 72 }}>
        {Array.from({ length: 24 }, (_, i) => (
          <option key={i} value={i}>{pad2(i)}</option>
        ))}
      </SelectWrap>
      <span style={{ color: 'var(--text-strong)', fontWeight: 600, fontSize: 14 }}>:</span>
      <SelectWrap value={parsed.minute} onChange={v => update('minute', v)} style={{ width: 72 }}>
        {minuteOptions.map(m => (
          <option key={m} value={m}>{pad2(m)}</option>
        ))}
      </SelectWrap>
    </div>
  )
}

function ScheduleEditor({ fields, changes, handleChange }) {
  const { t } = useLanguage()
  const getVal = (key) => key in changes ? changes[key] : (fields[key]?.value ?? '')

  const monitorCron = getVal('schedule_track_cron')
  const weeklyCron = getVal('schedule_weekly_cron')
  const monthlyCron = getVal('schedule_monthly_cron')
  const timezone = getVal('schedule_timezone')
  const enabled = getVal('schedule_enabled')

  const weeklyParsed = parseCron(weeklyCron)
  const monthlyParsed = parseCron(monthlyCron)

  const trackParsed = parseCron(monitorCron)
  const isTrackWeekly = trackParsed.dayOfWeek != null

  const scheduleRows = [
    {
      key: 'schedule_track_cron',
      title: t('settings.schedule.trackTitle'),
      desc: t('settings.schedule.trackDesc'),
      render: () => (
        <div className="flex items-center gap-2 flex-wrap">
          <SelectWrap
            value={isTrackWeekly ? 'weekly' : 'daily'}
            onChange={v => {
              const cur = parseCron(monitorCron)
              if (v === 'weekly') {
                handleChange('schedule_track_cron', buildCron({ ...cur, dayOfWeek: 0 }))
              } else {
                handleChange('schedule_track_cron', buildCron({ minute: cur.minute, hour: cur.hour, dayOfMonth: null, dayOfWeek: null }))
              }
            }}
            style={{ width: 110 }}
          >
              <option value="daily">{t('settings.schedule.daily')}</option>
              <option value="weekly">{t('settings.schedule.weekly')}</option>
          </SelectWrap>
          {isTrackWeekly && (
            <SelectWrap
              value={trackParsed.dayOfWeek ?? 0}
              onChange={v => {
                const next = { ...trackParsed, dayOfWeek: parseInt(v, 10) }
                handleChange('schedule_track_cron', buildCron(next))
              }}
              style={{ width: 130 }}
            >
              {WEEKDAYS.map(d => (
                <option key={d.value} value={d.value}>{t(d.labelKey)}</option>
              ))}
            </SelectWrap>
          )}
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.schedule.at')}</span>
          <CronTimePicker
            cronValue={monitorCron}
            onChange={v => {
              const tp = parseCron(v)
              if (isTrackWeekly) {
                handleChange('schedule_track_cron', buildCron({ ...tp, dayOfWeek: trackParsed.dayOfWeek ?? 0 }))
              } else {
                handleChange('schedule_track_cron', buildCron(tp))
              }
            }}
          />
        </div>
      ),
    },
    {
      key: 'schedule_weekly_cron',
      title: t('settings.schedule.weeklyTitle'),
      desc: t('settings.schedule.weeklyDesc'),
      render: () => (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.schedule.every')}</span>
          <SelectWrap
            value={weeklyParsed.dayOfWeek ?? 1}
            onChange={v => {
              const next = { ...weeklyParsed, dayOfWeek: parseInt(v, 10) }
              handleChange('schedule_weekly_cron', buildCron(next))
            }}
            style={{ width: 130 }}
          >
            {WEEKDAYS.map(d => (
              <option key={d.value} value={d.value}>{t(d.labelKey)}</option>
            ))}
          </SelectWrap>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.schedule.at')}</span>
          <CronTimePicker
            cronValue={weeklyCron}
            onChange={v => {
              const tp = parseCron(v)
              handleChange('schedule_weekly_cron', buildCron({ ...tp, dayOfWeek: weeklyParsed.dayOfWeek ?? 1 }))
            }}
          />
        </div>
      ),
    },
    {
      key: 'schedule_monthly_cron',
      title: t('settings.schedule.monthlyTitle'),
      desc: t('settings.schedule.monthlyDesc'),
      render: () => (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.schedule.onDay')}</span>
          <SelectWrap
            value={monthlyParsed.dayOfMonth ?? 1}
            onChange={v => {
              const next = { ...monthlyParsed, dayOfMonth: parseInt(v, 10) }
              handleChange('schedule_monthly_cron', buildCron(next))
            }}
            style={{ width: 72 }}
          >
            {Array.from({ length: 28 }, (_, i) => (
              <option key={i + 1} value={i + 1}>{i + 1}</option>
            ))}
          </SelectWrap>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.schedule.ofEachMonthAt')}</span>
          <CronTimePicker
            cronValue={monthlyCron}
            onChange={v => {
              const timeParsed = parseCron(v)
              const next = { ...timeParsed, dayOfMonth: monthlyParsed.dayOfMonth ?? 1 }
              handleChange('schedule_monthly_cron', buildCron(next))
            }}
          />
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium block mb-1" style={{ color: 'var(--muted)' }}>
            {t('settings.schedule.timezone')}
          </label>
            <SelectWrap
              value={timezone === SYSTEM_TZ ? '__system__' : (timezone || '__system__')}
              onChange={v => handleChange('schedule_timezone', v === '__system__' ? SYSTEM_TZ : v)}
              style={{ width: '100%' }}
            >
              <option value="__system__">{t('settings.schedule.system').replace('{tz}', SYSTEM_TZ)}</option>
              {TIMEZONES.map(tz => (
                <option key={tz.value} value={tz.value}>{tz.label}</option>
              ))}
            </SelectWrap>
        </div>
        <div>
          <label className="text-xs font-medium block mb-1" style={{ color: 'var(--muted)' }}>
            {t('settings.schedule.enable')}
          </label>
          <Toggle
            checked={enabled === true || enabled === 'true'}
            onChange={v => handleChange('schedule_enabled', v)}
          />
        </div>
      </div>

      {scheduleRows.map(row => (
        <div
          key={row.key}
          className="rounded-lg border p-4"
          style={{
            background: 'var(--bg-elevated)',
            borderColor: 'var(--border)',
          }}
        >
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0">
              <div className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
                {row.title}
              </div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                {row.desc}
              </div>
            </div>
            <div className="shrink-0">
              {row.render()}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="relative inline-flex items-center rounded-full transition-colors cursor-pointer"
      style={{
        width: 40,
        height: 22,
        background: checked ? 'var(--accent)' : 'var(--bg-muted)',
        border: 'none',
        padding: 0,
      }}
    >
      <span
        className="block rounded-full transition-transform"
        style={{
          width: 18,
          height: 18,
          background: '#fff',
          transform: checked ? 'translateX(20px)' : 'translateX(2px)',
        }}
      />
    </button>
  )
}

function FieldInput({ fieldKey, meta, value, onChange }) {
  const isSecret = meta.secret
  const isInt = meta.type === 'int'
  const isFloat = meta.type === 'float'
  const isBool = meta.type === 'bool'

  if (isBool) {
    return (
      <div>
        <label className="text-xs font-medium block mb-1" style={{ color: 'var(--muted)' }}>
          {meta.label}
        </label>
        <Toggle checked={value === true || value === 'true'} onChange={v => onChange(fieldKey, v)} />
        {meta.desc && (
          <p className="text-[11px] mt-1" style={{ color: 'var(--muted)', opacity: 0.7 }}>{meta.desc}</p>
        )}
      </div>
    )
  }

  return (
    <div>
      <label className="text-xs font-medium block mb-1" style={{ color: 'var(--muted)' }}>
        {meta.label}
      </label>
      <input
        type={isSecret ? 'password' : (isInt || isFloat) ? 'number' : 'text'}
        step={isFloat ? '0.1' : undefined}
        placeholder={isSecret ? meta.value : ''}
        value={isSecret ? (value ?? '') : (value ?? meta.value ?? '')}
        onChange={e => {
          let v = e.target.value
          if (isInt) v = v === '' ? '' : parseInt(v, 10)
          else if (isFloat) v = v === '' ? '' : parseFloat(v)
          onChange(fieldKey, v)
        }}
        style={inputStyle}
        onFocus={e => e.target.style.boxShadow = '0 0 0 2px var(--accent-subtle)'}
        onBlur={e => e.target.style.boxShadow = 'none'}
      />
      {meta.desc && (
        <p className="text-[11px] mt-1" style={{ color: 'var(--muted)', opacity: 0.7 }}>{meta.desc}</p>
      )}
    </div>
  )
}

function LanguageSection({ fields, changes, handleChange }) {
  const { lang, setLang, t } = useLanguage()
  const getVal = (key) => key in changes ? changes[key] : (fields[key]?.value ?? '')
  const langVal = getVal('output_language')
  const isCustomLang = langVal && !LANGUAGES.some(l => l.value === langVal)
  const [showCustomLang, setShowCustomLang] = useState(isCustomLang)

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium block mb-1" style={{ color: 'var(--muted)' }}>
          {t('settings.language.ui')}
        </label>
        <div className="inline-flex rounded-lg p-0.5" style={{ background: 'var(--bg-muted)' }}>
          <button
            type="button"
            onClick={() => setLang('zh')}
            className="px-3 py-1 text-xs font-medium rounded-md transition-all cursor-pointer"
            style={{
              background: lang === 'zh' ? 'var(--accent)' : 'transparent',
              color: lang === 'zh' ? 'var(--accent-foreground)' : 'var(--muted)',
              border: 'none',
            }}
          >
            {t('settings.language.uiZh')}
          </button>
          <button
            type="button"
            onClick={() => setLang('en')}
            className="px-3 py-1 text-xs font-medium rounded-md transition-all cursor-pointer"
            style={{
              background: lang === 'en' ? 'var(--accent)' : 'transparent',
              color: lang === 'en' ? 'var(--accent-foreground)' : 'var(--muted)',
              border: 'none',
            }}
          >
            {t('settings.language.uiEn')}
          </button>
        </div>
      </div>

      <div>
        <label className="text-xs font-medium block mb-1" style={{ color: 'var(--muted)' }}>
          {t('settings.language.output')}
        </label>
        <div className="flex items-center gap-2">
          <SelectWrap
            value={showCustomLang ? '__custom__' : (langVal || '中文')}
            onChange={v => {
              if (v === '__custom__') {
                setShowCustomLang(true)
                handleChange('output_language', '')
              } else {
                setShowCustomLang(false)
                handleChange('output_language', v)
              }
            }}
            style={{ width: 160 }}
          >
            {LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
            <option value="__custom__">{t('settings.language.custom')}</option>
          </SelectWrap>
          {showCustomLang && (
            <input
              type="text"
              value={langVal}
              onChange={e => handleChange('output_language', e.target.value)}
              placeholder="e.g. Deutsch, Português"
              style={{ ...inputStyle, width: 200 }}
              onFocus={e => e.target.style.boxShadow = '0 0 0 2px var(--accent-subtle)'}
              onBlur={e => e.target.style.boxShadow = 'none'}
            />
          )}
        </div>
        <p className="text-[11px] mt-1" style={{ color: 'var(--muted)', opacity: 0.7 }}>
          {t('settings.language.outputDesc')}
        </p>
      </div>

      <div
        className="rounded-lg p-3"
        style={{ background: 'var(--bg-muted)', border: '1px solid var(--border)' }}
      >
        <p className="text-xs" style={{ color: 'var(--muted)', lineHeight: 1.6 }}>
          {t('settings.language.note')} <code
            className="text-[11px] px-1 py-0.5 rounded"
            style={{ background: 'var(--bg-elevated)', color: 'var(--text-strong)' }}
          >src/prompts/</code>
        </p>
      </div>
    </div>
  )
}

function EmailHistory() {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['emailLogs'],
    queryFn: () => getEmailLogs({ page_size: 20 }),
    enabled: open,
  })

  const queryClient = useQueryClient()
  const testMutation = useMutation({
    mutationFn: sendTestEmail,
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['emailLogs'] }),
  })

  const testResult = testMutation.data

  if (!open) {
    return (
      <div className="flex items-center gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-1.5 text-xs cursor-pointer"
          style={{ background: 'none', border: 'none', color: 'var(--muted)', padding: 0 }}
        >
          <History size={12} />
          {t('settings.email.sendHistory')}
          <ChevronRight size={12} />
        </button>
        <div className="ml-auto">
          <button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs cursor-pointer disabled:opacity-50"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            {testMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
            {t('settings.email.sendTest')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setOpen(false)}
          className="flex items-center gap-1.5 text-xs cursor-pointer"
          style={{ background: 'none', border: 'none', color: 'var(--muted)', padding: 0 }}
        >
          <History size={12} />
          {t('settings.email.sendHistory')}
          <ChevronDown size={12} />
        </button>
        <button
          onClick={() => testMutation.mutate()}
          disabled={testMutation.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs cursor-pointer disabled:opacity-50"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text)' }}
        >
          {testMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
          {t('settings.email.sendTest')}
        </button>
      </div>

      {testResult && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs mb-3"
          style={{
            background: testResult.status === 'ok' ? 'var(--ok-subtle)' : 'var(--danger-subtle)',
            color: testResult.status === 'ok' ? 'var(--ok)' : 'var(--danger)',
          }}
        >
          {testResult.status === 'ok' ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
          {testResult.message}
        </div>
      )}

      {isLoading ? (
        <div className="h-20 rounded-lg animate-pulse" style={{ background: 'var(--bg-elevated)' }} />
      ) : data?.items?.length > 0 ? (
        <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border)' }}>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: 'var(--bg-elevated)' }}>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--muted)' }}>{t('settings.email.time')}</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--muted)' }}>{t('settings.email.topic')}</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--muted)' }}>{t('settings.email.type')}</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--muted)' }}>{t('settings.email.recipient')}</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--muted)' }}>{t('settings.email.status')}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map(log => (
                <tr
                  key={log.id}
                  className="border-t"
                  style={{ borderColor: 'var(--border)' }}
                >
                  <td className="px-3 py-2" style={{ color: 'var(--text)' }}>
                    {log.created_at ? new Date(log.created_at).toLocaleString('en-US', {
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    }) : '—'}
                  </td>
                  <td className="px-3 py-2" style={{ color: 'var(--text)' }}>
                    {log.topic_name || '—'}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                      style={{
                        background: log.digest_type === 'test' ? 'var(--bg-muted)' : 'var(--accent-subtle)',
                        color: log.digest_type === 'test' ? 'var(--muted)' : 'var(--accent)',
                      }}
                    >
                      {{ field_overview: t('settings.email.overview'), weekly: t('settings.email.weekly'), monthly: t('settings.email.monthly'), test: t('settings.email.test') }[log.digest_type] || log.digest_type || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2" style={{ color: 'var(--muted)' }}>
                    {log.recipient}
                  </td>
                  <td className="px-3 py-2">
                    {log.status === 'sent' ? (
                      <span className="flex items-center gap-1" style={{ color: 'var(--ok)' }}>
                        <CheckCircle2 size={12} /> {t('settings.email.sent')}
                      </span>
                    ) : (
                      <span
                        className="flex items-center gap-1"
                        style={{ color: 'var(--danger)' }}
                        title={log.error || ''}
                      >
                        <XCircle size={12} /> {t('settings.email.failed')}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-xs py-4 text-center" style={{ color: 'var(--muted)' }}>
          {t('settings.email.none')}
        </p>
      )}
    </div>
  )
}

function EmailSection({ fields, changes, handleChange }) {
  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(fields).map(([fieldKey, meta]) => (
          <FieldInput
            key={fieldKey}
            fieldKey={fieldKey}
            meta={meta}
            value={fieldKey in changes ? changes[fieldKey] : (meta.secret ? undefined : meta.value)}
            onChange={handleChange}
          />
        ))}
      </div>
      <EmailHistory />
    </div>
  )
}

function PipelineSection({ fields, changes, handleChange }) {
  const { t } = useLanguage()
  const regularFields = {}
  const experimentalFields = {}

  for (const [key, meta] of Object.entries(fields)) {
    if (key.startsWith('auto_analysis_')) {
      experimentalFields[key] = meta
    } else {
      regularFields[key] = meta
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(regularFields).map(([fieldKey, meta]) => (
          <FieldInput
            key={fieldKey}
            fieldKey={fieldKey}
            meta={meta}
            value={fieldKey in changes ? changes[fieldKey] : (meta.secret ? undefined : meta.value)}
            onChange={handleChange}
          />
        ))}
      </div>

      {Object.keys(experimentalFields).length > 0 && (
        <div
          className="rounded-lg border p-4"
          style={{
            borderColor: 'color-mix(in srgb, #f59e0b 30%, var(--border))',
            background: 'var(--bg-elevated)',
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <FlaskConical size={14} style={{ color: '#f59e0b' }} />
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: '#f59e0b18', color: '#f59e0b' }}
            >
              {t('settings.pipeline.experimental')}
            </span>
            <span className="text-sm font-medium" style={{ color: 'var(--text-strong)' }}>
              {t('settings.pipeline.autoAnalysis')}
            </span>
          </div>
          <p className="text-xs mb-3" style={{ color: 'var(--muted)', lineHeight: 1.5 }}>
            {t('settings.pipeline.autoAnalysisDesc')}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(experimentalFields).map(([fieldKey, meta]) => (
              <FieldInput
                key={fieldKey}
                fieldKey={fieldKey}
                meta={meta}
                value={fieldKey in changes ? changes[fieldKey] : (meta.secret ? undefined : meta.value)}
                onChange={handleChange}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AppSettings() {
  const { t } = useLanguage()
  const queryClient = useQueryClient()
  const [changes, setChanges] = useState({})
  const [message, setMessage] = useState(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
  })

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [message])

  const mutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['costStats'] })
      setChanges({})
      setMessage({ type: 'success', text: t('settings.saved') })
    },
    onError: (err) => {
      setMessage({ type: 'error', text: err?.response?.data?.detail || t('settings.failedToSave') })
    },
  })

  const handleChange = useCallback((key, value) => {
    setChanges(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleSave = () => {
    const payload = {}
    for (const [key, value] of Object.entries(changes)) {
      const meta = findMeta(key)
      if (meta?.secret && (value === '' || value == null)) continue
      payload[key] = value
    }
    if (Object.keys(payload).length === 0) return
    mutation.mutate(payload)
  }

  const findMeta = (key) => {
    if (!settings) return null
    for (const cat of Object.values(settings)) {
      if (cat[key]) return cat[key]
    }
    return null
  }

  const hasChanges = Object.keys(changes).length > 0

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight mb-1"
          style={{ color: 'var(--text-strong)' }}
        >
          {t('settings.title')}
        </h1>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          {t('settings.subtitle')}
        </p>
      </div>

      {message && (
        <div
          className="flex items-center gap-2 px-4 py-3 rounded-lg mb-5 text-sm"
          style={{
            background: message.type === 'success' ? 'var(--ok-subtle)' : 'var(--danger-subtle)',
            color: message.type === 'success' ? 'var(--ok)' : 'var(--danger)',
          }}
        >
          {message.type === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
          {message.text}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-5">
          {[1, 2, 3, 4].map(i => (
            <div
              key={i}
              className="h-40 rounded-xl animate-pulse"
              style={{ background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      ) : settings && (
        <>
          {SECTIONS.map(({ key: catKey, labelKey, icon: Icon }) => {
            const fields = catKey === 'language' ? settings.prompts : settings[catKey]
            if (!fields) return null
            return (
              <div
                key={catKey}
                className="rounded-xl border p-5 mb-5"
                style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
              >
                <div className="flex items-center gap-2 mb-4">
                  <Icon size={18} style={{ color: 'var(--accent)' }} />
                  <h2 className="text-sm font-semibold" style={{ color: 'var(--text-strong)' }}>
                    {t(labelKey)}
                  </h2>
                </div>
                {catKey === 'language' ? (
                  <LanguageSection fields={fields} changes={changes} handleChange={handleChange} />
                ) : catKey === 'api' ? (
                  <ApiProviderEditor fields={fields} changes={changes} handleChange={handleChange} />
                ) : catKey === 'schedule' ? (
                  <ScheduleEditor fields={fields} changes={changes} handleChange={handleChange} />
                ) : catKey === 'email' ? (
                  <EmailSection fields={fields} changes={changes} handleChange={handleChange} />
                ) : catKey === 'pipeline' ? (
                  <PipelineSection fields={fields} changes={changes} handleChange={handleChange} />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(fields).map(([fieldKey, meta]) => (
                      <FieldInput
                        key={fieldKey}
                        fieldKey={fieldKey}
                        meta={meta}
                        value={fieldKey in changes ? changes[fieldKey] : (meta.secret ? undefined : meta.value)}
                        onChange={handleChange}
                      />
                    ))}
                  </div>
                )}
              </div>
            )
          })}

          <div className="flex items-center justify-end gap-3 mt-2">
            {hasChanges && (
              <button
                onClick={() => setChanges({})}
                className="px-4 py-2 rounded-lg text-sm cursor-pointer"
                style={{
                  background: 'transparent',
                  color: 'var(--muted)',
                  border: '1px solid var(--border)',
                }}
              >
                {t('settings.discard')}
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!hasChanges || mutation.isPending}
              className="px-5 py-2 rounded-lg text-sm font-medium cursor-pointer disabled:opacity-40"
              style={{
                background: 'var(--accent)',
                color: 'var(--accent-foreground)',
                border: 'none',
              }}
            >
              {mutation.isPending ? t('settings.saving') : t('settings.saveChanges')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default AppSettings
