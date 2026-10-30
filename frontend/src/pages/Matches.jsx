import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import MatchCard from '../components/MatchCard'
import { EmptyState, ErrorBox, PageHeader, Spinner } from '../components/ui'

export default function Matches() {
  const { data, loading, error, reload } = useAsync(() => api.get('/matches'), [])
  return (
    <>
      <PageHeader title="AI suggested matches" subtitle="Ranked by a weighted, explainable score. Suggestions never prove ownership — you still need to claim and verify." />
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.matches.length === 0
        ? <EmptyState title="No suggested matches yet" text="We will notify you as soon as a similar found item is registered." action={<Link className="btn-primary" to="/app/report-lost">Report a lost item</Link>} />
        : <div className="space-y-4">{data.matches.map((m) => <MatchCard key={m.id} m={m} />)}</div>}
    </>
  )
}
