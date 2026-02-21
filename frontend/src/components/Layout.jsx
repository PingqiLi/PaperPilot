import { Link, useLocation } from 'react-router-dom'
import {
  Home, BarChart3, Settings, Sun, Moon, Plus, ListTodo,
} from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'
import { useTasks } from '../contexts/TaskContext'
import TaskToast from './TaskToast'

const NAV_ITEMS = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/tasks', icon: ListTodo, label: 'Tasks', hasBadge: true },
  { to: '/stats', icon: BarChart3, label: 'Cost Stats' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function NavLink({ to, icon: Icon, label, active, badge }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors no-underline"
      style={{
        background: active ? 'var(--bg-hover)' : 'transparent',
        color: active ? 'var(--text-strong)' : 'var(--muted)',
      }}
    >
      <Icon size={18} />
      {label}
      {badge > 0 && (
        <span
          className="ml-auto text-[10px] min-w-[18px] h-[18px] flex items-center justify-center rounded-full font-semibold"
          style={{
            background: 'var(--accent)',
            color: 'var(--accent-foreground)',
            animation: 'pulse-subtle 2s ease-in-out infinite',
          }}
        >
          {badge}
        </span>
      )}
    </Link>
  )
}

function Layout({ children }) {
  const location = useLocation()
  const { theme, toggleTheme } = useTheme()
  const { runningCount } = useTasks()

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg)' }}>
      <aside
        className="w-64 flex-shrink-0 flex flex-col border-r"
        style={{
          background: 'var(--bg-accent)',
          borderColor: 'var(--border)',
        }}
      >
        <Link to="/" className="p-5 flex items-center gap-3 no-underline" style={{ color: 'inherit' }}>
          <svg viewBox="0 0 32 32" fill="none" className="w-7 h-7 flex-shrink-0" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="7" fill="var(--accent)"/>
            <path d="M10 7h8.5l5.5 5.5V25a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z" fill="white"/>
            <path d="M18.5 7v4a1.5 1.5 0 0 0 1.5 1.5h4" fill="currentColor" fillOpacity="0.08"/>
            <rect x="11" y="15.5" width="9" height="1.2" rx="0.6" fill="var(--accent)" opacity="0.45"/>
            <rect x="11" y="18.5" width="6.5" height="1.2" rx="0.6" fill="var(--accent)" opacity="0.3"/>
            <rect x="11" y="21.5" width="7.5" height="1.2" rx="0.6" fill="var(--accent)" opacity="0.18"/>
            <circle cx="25" cy="7" r="5" fill="var(--accent-hover)"/>
            <path d="M23 7l1 1 2-2" stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          </svg>
          <span
            className="text-base font-semibold tracking-tight"
            style={{ color: 'var(--text-strong)' }}
          >
            PaperPilot
          </span>
          <span
            className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-medium"
            style={{
              background: 'var(--accent-subtle)',
              color: 'var(--accent)',
            }}
          >
            v1.0
          </span>
        </Link>

        <div className="px-3 mb-2">
          <Link
            to="/topics/new"
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline"
            style={{
              background: 'var(--accent)',
              color: 'var(--accent-foreground)',
            }}
          >
            <Plus size={16} />
            New Topic
          </Link>
        </div>

        <nav className="px-3 py-2 flex flex-col gap-1">
          {NAV_ITEMS.map(({ to, icon, label, hasBadge }) => {
            const active = location.pathname === to
            return (
              <NavLink
                key={to}
                to={to}
                icon={icon}
                label={label}
                active={active}
                badge={hasBadge ? runningCount : null}
              />
            )
          })}
        </nav>

        <div className="flex-1" />

        <div
          className="p-3 border-t flex items-center justify-between"
          style={{ borderColor: 'var(--border)' }}
        >
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            PaperPilot
          </span>
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-md transition-colors cursor-pointer"
            style={{
              background: 'transparent',
              color: 'var(--muted)',
              border: 'none',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </aside>

      <main
        className="flex-1 overflow-auto"
        style={{ background: 'var(--bg)' }}
      >
        {children}
      </main>
      <TaskToast />
    </div>
  )
}

export default Layout
