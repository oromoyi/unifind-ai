import { Link } from 'react-router-dom'
import { STATUS_STYLE, titleCase, fmtDate, getItemPhoto } from '../lib/format'

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-slate-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function StatusBadge({ status }) {
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[status] || 'bg-slate-200 text-slate-700'}`}>{titleCase(status)}</span>
}

export function EmptyState({ title, text, action }) {
  return (
    <div className="card flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300" aria-hidden>
        <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
      </div>
      <h3 className="text-base">{title}</h3>
      {text && <p className="mt-1 max-w-sm text-sm text-slate-500 dark:text-slate-400">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
      {error.message || String(error)}
      {onRetry && <button className="ml-3 underline" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function Field({ label, error, hint, id, children }) {
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p id={`${id}-err`} role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}

export function Input({ label, error, hint, id, ...props }) {
  return <Field label={label} error={error} hint={hint} id={id}><input id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-err` : undefined} className={`input ${error ? 'border-red-500' : ''}`} {...props} /></Field>
}

export function Textarea({ label, error, hint, id, ...props }) {
  return <Field label={label} error={error} hint={hint} id={id}><textarea id={id} rows={4} aria-invalid={!!error} className={`input ${error ? 'border-red-500' : ''}`} {...props} /></Field>
}

export function Select({ label, error, id, options, placeholder, ...props }) {
  return (
    <Field label={label} error={error} id={id}>
      <select id={id} aria-invalid={!!error} className={`input ${error ? 'border-red-500' : ''}`} {...props}>
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => <option key={o.value ?? o.id} value={o.value ?? o.id}>{o.label ?? o.name}</option>)}
      </select>
    </Field>
  )
}

export function Pagination({ page, pages, total, onChange }) {
  if (!pages || pages <= 1) return total !== undefined ? <p className="mt-3 text-xs text-slate-500">{total} result{total === 1 ? '' : 's'}</p> : null
  return (
    <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pagination">
      <span className="text-slate-500">Page {page} of {pages} · {total} results</span>
      <div className="flex gap-2">
        <button className="btn-outline" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
        <button className="btn-outline" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
      </div>
    </nav>
  )
}

export function Modal({ open, title, onClose, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label={title} onKeyDown={(e) => e.key === 'Escape' && onClose()}>
      <div className="card animate-fade-up max-h-[90vh] w-full max-w-lg overflow-auto p-5">
        <div className="mb-3 flex items-center justify-between"><h2 className="text-lg">{title}</h2>
          <button className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-navy-800" onClick={onClose} aria-label="Close">✕</button></div>
        {children}
      </div>
    </div>
  )
}

export function KpiCard({ label, value, hint, accent }) {
  return (
    <div className="card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accent ? 'text-teal-600 dark:text-teal-300' : 'text-navy-900 dark:text-white'}`}>{value ?? '-'}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl">{title}</h1>{subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}</div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}

export function ItemCard({ item, to }) {
  const photo = getItemPhoto(item)
  return (
    <Link to={to || `/items/${item.id}`} className="card group animate-fade-up overflow-hidden transition hover:shadow-md focus-visible:ring-2">
      <div className="aspect-[4/3] bg-slate-100 overflow-hidden dark:bg-navy-800">
        <img
          src={photo}
          alt={item.title}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          onError={(e) => {
            const fallback = getItemPhoto({ title: item.title, category: item.category })
            if (e.target.src !== fallback) e.target.src = fallback
          }}
        />
      </div>
      <div className="p-4">
        <div className="mb-1 flex items-start justify-between gap-2">
          <h3 className="line-clamp-1 text-base">{item.title}</h3><StatusBadge status={item.status} />
        </div>
        <p className="line-clamp-2 min-h-[2.5rem] text-sm text-slate-600 dark:text-slate-400">{item.description}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
          <span>{item.category}</span><span>📍 {item.location}</span><span>{fmtDate(item.date)}</span>
        </div>
      </div>
    </Link>
  )
}

export function ScoreBar({ score }) {
  const color = score >= 70 ? 'bg-emerald-500' : score >= 50 ? 'bg-teal-500' : 'bg-amber-500'
  return (
    <div className="flex items-center gap-2" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label="Match score">
      <div className="h-2 w-28 overflow-hidden rounded-full bg-slate-200 dark:bg-navy-700"><div className={`h-full ${color}`} style={{ width: `${Math.min(100, score)}%` }} /></div>
      <span className="text-sm font-semibold">{Math.round(score)}%</span>
    </div>
  )
}

export function ItemCardSkeleton() {
  return (
    <div className="card animate-pulse overflow-hidden">
      <div className="aspect-[4/3] bg-slate-200 dark:bg-navy-800" />
      <div className="p-4 space-y-3">
        <div className="flex justify-between items-center">
          <div className="h-4 bg-slate-200 dark:bg-navy-700 rounded w-1/2" />
          <div className="h-4 bg-slate-200 dark:bg-navy-700 rounded-full w-16" />
        </div>
        <div className="space-y-1.5">
          <div className="h-3 bg-slate-200 dark:bg-navy-700 rounded w-full" />
          <div className="h-3 bg-slate-200 dark:bg-navy-700 rounded w-4/5" />
        </div>
        <div className="flex gap-3 pt-2">
          <div className="h-3 bg-slate-200 dark:bg-navy-700 rounded w-16" />
          <div className="h-3 bg-slate-200 dark:bg-navy-700 rounded w-20" />
        </div>
      </div>
    </div>
  )
}

export function ItemTimeline({ status = 'pending', kind = 'found' }) {
  const steps = [
    { key: 'reported', label: 'Reported', desc: 'Item cataloged in UniFind AI' },
    { key: 'matched', label: 'AI Analysis', desc: 'Signals computed & matches ranked' },
    { key: 'claim', label: 'Verification', desc: 'Ownership questions checked' },
    { key: 'returned', label: 'Returned', desc: 'Handover code validated & receipt issued' },
  ]

  const getStepState = (idx) => {
    const isReturned = ['returned', 'recovered', 'completed'].includes(status)
    const isApproved = ['approved', 'ready'].includes(status)
    const isClaimed = ['claimed', 'matched'].includes(status)

    if (isReturned) return 'done'
    if (idx === 0) return 'done'
    if (idx === 1) return isApproved || isClaimed ? 'done' : 'current'
    if (idx === 2) return isApproved ? 'done' : isClaimed ? 'current' : 'upcoming'
    if (idx === 3) return isReturned ? 'done' : isApproved ? 'current' : 'upcoming'
    return 'upcoming'
  }

  return (
    <div className="my-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-navy-700 dark:bg-navy-900">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
        Recovery Lifecycle Timeline
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 relative">
        {steps.map((st, i) => {
          const state = getStepState(i)
          return (
            <div key={st.key} className="flex flex-col items-start relative">
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  state === 'done' 
                    ? 'bg-emerald-500 text-white shadow-sm' 
                    : state === 'current'
                    ? 'bg-teal-600 text-white ring-4 ring-teal-100 dark:ring-teal-900/50'
                    : 'bg-slate-200 text-slate-500 dark:bg-navy-700 dark:text-slate-400'
                }`}>
                  {state === 'done' ? '✓' : i + 1}
                </span>
                <span className={`text-sm font-semibold ${
                  state === 'done' || state === 'current' ? 'text-navy-900 dark:text-white' : 'text-slate-400 dark:text-slate-500'
                }`}>
                  {st.label}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 pl-9 sm:pl-0">{st.desc}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
