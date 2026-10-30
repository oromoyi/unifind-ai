import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync, useToast } from '../lib/hooks'
import { ErrorBox, Input, PageHeader, Select, Spinner, Textarea } from '../components/ui'
import { getItemPhoto } from '../lib/format'

export default function ClaimForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const item = useAsync(() => api.get(`/found/${id}`), [id])
  const mine = useAsync(() => api.get('/lost?status=open&per_page=50'), [])
  const [v, setV] = useState({ description: '', verification_answer: '', lost_report_id: '' })
  const [errs, setErrs] = useState({})
  const [top, setTop] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErrs({}); setTop('')
    try { const d = await api.post(`/found/${id}/claims`, { ...v, lost_report_id: v.lost_report_id || undefined }); toast(d.message); nav('/app/my-claims') }
    catch (x) { setErrs(x.fields || {}); setTop(x.message) } finally { setBusy(false) }
  }
  if (item.loading) return <Spinner />
  if (item.error) return <ErrorBox error={item.error} />
  const it = item.data.item
  return (
    <>
      <PageHeader title="Submit an ownership claim" subtitle="Your answers are compared privately; they are never shown publicly." />
      <div className="grid gap-6 lg:grid-cols-3">
        <aside className="card p-4 lg:col-span-1">
          <img src={getItemPhoto(it)} alt={it.title} className="mb-3 aspect-[4/3] w-full rounded-lg object-cover" />
          <h2 className="text-base">{it.title}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{it.description}</p>
          <p className="mt-2 text-xs text-slate-500">Found at {it.location}</p>
        </aside>
        <form onSubmit={submit} className="card space-y-4 p-5 lg:col-span-2" noValidate>
          {top && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{top}</div>}
          {it.verification_question && <Input id="ans" label={`Verification question: ${it.verification_question}`} value={v.verification_answer} onChange={(e) => setV({ ...v, verification_answer: e.target.value })} error={errs.verification_answer} autoComplete="off" hint="Answer from memory. You have a limited number of attempts per item." />}
          <Textarea id="desc" label="Describe the item in detail" hint="Unique marks, contents, accessories, serial number, when and where you lost it — details not visible in the public listing." value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} error={errs.description} rows={6} />
          <Select id="lost" label="Link one of your lost reports (optional)" placeholder="None" options={(mine.data?.items || []).map((r) => ({ value: r.id, label: r.title }))} value={v.lost_report_id} onChange={(e) => setV({ ...v, lost_report_id: e.target.value })} />
          <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">False claims are recorded in the audit log and may be reported to the university disciplinary committee.</p>
          <div className="flex gap-2"><button className="btn-accent" disabled={busy}>{busy ? 'Submitting…' : 'Submit claim'}</button><Link to={`/items/${id}`} className="btn-outline">Cancel</Link></div>
        </form>
      </div>
    </>
  )
}
