import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync } from '../lib/hooks'
import { EmptyState, ErrorBox, ItemCard, KpiCard, PageHeader, Spinner, StatusBadge } from '../components/ui'
import { fmtDate } from '../lib/format'

export const C = { navy: '#1d4283', teal: '#17a89f', amber: '#d97706', slate: '#94a3b8' }

function StaffDashboard() {
  const { user, can } = useAuth()
  const a = useAsync(() => api.get('/admin/analytics'), [])
  const pending = useAsync(() => api.get('/claims?status=pending&per_page=5'), [])
  if (a.loading) return <Spinner />
  if (a.error) return <ErrorBox error={a.error} onRetry={a.reload} />
  const k = a.data.kpis
  return (
    <>
      <PageHeader title={user.role === 'admin' ? 'Administrator dashboard' : 'Officer dashboard'} subtitle="Live figures computed from the database." />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label="Available items" value={k.available_items} /><KpiCard label="Open lost reports" value={k.lost_reports} />
        <KpiCard label="Pending claims" value={k.pending_claims} hint={`${k.suspicious_claims} flagged`} /><KpiCard label="Awaiting review" value={k.pending_review} />
        <KpiCard label="Returned" value={k.returned_items} accent /><KpiCard label="Recovery rate" value={`${k.recovery_rate_pct}%`} accent />
        <KpiCard label="Avg. time to recovery" value={k.avg_time_to_recovery_hours === null ? 'n/a' : `${k.avg_time_to_recovery_hours} h`} /><KpiCard label="Users" value={k.total_users} />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="card p-4"><h2 className="mb-3 text-base">Activity (last 6 months)</h2>
          <div className="h-64" role="img" aria-label="Line chart of lost reports, found items and returns per month">
            <ResponsiveContainer><LineChart data={a.data.monthly}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="month" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip /><Legend />
              <Line dataKey="lost" name="Lost" stroke={C.amber} strokeWidth={2} /><Line dataKey="found" name="Found" stroke={C.navy} strokeWidth={2} /><Line dataKey="returned" name="Returned" stroke={C.teal} strokeWidth={2} /></LineChart></ResponsiveContainer></div></section>
        <section className="card p-4"><h2 className="mb-3 text-base">Claims awaiting review</h2>
          {pending.loading ? <Spinner /> : pending.data?.items.length ? <ul className="divide-y divide-slate-100 dark:divide-navy-800">{pending.data.items.map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-2 py-2 text-sm"><span>{c.item_title}<br /><span className="text-xs text-slate-500">{c.claimant?.name} · {fmtDate(c.created_at)}</span></span>{c.suspicious && <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-800">Flagged</span>}</li>))}</ul>
            : <p className="text-sm text-slate-500">No pending claims.</p>}
          {can('claims.review') && <Link className="btn-primary mt-3" to="/app/admin/manage">Open review queue</Link>}</section>
      </div>
    </>
  )
}

function MemberDashboard() {
  const { user } = useAuth()
  const isStudent = user.role === 'student'
  const mine = useAsync(() => api.get(isStudent ? '/lost?per_page=4' : '/found?mine=1&per_page=4'), [])
  const matches = useAsync(() => (isStudent ? api.get('/matches') : Promise.resolve({ matches: [] })), [])
  const claims = useAsync(() => (isStudent ? api.get('/claims?per_page=5') : Promise.resolve({ items: [] })), [])
  const handovers = useAsync(() => (isStudent ? api.get('/handovers?status=ready') : Promise.resolve({ items: [] })), [])
  const m = mine.data?.items || []
  return (
    <>
      <PageHeader title={`Hello, ${user.full_name.split(' ')[0]}`} subtitle={isStudent ? 'Track your lost items, matches and claims.' : 'Thank you for helping return property to its owners.'}
        actions={<Link className="btn-primary" to={isStudent ? '/app/report-lost' : '/app/report-found'}>{isStudent ? 'Report lost item' : 'Register found item'}</Link>} />
      {isStudent && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiCard label="My reports" value={mine.data?.total ?? '…'} /><KpiCard label="Suggested matches" value={matches.data?.matches.length ?? '…'} accent />
          <KpiCard label="My claims" value={claims.data?.total ?? '…'} /><KpiCard label="Ready to collect" value={handovers.data?.items.length ?? '…'} accent />
        </div>)}
      {isStudent && handovers.data?.items.length > 0 && <div className="mt-4 rounded-xl border border-teal-300 bg-teal-50 p-4 text-sm text-teal-900 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-100">🎉 You have {handovers.data.items.length} item(s) ready for collection. <Link className="font-semibold underline" to="/app/handovers">See handover codes</Link></div>}
      <h2 className="mb-3 mt-8 text-lg">{isStudent ? 'Recent lost reports' : 'My recent found items'}</h2>
      {mine.loading ? <Spinner /> : mine.error ? <ErrorBox error={mine.error} /> : m.length === 0 ? <EmptyState title="No reports yet" text="Create your first report to get started." action={<Link className="btn-primary" to={isStudent ? '/app/report-lost' : '/app/report-found'}>Create report</Link>} />
        : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{m.map((i) => <ItemCard key={i.id} item={i} to={isStudent ? `/app/lost/${i.id}` : `/items/${i.id}`} />)}</div>}
      {isStudent && claims.data?.items.length > 0 && <><h2 className="mb-3 mt-8 text-lg">Recent claims</h2>
        <ul className="card divide-y divide-slate-100 dark:divide-navy-800">{claims.data.items.map((c) => <li key={c.id} className="flex items-center justify-between p-3 text-sm"><span>{c.item_title}</span><StatusBadge status={c.status} /></li>)}</ul></>}
    </>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  return user.role === 'admin' || user.role === 'officer' ? <StaffDashboard /> : <MemberDashboard />
}
