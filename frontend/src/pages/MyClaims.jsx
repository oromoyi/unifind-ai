import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync, useToast } from '../lib/hooks'
import { EmptyState, ErrorBox, PageHeader, Pagination, Spinner, StatusBadge } from '../components/ui'
import { fmtDate, getItemPhoto } from '../lib/format'

export default function MyClaims() {
  const toast = useToast()
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => api.get(`/claims?page=${page}`), [page])
  const withdraw = async (id) => { try { await api.post(`/claims/${id}/withdraw`); toast('Claim withdrawn.'); reload() } catch (e) { toast(e.message, 'error') } }
  return (
    <>
      <PageHeader title="My claims" subtitle="Track verification and recovery status." />
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No claims yet" text="Find your item in the browse page and press “This is mine”." action={<Link className="btn-primary" to="/browse">Browse found items</Link>} />
        : <><ul className="space-y-3">{data.items.map((c) => (
          <li key={c.id} className="card flex flex-wrap items-center gap-4 p-4">
            <img src={c.item_image || getItemPhoto({ title: c.item_title })} alt="" className="h-16 w-16 rounded-lg object-cover" />
            <div className="min-w-0 flex-1"><p className="font-medium">{c.item_title}</p><p className="text-xs text-slate-500">Submitted {fmtDate(c.created_at)}</p>
              {c.review_reason && <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Officer note: {c.review_reason}</p>}</div>
            <StatusBadge status={c.status} />
            {c.status === 'approved' && <Link className="btn-accent" to="/app/handovers">Collection details</Link>}
            {c.status === 'pending' && <button className="btn-outline" onClick={() => withdraw(c.id)}>Withdraw</button>}
          </li>))}</ul><Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} /></>}
    </>
  )
}
