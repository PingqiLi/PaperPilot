import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTasks } from '../api/tasks'
import { qk } from '../api/queryKeys'

const TaskContext = createContext()

export function TaskProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const prevRunningRef = useRef(new Set())

  const { data } = useQuery({
    queryKey: qk.activeTasks,
    queryFn: () => getTasks({ status: 'running,awaiting_approval', limit: 50 }),
    refetchInterval: (query) => {
      const items = query.state.data?.items
      return items?.length > 0 ? 3000 : 15000
    },
  })

  const runningCount = data?.items?.length || 0

  useEffect(() => {
    if (!data?.items) return
    const currentIds = new Set(data.items.map(t => t.id))
    const prevIds = prevRunningRef.current
    for (const t of data.items) {
      if (!prevIds.has(t.id)) break
    }
    prevRunningRef.current = currentIds
  }, [data])

  const addToast = useCallback((toast) => {
    const id = toast.id || Date.now()
    setToasts(prev => [...prev, { ...toast, id, timestamp: Date.now() }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <TaskContext.Provider value={{ tasks: data?.items || [], runningCount, toasts, addToast, removeToast }}>
      {children}
    </TaskContext.Provider>
  )
}

export function useTasks() {
  const ctx = useContext(TaskContext)
  if (!ctx) throw new Error('useTasks must be used within TaskProvider')
  return ctx
}
