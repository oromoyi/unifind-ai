import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useAsync, useToast } from '../lib/hooks'
import { api } from '../lib/api'
import { Input, Select } from '../components/ui'

function Shell({ title, subtitle, children }) {
  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-12">
      <div className="card animate-fade-up p-6"><h1 className="text-2xl">{title}</h1><p className="mb-5 mt-1 text-sm text-slate-500">{subtitle}</p>{children}</div>
    </div>
  )
}

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const toast = useToast()
  const [v, setV] = useState({ email: '', password: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await login(v.email, v.password); toast('Welcome back!'); nav(loc.state?.from || '/app') }
    catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  const quickLogin = async (email, password) => {
    setV({ email, password })
    setErr('')
    setBusy(true)
    try {
      await login(email, password)
      toast('Signed in as demo account!')
      nav(loc.state?.from || '/app')
    } catch (x) {
      setErr(x.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title="Log in" subtitle="Access your reports, claims and notifications.">
      <div className="mb-5 rounded-xl border border-teal-200 bg-teal-50/60 p-3.5 dark:border-teal-800 dark:bg-teal-950/30">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-teal-800 dark:text-teal-200">
            ⚡ 1-Click Demo Login
          </p>
          <span className="text-[10px] bg-teal-200 text-teal-900 dark:bg-teal-800 dark:text-teal-100 px-2 py-0.5 rounded-full font-medium">Defense Ready</span>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 mb-2.5">
          Select any role to test the platform instantly:
        </p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => quickLogin('student1@unifind.test', 'Student@12345')}
            className="flex items-center gap-1.5 rounded-lg border border-teal-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 shadow-sm hover:bg-teal-100/50 hover:border-teal-500 transition dark:border-teal-700 dark:bg-navy-900 dark:text-white"
          >
            <span>🎓</span> <span className="font-semibold">Student</span>
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => quickLogin('finder1@unifind.test', 'Finder@12345')}
            className="flex items-center gap-1.5 rounded-lg border border-teal-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 shadow-sm hover:bg-teal-100/50 hover:border-teal-500 transition dark:border-teal-700 dark:bg-navy-900 dark:text-white"
          >
            <span>📦</span> <span className="font-semibold">Finder</span>
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => quickLogin('officer@unifind.test', 'Officer@12345')}
            className="flex items-center gap-1.5 rounded-lg border border-teal-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 shadow-sm hover:bg-teal-100/50 hover:border-teal-500 transition dark:border-teal-700 dark:bg-navy-900 dark:text-white"
          >
            <span>🛡️</span> <span className="font-semibold">Officer</span>
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => quickLogin('admin@unifind.test', 'Admin@12345')}
            className="flex items-center gap-1.5 rounded-lg border border-teal-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 shadow-sm hover:bg-teal-100/50 hover:border-teal-500 transition dark:border-teal-700 dark:bg-navy-900 dark:text-white"
          >
            <span>👑</span> <span className="font-semibold">Admin</span>
          </button>
        </div>
      </div>

      <form onSubmit={submit} className="space-y-4" noValidate>
        {err && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{err}</div>}
        <Input id="email" label="Email" type="email" autoComplete="email" required value={v.email} onChange={(e) => setV({ ...v, email: e.target.value })} />
        <Input id="password" label="Password" type="password" autoComplete="current-password" required value={v.password} onChange={(e) => setV({ ...v, password: e.target.value })} />
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Log in'}</button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-500">New here? <Link className="font-medium text-teal-700 dark:text-teal-300" to="/register">Create an account</Link></p>
    </Shell>
  )
}

export function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const toast = useToast()
  const meta = useAsync(() => api.get('/meta'), [])
  const [v, setV] = useState({ full_name: '', email: '', password: '', confirm_password: '', role: 'student', student_id: '', department: '', phone: '' })
  const [errs, setErrs] = useState({})
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setErrs({})
    const local = {}
    if (v.password !== v.confirm_password) local.confirm_password = 'Passwords do not match.'
    if (Object.keys(local).length) return setErrs(local)
    setBusy(true)
    try { await register(v); toast('Account created. Welcome to UniFind AI!'); nav('/app') }
    catch (x) { setErrs(x.fields || {}); setErr(Object.keys(x.fields || {}).length ? '' : x.message) } finally { setBusy(false) }
  }
  return (
    <Shell title="Create your account" subtitle={`Join ${meta.data?.university_name || 'your university'}'s lost-and-found community.`}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {err && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{err}</div>}
        <Select id="role" label="I am a…" options={[{ value: 'student', label: 'Student / staff member (report lost items, claim)' }, { value: 'finder', label: 'Finder (register items I found)' }]} value={v.role} onChange={set('role')} error={errs.role} />
        <Input id="full_name" label="Full name" autoComplete="name" value={v.full_name} onChange={set('full_name')} error={errs.full_name} />
        <Input id="email" label="Email" type="email" autoComplete="email" value={v.email} onChange={set('email')} error={errs.email} />
        {v.role === 'student' && <Input id="student_id" label="Student ID" placeholder="UGR/1234/15" value={v.student_id} onChange={set('student_id')} error={errs.student_id} hint="Format depends on your university (configurable by the administrator)." />}
        <Select id="dept" label="Department (optional)" placeholder="Select…" options={(meta.data?.departments || []).map((d) => ({ value: d, label: d }))} value={v.department} onChange={set('department')} />
        <Input id="phone" label="Phone (optional, kept private)" type="tel" autoComplete="tel" value={v.phone} onChange={set('phone')} />
        <Input id="password" label="Password" type="password" autoComplete="new-password" value={v.password} onChange={set('password')} error={errs.password} hint="At least 8 characters with letters and digits." />
        <Input id="confirm_password" label="Confirm password" type="password" autoComplete="new-password" value={v.confirm_password} onChange={set('confirm_password')} error={errs.confirm_password} />
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-500">Already registered? <Link className="font-medium text-teal-700 dark:text-teal-300" to="/login">Log in</Link></p>
      <p className="mt-2 text-center text-xs text-slate-400">Officer and administrator accounts are created by an administrator only.</p>
    </Shell>
  )
}
