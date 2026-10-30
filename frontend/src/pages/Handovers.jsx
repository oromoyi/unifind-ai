import { useState } from 'react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync, useToast } from '../lib/hooks'
import { EmptyState, ErrorBox, Input, Modal, PageHeader, Pagination, Spinner, StatusBadge, Textarea } from '../components/ui'
import { fmtDateTime, getItemPhoto, exportToCsv } from '../lib/format'

function Feedback({ id, onDone }) {
  const toast = useToast()
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const send = async () => { try { await api.post(`/handovers/${id}/feedback`, { rating, comment }); toast('Thank you for your feedback!'); onDone() } catch (e) { toast(e.message, 'error') } }
  return (
    <div className="mt-3 rounded-lg bg-slate-50 p-3 dark:bg-navy-800">
      <p className="text-sm font-medium">How was the recovery experience?</p>
      <div className="mt-1 flex items-center gap-2"><label className="sr-only" htmlFor={`r${id}`}>Rating</label>
        <select id={`r${id}`} className="input w-24" value={rating} onChange={(e) => setRating(+e.target.value)}>{[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} ★</option>)}</select>
        <input className="input" aria-label="Comment" placeholder="Optional comment" value={comment} onChange={(e) => setComment(e.target.value)} />
        <button className="btn-primary" onClick={send}>Send</button></div>
    </div>
  )
}

export default function Handovers() {
  const { user, can } = useAuth()
  const staff = can('handovers.manage')
  const toast = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState(staff ? 'ready' : '')
  const { data, loading, error, reload } = useAsync(() => api.get(`/handovers?page=${page}${status ? `&status=${status}` : ''}`), [page, status])
  const [target, setTarget] = useState(null)
  const [form, setForm] = useState({ reference_code: '', id_verified: false, notes: '' })
  const [err, setErr] = useState({})
  const [busy, setBusy] = useState(false)

  const complete = async (e) => {
    e.preventDefault(); setBusy(true); setErr({})
    try { await api.post(`/handovers/${target.id}/complete`, form); toast('Handover recorded. Item marked as returned.'); setTarget(null); setForm({ reference_code: '', id_verified: false, notes: '' }); reload() }
    catch (x) { setErr(x.fields || { reference_code: x.message }) } finally { setBusy(false) }
  }
  const receipt = (h) => api.download(`/handovers/${h.id}/receipt`, `receipt-${h.id}.pdf`).catch((e) => toast(e.message, 'error'))

  return (
    <>
      <PageHeader title={staff ? 'Secure item handover' : 'My handovers'} subtitle={staff ? 'Verify ID, ask the claimant for their handover code, then record the physical return.' : 'Show your ID and the code below at the Lost-and-Found office.'}
        actions={
          <div className="flex items-center gap-2">
            {data?.items?.length > 0 && (
              <button 
                className="btn-outline text-xs" 
                onClick={() => exportToCsv('handovers', data.items, [
                  { header: 'ID', key: 'id' },
                  { header: 'Item', key: 'item_title' },
                  { header: 'Status', key: 'status' },
                  { header: 'Claimant', key: (r) => r.claimant?.name || '' },
                  { header: 'Code', key: 'reference_code' },
                  { header: 'Completed At', key: 'completed_at' }
                ])}
              >
                📥 Export CSV
              </button>
            )}
            {staff && (
              <select aria-label="Status filter" className="input" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
                <option value="ready">Ready for collection</option>
                <option value="completed">Completed</option>
                <option value="">All</option>
              </select>
            )}
          </div>
        } />
      {loading ? <Spinner /> : error ? <ErrorBox error={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No handovers" text={staff ? 'Approved claims awaiting collection appear here.' : 'When an officer approves a claim, your collection code appears here.'} />
        : <><ul className="space-y-3">{data.items.map((h) => (
          <li key={h.id} className="card p-4">
            <div className="flex flex-wrap items-center gap-4">
              <img src={h.item_image || getItemPhoto({ title: h.item_title })} alt="" className="h-16 w-16 rounded-lg object-cover" />
              <div className="min-w-0 flex-1">
                <p className="font-medium">{h.item_title}</p>
                {staff ? <p className="text-sm text-slate-600 dark:text-slate-400">Claimant: {h.claimant.name}{h.claimant.student_id ? ` (${h.claimant.student_id})` : ''}</p>
                  : <p className="text-sm text-slate-600 dark:text-slate-400">{h.storage_location ? `Collect from: ${h.storage_location}` : 'Collect from the Lost-and-Found office'}</p>}
                {h.completed_at && <p className="text-xs text-slate-500">Completed {fmtDateTime(h.completed_at)}{h.officer ? ` by ${h.officer}` : ''}</p>}
              </div>
              <StatusBadge status={h.status} />
              {!staff && h.status === 'ready' && (
                <div className="flex flex-col sm:flex-row items-center gap-3 rounded-xl border-2 border-teal-500/40 bg-teal-50/50 p-3 dark:bg-teal-950/20">
                  <div className="flex flex-col items-center justify-center rounded-lg bg-white p-2 shadow-sm dark:bg-navy-900 border border-teal-200 dark:border-teal-800">
                    <img 
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=${encodeURIComponent(h.reference_code)}`} 
                      alt={`QR for ${h.reference_code}`} 
                      className="h-20 w-20 rounded"
                    />
                    <span className="mt-1 text-[10px] font-semibold tracking-wider text-teal-800 dark:text-teal-300 uppercase">Scan to Verify</span>
                  </div>
                  <div className="text-center sm:text-left">
                    <p className="text-xs text-slate-500">Handover Code</p>
                    <p className="font-mono text-xl font-bold tracking-widest text-navy-900 dark:text-teal-300" aria-label={`Handover code ${h.reference_code}`}>{h.reference_code}</p>
                    <p className="mt-1 text-xs text-slate-500 max-w-[180px]">Present this QR code or 6-digit code to the desk officer.</p>
                  </div>
                </div>
              )}
              {staff && h.status === 'ready' && <button className="btn-accent" onClick={() => setTarget(h)}>Record handover</button>}
              {h.status === 'completed' && <button className="btn-outline" onClick={() => receipt(h)}>Download receipt (PDF)</button>}
            </div>
            {!staff && h.status === 'completed' && <Feedback id={h.id} onDone={reload} />}
          </li>))}</ul><Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} /></>}
      <Modal open={!!target} title="Complete handover" onClose={() => setTarget(null)}>
        <form onSubmit={complete} className="space-y-4" noValidate>
          <p className="text-sm">Item: <strong>{target?.item_title}</strong><br />Claimant: <strong>{target?.claimant?.name}</strong></p>
          <Input id="code" label="Handover code (from claimant)" value={form.reference_code} onChange={(e) => setForm({ ...form, reference_code: e.target.value })} error={err.reference_code} autoComplete="off" className="uppercase" />
          <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={form.id_verified} onChange={(e) => setForm({ ...form, id_verified: e.target.checked })} />I checked the claimant’s photo ID against the claim.</label>
          {err.id_verified && <p role="alert" className="text-xs text-red-600">Please confirm the ID check.</p>}
          <Textarea id="notes" label="Notes (optional)" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          <div className="flex justify-end gap-2"><button type="button" className="btn-outline" onClick={() => setTarget(null)}>Cancel</button><button className="btn-accent" disabled={busy}>{busy ? 'Saving…' : 'Confirm return'}</button></div>
        </form>
      </Modal>
    </>
  )
}
