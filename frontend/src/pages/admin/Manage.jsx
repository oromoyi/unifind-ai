import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, qs } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { useAsync, useToast } from '../../lib/hooks'
import { EmptyState, ErrorBox, Input, Modal, PageHeader, Pagination, Select, Spinner, StatusBadge } from '../../components/ui'
import { fmtDate, fmtDateTime, getItemPhoto, exportToCsv } from '../../lib/format'

function useReasonDialog(toast, reload) {
  const [d, setD] = useState(null)
  const [reason, setReason] = useState('')
  const open = (title, url, extra = {}) => { setReason(''); setD({ title, url, extra }) }
  const submit = async (e) => {
    e.preventDefault()
    try { await api.post(d.url, { ...d.extra, reason }); toast('Done.'); setD(null); reload() } catch (x) { toast(x.message, 'error') }
  }
  const node = (
    <Modal open={!!d} title={d?.title || ''} onClose={() => setD(null)}>
      <form onSubmit={submit} className="space-y-3"><Input id="reason" label="Reason / verification notes (recorded in the audit log)" value={reason} onChange={(e) => setReason(e.target.value)} autoFocus />
        <div className="flex justify-end gap-2"><button type="button" className="btn-outline" onClick={() => setD(null)}>Cancel</button><button className="btn-primary">Confirm</button></div></form>
    </Modal>)
  return [open, node]
}

function ClaimsTab() {
  const toast = useToast()
  const [status, setStatus] = useState('pending')
  const [flagged, setFlagged] = useState(false)
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => api.get('/claims' + qs({ status, suspicious: flagged ? 1 : '', page })), [status, flagged, page])
  const [ask, dialog] = useReasonDialog(toast, reload)
  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-44"><Select id="cs" label="Status" placeholder="All" options={['pending', 'approved', 'rejected', 'withdrawn'].map((s) => ({ value: s, label: s }))} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} /></div>
          <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={flagged} onChange={(e) => setFlagged(e.target.checked)} />Flagged as suspicious only</label>
        </div>
        {data?.items?.length > 0 && (
          <button
            type="button"
            className="btn-outline text-xs"
            onClick={() => exportToCsv('claims-export', data.items, [
              { header: 'Claim ID', key: 'id' },
              { header: 'Item Title', key: 'item_title' },
              { header: 'Claimant Name', key: (c) => c.claimant?.name || '' },
              { header: 'Claimant Email', key: (c) => c.claimant?.email || '' },
              { header: 'Claimant ID', key: (c) => c.claimant?.student_id || '' },
              { header: 'Status', key: 'status' },
              { header: 'Suspicious', key: (c) => c.suspicious ? 'Yes' : 'No' },
              { header: 'Date', key: 'created_at' }
            ])}
          >
            📥 Export Claims CSV
          </button>
        )}
      </div>
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No claims in this view" /> : (
        <ul className="space-y-3">{data.items.map((c) => (
          <li key={c.id} className={`card p-4 ${c.suspicious ? 'border-red-300 dark:border-red-800' : ''}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <img
                  src={c.item_image || getItemPhoto({ title: c.item_title })}
                  alt=""
                  className="h-14 w-14 rounded-lg object-cover border border-slate-200 dark:border-navy-700"
                />
                <div>
                  <p className="font-semibold text-base">{c.item_title}</p>
                  <p className="text-xs text-slate-500">Claim #{c.id} · {fmtDateTime(c.created_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {c.suspicious && <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800" title={c.flag_reason}>⚠ Flagged</span>}
                <StatusBadge status={c.status} />
              </div>
            </div>
            <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
              <div><p className="text-xs font-semibold uppercase text-slate-500">Claimant</p><p>{c.claimant.name} · {c.claimant.student_id || 'no ID'}</p><p className="text-slate-500">{c.claimant.email}{c.claimant.phone ? ` · ${c.claimant.phone}` : ''}</p>
                <p className="mt-2 text-xs font-semibold uppercase text-slate-500">Claimant’s description</p><p>{c.description}</p></div>
              <div><p className="text-xs font-semibold uppercase text-slate-500">Verification</p>
                <p>Question: {c.verification_question || '— none set —'}</p>
                <p>Automatic answer check: {c.auto_check_passed === null ? 'n/a' : c.auto_check_passed ? <span className="font-medium text-emerald-600">matched</span> : <span className="font-medium text-red-600">did not match</span>}</p>
                {c.flag_reason && <p className="text-red-600">Flag: {c.flag_reason}</p>}
                {c.private_details && <p className="mt-2 rounded bg-amber-50 p-2 text-xs dark:bg-amber-950/30"><strong>Private details on file:</strong> {c.private_details}</p>}
                {c.review_reason && <p className="mt-2 text-xs text-slate-500">Decision note: {c.review_reason}</p>}</div>
            </div>
            {c.status === 'pending' && <div className="mt-3 flex gap-2"><button className="btn-accent" onClick={() => ask('Approve claim', `/claims/${c.id}/approve`)}>Approve</button><button className="btn-danger" onClick={() => ask('Reject claim', `/claims/${c.id}/reject`)}>Reject</button><Link className="btn-outline" to={`/items/${c.found_item_id}`}>View item</Link></div>}
          </li>))}</ul>)}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      {dialog}
    </>
  )
}

function ItemsTab({ kind }) {
  const toast = useToast()
  const [status, setStatus] = useState(kind === 'found' ? 'pending' : 'pending')
  const [page, setPage] = useState(1)
  const url = kind === 'found' ? '/found' : '/lost'
  const { data, loading, error, reload } = useAsync(() => api.get(url + qs({ scope: 'all', status, page, per_page: 10 })), [url, status, page])
  const [ask, dialog] = useReasonDialog(toast, reload)
  const statuses = kind === 'found' ? ['pending', 'available', 'claimed', 'returned', 'rejected', 'archived'] : ['pending', 'open', 'matched', 'recovered', 'closed', 'rejected', 'archived']
  const quick = async (path, body) => { try { await api.post(path, body); toast('Done.'); reload() } catch (x) { toast(x.message, 'error') } }
  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="w-48">
          <Select id="is" label="Status" placeholder="All" options={statuses.map((s) => ({ value: s, label: s }))} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} />
        </div>
        {data?.items?.length > 0 && (
          <button
            type="button"
            className="btn-outline text-xs"
            onClick={() => exportToCsv(`${kind}-items`, data.items, [
              { header: 'ID', key: 'id' },
              { header: 'Title', key: 'title' },
              { header: 'Category', key: 'category' },
              { header: 'Location', key: 'location' },
              { header: 'Date', key: 'date' },
              { header: 'Status', key: 'status' },
              { header: 'Reporter', key: (r) => r.reporter?.name || '' }
            ])}
          >
            📥 Export CSV
          </button>
        )}
      </div>
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="Nothing in this status" /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead><tr><th className="th w-14">Photo</th><th className="th">Item</th><th className="th">Category</th><th className="th">Location</th><th className="th">Date</th><th className="th">Status</th><th className="th">Actions</th></tr></thead>
          <tbody className="divide-y divide-slate-100 dark:divide-navy-800">{data.items.map((i) => (
            <tr key={i.id}>
              <td className="td w-14">
                <img
                  src={i.images?.[0] || getItemPhoto(i)}
                  alt=""
                  className="h-10 w-10 rounded-lg object-cover border border-slate-200 dark:border-navy-700"
                />
              </td>
              <td className="td font-medium">{i.title}<span className="block text-xs text-slate-500">by {i.reporter?.name}</span></td><td className="td">{i.category}</td><td className="td">{i.location}</td><td className="td">{fmtDate(i.date)}</td><td className="td"><StatusBadge status={i.status} /></td>
              <td className="td whitespace-nowrap">
                {i.status === 'pending' && <button className="btn-accent !py-1" onClick={() => quick(`${url}/${i.id}/review`, { decision: 'approve' })}>Approve</button>}{' '}
                {['pending', 'available', 'open'].includes(i.status) && <button className="btn-danger !py-1" onClick={() => ask('Reject report', `${url}/${i.id}/review`, { decision: 'reject' })}>Reject</button>}{' '}
                {['available', 'returned', 'rejected', 'recovered', 'closed'].includes(i.status) && <button className="btn-outline !py-1" onClick={() => quick(`${url}/${i.id}/review`, { decision: 'archive' })}>Archive</button>}{' '}
                {kind === 'found' && <Link className="btn-outline !py-1" to={`/items/${i.id}`}>View</Link>}</td></tr>))}</tbody></table></div>)}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      {dialog}
    </>
  )
}

function CatalogTab() {
  const toast = useToast()
  const cats = useAsync(() => api.get('/admin/categories'), [])
  const locs = useAsync(() => api.get('/admin/locations'), [])
  const [nc, setNc] = useState('')
  const [nl, setNl] = useState({ name: '', zone: '', x: '', y: '' })
  const add = async (path, body, reset, reload) => { try { await api.post(path, body); reset(); reload(); toast('Added.') } catch (x) { toast(x.message, 'error') } }
  const toggle = async (path, o, reload) => { try { await api.put(`${path}/${o.id}`, { is_active: !o.is_active }); reload() } catch (x) { toast(x.message, 'error') } }
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="card p-4"><h2 className="mb-3 text-base">Item categories</h2>
        <form className="mb-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); add('/admin/categories', { name: nc }, () => setNc(''), cats.reload) }}><input aria-label="New category" className="input" placeholder="New category" value={nc} onChange={(e) => setNc(e.target.value)} /><button className="btn-primary">Add</button></form>
        {cats.loading ? <Spinner /> : <ul className="divide-y divide-slate-100 dark:divide-navy-800">{cats.data?.items.map((c) => <li key={c.id} className="flex items-center justify-between py-2 text-sm"><span className={c.is_active ? '' : 'text-slate-400 line-through'}>{c.name}</span><button className="btn-outline !py-1" onClick={() => toggle('/admin/categories', c, cats.reload)}>{c.is_active ? 'Disable' : 'Enable'}</button></li>)}</ul>}</section>
      <section className="card p-4"><h2 className="mb-3 text-base">Campus locations</h2>
        <form className="mb-3 grid grid-cols-2 gap-2" onSubmit={(e) => { e.preventDefault(); add('/admin/locations', { ...nl, x: nl.x === '' ? null : +nl.x, y: nl.y === '' ? null : +nl.y }, () => setNl({ name: '', zone: '', x: '', y: '' }), locs.reload) }}>
          <input aria-label="Location name" className="input col-span-2" placeholder="Location name" value={nl.name} onChange={(e) => setNl({ ...nl, name: e.target.value })} />
          <input aria-label="Zone" className="input" placeholder="Zone" value={nl.zone} onChange={(e) => setNl({ ...nl, zone: e.target.value })} />
          <div className="flex gap-2"><input aria-label="X metres" className="input" placeholder="x (m)" type="number" value={nl.x} onChange={(e) => setNl({ ...nl, x: e.target.value })} /><input aria-label="Y metres" className="input" placeholder="y (m)" type="number" value={nl.y} onChange={(e) => setNl({ ...nl, y: e.target.value })} /></div>
          <button className="btn-primary col-span-2">Add location</button></form>
        <p className="mb-2 text-xs text-slate-500">x / y are map coordinates in metres; the matcher uses them to score location proximity.</p>
        {locs.loading ? <Spinner /> : <ul className="divide-y divide-slate-100 dark:divide-navy-800">{locs.data?.items.map((l) => <li key={l.id} className="flex items-center justify-between py-2 text-sm"><span className={l.is_active ? '' : 'text-slate-400 line-through'}>{l.name} <span className="text-xs text-slate-500">{l.zone}</span></span><button className="btn-outline !py-1" onClick={() => toggle('/admin/locations', l, locs.reload)}>{l.is_active ? 'Disable' : 'Enable'}</button></li>)}</ul>}</section>
    </div>
  )
}

function SettingsTab() {
  const toast = useToast()
  const { data, loading, error, reload } = useAsync(() => api.get('/admin/settings'), [])
  const [s, setS] = useState(null)
  const [errs, setErrs] = useState({})
  const cur = s || data?.settings
  if (loading) return <Spinner />
  if (error) return <ErrorBox error={error} />
  const set = (k, v) => setS({ ...cur, [k]: v })
  const save = async (e) => {
    e.preventDefault(); setErrs({})
    try { await api.put('/admin/settings', cur); toast('Settings saved. Use “Recompute matches” to apply new weights to existing reports.'); reload(); setS(null) } catch (x) { setErrs(x.fields || {}); toast(x.message, 'error') }
  }
  const rematch = async () => { try { const d = await api.post('/admin/rematch'); toast(d.message) } catch (x) { toast(x.message, 'error') } }
  const wsum = Object.values(cur.match_weights).reduce((a, b) => a + Number(b), 0) || 1
  return (
    <form onSubmit={save} className="space-y-6">
      <section className="card p-4"><h2 className="text-base">Matching weights</h2><p className="mb-3 text-xs text-slate-500">Relative importance of each signal (normalised automatically). Missing signals, e.g. no photo, are excluded and the others re-scaled.</p>
        {errs.match_weights && <p role="alert" className="mb-2 text-sm text-red-600">{errs.match_weights}</p>}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(cur.match_weights).map(([k, v]) => (
          <div key={k}><label className="label capitalize" htmlFor={`w-${k}`}>{k} — {Math.round((100 * v) / wsum)}%</label><input id={`w-${k}`} type="range" min="0" max="1" step="0.05" className="w-full accent-teal-600" value={v} onChange={(e) => set('match_weights', { ...cur.match_weights, [k]: +e.target.value })} /></div>))}</div></section>
      <section className="card grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-4"><div className="col-span-full"><h2 className="text-base">Thresholds &amp; limits</h2></div>
        <Input id="ms" label="Minimum score to store/show (0–100)" type="number" value={cur.match_min_score} onChange={(e) => set('match_min_score', e.target.value)} error={errs.match_min_score} />
        <Input id="mn" label="Notify owner at score ≥" type="number" value={cur.match_notify_score} onChange={(e) => set('match_notify_score', e.target.value)} error={errs.match_notify_score} />
        <Input id="mm" label="Max matches per report" type="number" value={cur.match_max_results} onChange={(e) => set('match_max_results', e.target.value)} error={errs.match_max_results} />
        <Input id="ma" label="Max claim attempts per item" type="number" value={cur.max_claim_attempts} onChange={(e) => set('max_claim_attempts', e.target.value)} error={errs.max_claim_attempts} /></section>
      <section className="card grid gap-4 p-4 sm:grid-cols-2"><div className="col-span-full"><h2 className="text-base">University &amp; moderation</h2></div>
        <Input id="un" label="University name" value={cur.university_name} onChange={(e) => set('university_name', e.target.value)} />
        <Input id="sp" label="Student ID pattern (regex)" value={cur.student_id_pattern} onChange={(e) => set('student_id_pattern', e.target.value)} error={errs.student_id_pattern} />
        <Input id="dp" label="Departments (comma separated)" value={cur.departments.join(', ')} onChange={(e) => set('departments', e.target.value.split(',').map((x) => x.trim()).filter(Boolean))} />
        <Input id="bk" label="Moderation keywords (reports containing these are held for review)" value={cur.blocked_keywords.join(', ')} onChange={(e) => set('blocked_keywords', e.target.value.split(',').map((x) => x.trim()).filter(Boolean))} /></section>
      <div className="flex gap-2"><button className="btn-primary">Save settings</button><button type="button" className="btn-outline" onClick={rematch}>Recompute matches</button></div>
    </form>
  )
}

function AuditTab() {
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const { data, loading, error, reload } = useAsync(() => api.get('/admin/audit' + qs({ page, action })), [page, action])
  return (
    <>
      <div className="mb-4 w-64"><Select id="aa" label="Action prefix" placeholder="All actions" options={['user', 'lost', 'found', 'claim', 'handover', 'admin', 'report'].map((a) => ({ value: a, label: a }))} value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} /></div>
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead><tr><th className="th">When</th><th className="th">User</th><th className="th">Action</th><th className="th">Entity</th><th className="th">Details</th><th className="th">IP</th></tr></thead>
          <tbody className="divide-y divide-slate-100 dark:divide-navy-800">{data.items.map((l) => <tr key={l.id}><td className="td whitespace-nowrap">{fmtDateTime(l.created_at)}</td><td className="td">{l.user || '—'}</td><td className="td font-mono text-xs">{l.action}</td><td className="td">{l.entity_type} {l.entity_id ?? ''}</td><td className="td max-w-xs truncate font-mono text-xs" title={JSON.stringify(l.details)}>{l.details ? JSON.stringify(l.details) : ''}</td><td className="td">{l.ip_address}</td></tr>)}</tbody></table></div>)}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </>
  )
}

export default function Manage() {
  const { user, can } = useAuth()
  const tabs = [['claims', 'Claims', true], ['found', 'Found items', true], ['lost', 'Lost reports', true], ['catalog', 'Categories & locations', can('settings.manage')], ['settings', 'Matching & rules', can('settings.manage')], ['audit', 'Audit log', can('audit.view')]].filter((t) => t[2])
  const [tab, setTab] = useState('claims')
  return (
    <>
      <PageHeader title="Items, claims & system rules" subtitle={user.role === 'admin' ? 'Moderate reports, verify ownership and configure the system.' : 'Review claims and moderate item reports.'} />
      <div role="tablist" className="mb-5 flex flex-wrap gap-2">{tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'btn-primary' : 'btn-outline'} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'claims' && <ClaimsTab />}{tab === 'found' && <ItemsTab kind="found" />}{tab === 'lost' && <ItemsTab kind="lost" />}
      {tab === 'catalog' && <CatalogTab />}{tab === 'settings' && <SettingsTab />}{tab === 'audit' && <AuditTab />}
    </>
  )
}
