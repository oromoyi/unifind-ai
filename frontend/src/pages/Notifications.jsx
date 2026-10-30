import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { EmptyState, ErrorBox, PageHeader, Pagination, Spinner } from '../components/ui'
import { fmtDateTime } from '../lib/format'

const ICON = { match: '✨', claim: '🧾', ready: '📦', handover: '🤝', report: '📝', review: '🔎' }

export default function Notifications() {
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => api.get(`/notifications?page=${page}`), [page])
  const read = async (n) => { if (!n.is_read) { await api.post(`/notifications/${n.id}/read`); reload() } }
  const readAll = async () => { await api.post('/notifications/read-all'); reload() }
  return (
    <>
      <PageHeader title="Notifications" actions={data?.unread > 0 && <button className="btn-outline" onClick={readAll}>Mark all as read</button>} />
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="You’re all caught up" text="Match alerts and claim updates appear here." />
        : <><ul className="space-y-2">{data.items.map((n) => (
          <li key={n.id} className={`card flex items-start gap-3 p-4 ${n.is_read ? 'opacity-70' : 'border-l-4 border-l-teal-500'}`}>
            <span className="text-xl" aria-hidden>{ICON[n.type] || '🔔'}</span>
            <div className="min-w-0 flex-1"><p className="font-medium">{n.title}</p><p className="text-sm text-slate-600 dark:text-slate-400">{n.message}</p><p className="mt-1 text-xs text-slate-500">{fmtDateTime(n.created_at)}</p></div>
            <div className="flex flex-col items-end gap-1">{n.link && <Link className="text-sm text-teal-700 underline dark:text-teal-300" to={n.link} onClick={() => read(n)}>Open</Link>}{!n.is_read && <button className="text-xs text-slate-500 underline" onClick={() => read(n)}>Mark read</button>}</div>
          </li>))}</ul><Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} /></>}
    </>
  )
}
