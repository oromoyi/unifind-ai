import { useState } from 'react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useToast } from '../lib/hooks'
import { Input, PageHeader } from '../components/ui'

export default function Profile() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const [p, setP] = useState({ full_name: user.full_name, department: user.department || '', phone: user.phone || '' })
  const [pw, setPw] = useState({ current_password: '', new_password: '' })
  const [pwErr, setPwErr] = useState({})
  const save = async (e) => { e.preventDefault(); try { const d = await api.put('/auth/me', p); setUser(d.user); toast('Profile updated.') } catch (x) { toast(x.message, 'error') } }
  const change = async (e) => {
    e.preventDefault(); setPwErr({})
    try { await api.post('/auth/change-password', pw); toast('Password changed.'); setPw({ current_password: '', new_password: '' }) } catch (x) { setPwErr(x.fields || { current_password: x.message }) }
  }
  return (
    <>
      <PageHeader title="Profile & security" subtitle={`${user.email} · ${user.role}`} />
      <div className="grid gap-6 md:grid-cols-2">
        <form onSubmit={save} className="card space-y-4 p-5"><h2 className="text-base">Details</h2>
          <Input id="n" label="Full name" value={p.full_name} onChange={(e) => setP({ ...p, full_name: e.target.value })} />
          <Input id="d" label="Department" value={p.department} onChange={(e) => setP({ ...p, department: e.target.value })} />
          <Input id="ph" label="Phone (private)" value={p.phone} onChange={(e) => setP({ ...p, phone: e.target.value })} />
          <button className="btn-primary">Save changes</button></form>
        <form onSubmit={change} className="card space-y-4 p-5"><h2 className="text-base">Change password</h2>
          <Input id="cp" type="password" label="Current password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} error={pwErr.current_password} />
          <Input id="np" type="password" label="New password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} error={pwErr.new_password} />
          <button className="btn-primary">Update password</button></form>
      </div>
    </>
  )
}
