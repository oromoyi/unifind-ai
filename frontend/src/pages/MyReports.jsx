import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, qs } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync } from '../lib/hooks'
import { EmptyState, ErrorBox, ItemCard, ItemCardSkeleton, PageHeader, Pagination, Select, Spinner } from '../components/ui'
import { exportToCsv } from '../lib/format'

export default function MyReports() {
  const { user } = useAuth()
  const isStudent = user.role === 'student'
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const url = isStudent ? '/lost' : '/found'
  const { data, loading, error, reload } = useAsync(() => api.get(url + qs({ page, status, mine: isStudent ? '' : 1, per_page: 12 })), [page, status, url])
  const statuses = isStudent ? ['pending', 'open', 'matched', 'recovered', 'closed', 'rejected'] : ['pending', 'available', 'claimed', 'returned', 'rejected', 'archived']
  return (
    <>
      <PageHeader 
        title={isStudent ? 'My lost reports' : 'My found items'} 
        subtitle="Complete history with live status." 
        actions={
          <div className="flex items-center gap-2">
            {data?.items?.length > 0 && (
              <button 
                type="button" 
                className="btn-outline text-xs"
                onClick={() => exportToCsv(isStudent ? 'my-lost-reports' : 'my-found-items', data.items, [
                  { header: 'ID', key: 'id' },
                  { header: 'Title', key: 'title' },
                  { header: 'Category', key: 'category' },
                  { header: 'Location', key: 'location' },
                  { header: 'Date', key: 'date' },
                  { header: 'Status', key: 'status' }
                ])}
              >
                📥 Export CSV
              </button>
            )}
            <Link className="btn-primary" to={isStudent ? '/app/report-lost' : '/app/report-found'}>
              + New {isStudent ? 'lost report' : 'found item'}
            </Link>
          </div>
        } 
      />
      <div className="mb-4 max-w-xs"><Select id="st" label="Filter by status" placeholder="All statuses" options={statuses.map((s) => ({ value: s, label: s[0].toUpperCase() + s.slice(1) }))} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} /></div>
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map(n => <ItemCardSkeleton key={n} />)}
        </div>
      ) : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="Nothing here yet" text="Your reports will appear in this list." />
        : <><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.items.map((i) => <ItemCard key={i.id} item={i} to={isStudent ? `/app/lost/${i.id}` : `/items/${i.id}`} />)}</div>
          <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} /></>}
    </>
  )
}
