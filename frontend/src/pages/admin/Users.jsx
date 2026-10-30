import { useState } from 'react'
import { api, qs } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { useAsync, useDebounced, useToast } from '../../lib/hooks'
import { EmptyState, ErrorBox, Input, Modal, PageHeader, Pagination, Select, Spinner } from '../../components/ui'
import { fmtDate } from '../../lib/format'

const ROLES = ['student', 'finder', 'officer', 'admin']

function UsersTab() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounced(q)
  const { data, loading, error, reload } = useAsync(() => api.get('/admin/users' + qs({ q: dq, role, page })), [dq, role, page])
  const [open, setOpen] = useState(false)
  const [nu, setNu] = useState({ full_name: '', email: '', password: '', role: 'officer' })
  const [errs, setErrs] = useState({})
  const patch = async (u, body) => { try { await api.put(`/admin/users/${u.id}`, body); toast('User updated.'); reload() } catch (e) { toast(e.message, 'error'); reload() } }
  const create = async (e) => {
    e.preventDefault(); setErrs({})
    try { await api.post('/admin/users', nu); toast('User created.'); setOpen(false); setNu({ full_name: '', email: '', password: '', role: 'officer' }); reload() } catch (x) { setErrs(x.fields || {}) }
  }
  return (
    <>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="min-w-[14rem] flex-1"><label className="label" htmlFor="uq">Search name, email or student ID</label><input id="uq" className="input" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></div>
        <div className="w-40"><Select id="ur" label="Role" placeholder="All roles" options={ROLES.map((r) => ({ value: r, label: r }))} value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }} /></div>
        <button className="btn-primary" onClick={() => setOpen(true)}>+ Create staff account</button>
      </div>
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No users found" /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead><tr><th className="th">Name</th><th className="th">Email</th><th className="th">Role</th><th className="th">Joined</th><th className="th">Status</th><th className="th">Actions</th></tr></thead>
          <tbody className="divide-y divide-slate-100 dark:divide-navy-800">{data.items.map((u) => (
            <tr key={u.id}><td className="td font-medium">{u.full_name}{u.student_id && <span className="block text-xs text-slate-500">{u.student_id}</span>}</td><td className="td">{u.email}</td>
              <td className="td"><select aria-label={`Role for ${u.full_name}`} className="input !py-1" value={u.role} disabled={u.id === me.id} onChange={(e) => patch(u, { role: e.target.value })}>{ROLES.map((r) => <option key={r}>{r}</option>)}</select></td>
              <td className="td">{fmtDate(u.created_at)}</td><td className="td">{u.is_active ? <span className="text-emerald-600">Active</span> : <span className="text-red-600">Disabled</span>}</td>
              <td className="td"><button className="btn-outline !py-1" disabled={u.id === me.id} onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? 'Deactivate' : 'Activate'}</button>{' '}<button className="btn-outline !py-1" onClick={() => patch(u, { unlock: true })}>Unlock</button></td></tr>))}</tbody></table></div>)}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      <Modal open={open} title="Create staff account" onClose={() => setOpen(false)}>
        <form onSubmit={create} className="space-y-3" noValidate>
          <Input id="cn" label="Full name" value={nu.full_name} onChange={(e) => setNu({ ...nu, full_name: e.target.value })} error={errs.full_name} />
          <Input id="ce" label="Email" type="email" value={nu.email} onChange={(e) => setNu({ ...nu, email: e.target.value })} error={errs.email} />
          <Input id="cpw" label="Temporary password" type="password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} error={errs.password} />
          <Select id="cr" label="Role" options={ROLES.map((r) => ({ value: r, label: r }))} value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })} error={errs.role} />
          <div className="flex justify-end gap-2"><button type="button" className="btn-outline" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary">Create</button></div>
        </form>
      </Modal>
    </>
  )
}

function RolesTab() {
  const toast = useToast()
  const { data, loading, error, reload } = useAsync(() => api.get('/admin/roles'), [])
  const [draft, setDraft] = useState({})
  if (loading) return <Spinner />
  if (error) return <ErrorBox error={error} />
  const current = (r) => draft[r.id] ?? r.permissions
  const toggle = (r, code) => { const cur = current(r); setDraft({ ...draft, [r.id]: cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code] }) }
  const save = async (r) => { try { await api.put(`/admin/roles/${r.id}/permissions`, { permissions: current(r) }); toast(`Permissions saved for ${r.name}.`); setDraft({ ...draft, [r.id]: undefined }); reload() } catch (e) { toast(e.message, 'error') } }
  return (
    <div className="card overflow-x-auto"><table className="w-full"><thead><tr><th className="th">Permission</th>{data.roles.map((r) => <th key={r.id} className="th text-center">{r.name}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-100 dark:divide-navy-800">{data.permissions.map((p) => (
        <tr key={p.code}><td className="td"><span className="font-mono text-xs">{p.code}</span><span className="block text-xs text-slate-500">{p.description}</span></td>
          {data.roles.map((r) => <td key={r.id} className="td text-center"><input type="checkbox" aria-label={`${r.name} can ${p.code}`} checked={current(r).includes(p.code)} disabled={r.name === 'admin'} onChange={() => toggle(r, p.code)} /></td>)}</tr>))}
        <tr><td className="td" />{data.roles.map((r) => <td key={r.id} className="td text-center">{r.name !== 'admin' && draft[r.id] && <button className="btn-primary !py-1" onClick={() => save(r)}>Save</button>}</td>)}</tr></tbody></table></div>
  )
}

export default function AdminUsers() {
  const [tab, setTab] = useState('users')
  return (
    <>
      <PageHeader title="Users & role permissions" subtitle="Staff accounts can only be created here; public registration is limited to students and finders." />
      <div role="tablist" className="mb-4 flex gap-2">{[['users', 'Users'], ['roles', 'Role permissions']].map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={tab === k ? 'btn-primary' : 'btn-outline'}>{l}</button>)}</div>
      {tab === 'users' ? <UsersTab /> : <RolesTab />}
    </>
  )
}
