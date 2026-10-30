import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

/** Fetch helper with loading/error state. `fn` must be stable or wrapped in useCallback. */
export function useAsync(fn, deps = []) {
  const [state, set] = useState({ data: null, loading: true, error: null })
  const run = useCallback(() => {
    set((s) => ({ ...s, loading: true, error: null }))
    return fn().then((data) => set({ data, loading: false, error: null }))
      .catch((error) => set({ data: null, loading: false, error }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { run() }, [run])
  return { ...state, reload: run }
}

export function useDebounced(value, ms = 350) {
  const [v, setV] = useState(value)
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t) }, [value, ms])
  return v
}

const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const id = useRef(0)
  const push = useCallback((message, type = 'success') => {
    const key = ++id.current
    setItems((l) => [...l, { key, message, type }])
    setTimeout(() => setItems((l) => l.filter((i) => i.key !== key)), 4500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.key} className={`animate-fade-up rounded-lg px-4 py-3 text-sm text-white shadow-lg ${t.type === 'error' ? 'bg-red-600' : 'bg-navy-800 dark:bg-teal-600'}`}>{t.message}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const toggle = () => {
    const next = !dark
    document.documentElement.classList.toggle('dark', next)
    try { localStorage.setItem('theme', next ? 'dark' : 'light') } catch { /* ignore */ }
    setDark(next)
  }
  return [dark, toggle]
}
