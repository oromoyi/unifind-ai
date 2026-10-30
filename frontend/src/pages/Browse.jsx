import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, qs } from '../lib/api'
import { useAsync, useDebounced } from '../lib/hooks'
import { EmptyState, ErrorBox, ItemCard, ItemCardSkeleton, Pagination, Select, Spinner } from '../components/ui'

function AiSearchBar({ meta, onApply }) {
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [summary, setSummary] = useState('')
  const [error, setError] = useState('')

  const run = async () => {
    if (!query.trim()) return
    setBusy(true); setError(''); setSummary('')
    try {
      const d = await api.post('/ai/search', { query })
      const f = d.filters
      // Map location name → id from meta
      const locId = meta?.locations?.find(l => l.name === f.location)?.id || ''
      onApply({
        q: f.q || '',
        category_id: f.category_id ? String(f.category_id) : '',
        color: f.color || '',
        location_id: locId ? String(locId) : '',
        date_from: f.date_from || '',
        date_to: f.date_to || '',
      })
      if (f.summary) setSummary(f.summary)
    } catch (e) {
      setError(e.message || 'AI search failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-4 rounded-xl border border-teal-300 bg-teal-50/70 p-4 dark:border-teal-700 dark:bg-teal-950/20">
      <div className="flex items-center gap-2 mb-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-teal-600 text-[11px] font-bold text-white">AI</span>
        <span className="text-sm font-semibold text-teal-800 dark:text-teal-200">Smart Search</span>
        <span className="text-xs text-teal-600 dark:text-teal-400">— describe what you're looking for naturally</span>
      </div>
      <div className="flex gap-2">
        <input
          className="input flex-1 text-sm"
          placeholder='e.g. "I lost a blue Samsung phone near the library last week"'
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && run()}
          disabled={busy}
        />
        <button
          onClick={run}
          disabled={busy || !query.trim()}
          className="btn-accent shrink-0 disabled:opacity-50"
        >
          {busy
            ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            : 'Search'}
        </button>
      </div>
      {summary && (
        <p className="mt-2 text-xs text-teal-700 dark:text-teal-300">
          <span className="font-semibold">AI understood:</span> {summary}
        </p>
      )}
      {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}

export default function Browse() {
  const [sp, setSp] = useSearchParams()
  const [f, setF] = useState({ q: sp.get('q') || '', category_id: '', location_id: '', color: '', date_from: '', date_to: '', sort: 'newest' })
  const [page, setPage] = useState(1)
  const dq = useDebounced(f.q)
  const meta = useAsync(() => api.get('/meta'), [])
  const params = { ...f, q: dq, page, per_page: 12 }
  const res = useAsync(() => api.get('/found' + qs(params)), [JSON.stringify(params)])
  useEffect(() => { setPage(1) }, [dq, f.category_id, f.location_id, f.color, f.date_from, f.date_to, f.sort])
  useEffect(() => { setSp(dq ? { q: dq } : {}, { replace: true }) }, [dq])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const applyAiFilters = (filters) => {
    setF(prev => ({ ...prev, ...filters, sort: prev.sort }))
    setPage(1)
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl">Browse found items</h1>
      <p className="mt-1 text-sm text-slate-500">Public descriptions only. Private identifying details are kept hidden to prevent false claims.</p>

      {/* AI Smart Search */}
      <div className="mt-5">
        <AiSearchBar meta={meta.data} onApply={applyAiFilters} />
      </div>

      {/* Manual filters */}
      <form className="card grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4" role="search" onSubmit={(e) => e.preventDefault()}>
        <div className="sm:col-span-2"><label className="label" htmlFor="q">Search keywords</label><input id="q" className="input" placeholder="Keywords: black, Samsung, keys…" value={f.q} onChange={set('q')} /></div>
        <Select id="cat" label="Category" placeholder="All categories" options={meta.data?.categories || []} value={f.category_id} onChange={set('category_id')} />
        <Select id="loc" label="Found at" placeholder="All locations" options={meta.data?.locations || []} value={f.location_id} onChange={set('location_id')} />
        <div><label className="label" htmlFor="color">Colour</label><input id="color" className="input" placeholder="e.g. blue" value={f.color} onChange={set('color')} /></div>
        <div><label className="label" htmlFor="df">Found from</label><input id="df" type="date" className="input" value={f.date_from} onChange={set('date_from')} /></div>
        <div><label className="label" htmlFor="dt">Found until</label><input id="dt" type="date" className="input" value={f.date_to} onChange={set('date_to')} /></div>
        <Select id="sort" label="Sort by" options={[{ value: 'newest', label: 'Newest first' }, { value: 'oldest', label: 'Oldest first' }, { value: 'title', label: 'Title A–Z' }]} value={f.sort} onChange={set('sort')} />
      </form>

      {/* Quick Campus Hotspot Filters */}
      {meta.data?.locations?.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 mr-1">Hotspots:</span>
          <button
            type="button"
            onClick={() => setF(p => ({ ...p, location_id: '' }))}
            className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
              !f.location_id ? 'bg-navy-800 text-white dark:bg-teal-500 dark:text-navy-950' : 'bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-navy-800 dark:text-slate-300'
            }`}
          >
            All Campus
          </button>
          {meta.data.locations.map(loc => (
            <button
              key={loc.id}
              type="button"
              onClick={() => setF(p => ({ ...p, location_id: String(loc.id) }))}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                String(f.location_id) === String(loc.id)
                  ? 'bg-navy-800 text-white dark:bg-teal-500 dark:text-navy-950'
                  : 'bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-navy-800 dark:text-slate-300'
              }`}
            >
              📍 {loc.name}
            </button>
          ))}
        </div>
      )}

      <div className="mt-6" aria-live="polite">
        {res.loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map(n => <ItemCardSkeleton key={n} />)}
          </div>
        ) : res.error ? <ErrorBox error={res.error} onRetry={res.reload} /> :
          res.data.items.length === 0 ? <EmptyState title="No matching items" text="Try fewer keywords or clear the filters. You can also report your lost item so we can notify you when it appears." /> :
            <><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{res.data.items.map((i) => <ItemCard key={i.id} item={i} />)}</div>
              <Pagination page={res.data.page} pages={res.data.pages} total={res.data.total} onChange={setPage} /></>}
      </div>
    </div>
  )
}
