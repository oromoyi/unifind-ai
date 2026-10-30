import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { useAsync, useToast } from '../../lib/hooks'
import { ErrorBox, KpiCard, PageHeader, Spinner } from '../../components/ui'
import { titleCase } from '../../lib/format'

const COLORS = ['#1d4283', '#17a89f', '#d97706', '#7c3aed', '#dc2626', '#64748b']
const pct = (x) => `${(x * 100).toFixed(1)}%`

function Exports() {
  const toast = useToast()
  const kinds = [['summary', 'KPI summary'], ['found-items', 'Found items'], ['lost-reports', 'Lost reports'], ['claims', 'Claims']]
  const dl = (kind, fmt) => api.download(`/admin/export/${kind}?format=${fmt}`, `${kind}.${fmt}`).catch((e) => toast(e.message, 'error'))
  return (
    <section className="card p-4"><h2 className="mb-3 text-base">Downloadable reports</h2>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{kinds.map(([k, l]) => (
        <div key={k} className="rounded-lg border border-slate-200 p-3 dark:border-navy-700"><p className="mb-2 text-sm font-medium">{l}</p><div className="flex gap-2"><button className="btn-outline !py-1" onClick={() => dl(k, 'csv')}>CSV</button><button className="btn-outline !py-1" onClick={() => dl(k, 'pdf')}>PDF</button></div></div>))}</div></section>
  )
}

function Evaluation() {
  const { data, loading, error, reload } = useAsync(() => api.get('/admin/evaluation'), [])
  if (loading) return <Spinner label="Running offline evaluation…" />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const b = data.baseline_keyword, m = data.weighted_matcher
  const metrics = [['precision_at_1', 'Precision@1'], ['hit_rate_at_3', 'Hit-rate@3'], ['hit_rate_at_5', 'Hit-rate@5'], ['mrr', 'MRR']]
  const bar = metrics.map(([k, l]) => ({ metric: l, 'Keyword baseline': b[k], 'Weighted matcher': m[k] }))
  const curve = data.threshold_curve.matcher.map((r, i) => ({ threshold: r.threshold, Precision: r.precision, Recall: r.recall, F1: r.f1, 'Baseline F1': data.threshold_curve.baseline_keyword_normalised[i].f1 }))
  return (
    <section className="card space-y-4 p-4">
      <div><h2 className="text-base">Research evaluation: keyword baseline vs weighted matcher</h2>
        <p className="mt-1 rounded-lg bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-100"><strong>Read carefully:</strong> {data.note} Dataset “{data.dataset.name}”: {data.dataset.lost_reports} lost reports, {data.dataset.found_items} found items, {data.dataset.true_pairs} labelled true pairs. Computed live with the current admin weights.</p></div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="h-64" role="img" aria-label="Bar chart comparing ranking metrics of the keyword baseline and the weighted matcher"><ResponsiveContainer><BarChart data={bar}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="metric" fontSize={12} /><YAxis domain={[0, 1]} fontSize={12} /><Tooltip formatter={(v) => pct(v)} /><Legend /><Bar dataKey="Keyword baseline" fill="#94a3b8" /><Bar dataKey="Weighted matcher" fill="#17a89f" /></BarChart></ResponsiveContainer></div>
        <div className="h-64" role="img" aria-label="Line chart of precision, recall and F1 by score threshold"><ResponsiveContainer><LineChart data={curve}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="threshold" fontSize={12} label={{ value: 'Score threshold', position: 'insideBottom', offset: -2, fontSize: 11 }} /><YAxis domain={[0, 1]} fontSize={12} /><Tooltip formatter={(v) => pct(v)} /><Legend />
          <Line dataKey="Precision" stroke="#1d4283" strokeWidth={2} /><Line dataKey="Recall" stroke="#17a89f" strokeWidth={2} /><Line dataKey="F1" stroke="#d97706" strokeWidth={2} /><Line dataKey="Baseline F1" stroke="#94a3b8" strokeDasharray="5 5" /></LineChart></ResponsiveContainer></div>
      </div>
      <div className="overflow-x-auto"><table className="w-full"><thead><tr><th className="th">Metric</th><th className="th">Keyword baseline</th><th className="th">Weighted matcher</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-navy-800">{metrics.map(([k, l]) => <tr key={k}><td className="td">{l}</td><td className="td">{b[k]}</td><td className="td font-medium">{m[k]}</td></tr>)}</tbody></table></div>
      <details><summary className="cursor-pointer text-sm font-medium">Methodology</summary><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{data.methodology.map((x) => <li key={x}>{x}</li>)}</ul></details>
    </section>
  )
}

export default function Analytics() {
  const { can } = useAuth()
  const { data, loading, error, reload } = useAsync(() => api.get('/admin/analytics'), [])
  if (loading) return <Spinner />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const k = data.kpis
  return (
    <>
      <PageHeader title="Analytics & research" subtitle="Recovery performance, user feedback and matching-algorithm evaluation." />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label="Recovery rate" value={`${k.recovery_rate_pct}%`} hint="returned ÷ published found items" accent /><KpiCard label="Avg. time to recovery" value={k.avg_time_to_recovery_hours === null ? 'n/a' : `${k.avg_time_to_recovery_hours} h`} hint="item registered → handover" />
        <KpiCard label="Avg. feedback" value={k.avg_feedback_rating === null ? 'n/a' : `${k.avg_feedback_rating} / 5`} hint={`${k.feedback_count} response(s)`} /><KpiCard label="Suspicious pending claims" value={k.suspicious_claims} />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="card p-4"><h2 className="mb-3 text-base">Lost vs found vs returned</h2><div className="h-64" role="img" aria-label="Monthly line chart"><ResponsiveContainer><LineChart data={data.monthly}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="month" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip /><Legend /><Line dataKey="lost" stroke="#d97706" strokeWidth={2} /><Line dataKey="found" stroke="#1d4283" strokeWidth={2} /><Line dataKey="returned" stroke="#17a89f" strokeWidth={2} /></LineChart></ResponsiveContainer></div></section>
        <section className="card p-4"><h2 className="mb-3 text-base">By category</h2><div className="h-96" role="img" aria-label="Bar chart of lost and found items per category"><ResponsiveContainer><BarChart data={data.by_category} layout="vertical" margin={{ left: 30 }} barCategoryGap="25%"><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis type="number" allowDecimals={false} fontSize={12} /><YAxis type="category" dataKey="category" width={120} fontSize={11} /><Tooltip /><Legend /><Bar dataKey="lost" fill="#d97706" /><Bar dataKey="found" fill="#1d4283" /></BarChart></ResponsiveContainer></div></section>
        <section className="card p-4"><h2 className="mb-3 text-base">Found-item status</h2><div className="h-60" role="img" aria-label="Pie chart of found item statuses"><ResponsiveContainer><PieChart><Pie data={data.found_status} dataKey="count" nameKey="status" outerRadius={80} label={(e) => titleCase(e.status)}>{data.found_status.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div></section>
        <section className="card p-4"><h2 className="mb-3 text-base">Claim outcomes</h2><div className="h-60" role="img" aria-label="Bar chart of claim statuses"><ResponsiveContainer><BarChart data={data.claim_status}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="status" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip /><Bar dataKey="count" fill="#17a89f" /></BarChart></ResponsiveContainer></div>
          <p className="mt-2 text-xs text-slate-500">Operational check: {data.operational_matching.returned_item_was_suggested} of {data.operational_matching.completed_returns_linked_to_report} returns linked to a lost report were previously suggested. {data.operational_matching.note}</p></section>
      </div>
      <div className="mt-6 space-y-6">{can('reports.export') && <Exports />}<Evaluation /></div>
    </>
  )
}
