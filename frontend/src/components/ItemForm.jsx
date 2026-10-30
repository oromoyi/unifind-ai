import { useState } from 'react'
import { api } from '../lib/api'
import { useAsync, useToast } from '../lib/hooks'
import { Input, Select, Spinner, Textarea } from './ui'
import { Link } from 'react-router-dom'
import AiImageAnalyzer from './AiImageAnalyzer'

const today = () => new Date().toISOString().slice(0, 10)

/** Shared lost/found report form. kind: 'lost' | 'found'. */
export default function ItemForm({ kind, onDone, staff }) {
  const toast = useToast()
  const meta = useAsync(() => api.get('/meta'), [])
  const [v, setV] = useState({ title: '', category_id: '', description: '', color: '', brand: '', location_id: '', date: today(), distinguishing_features: '', private_details: '', storage_location: '', verification_question: '', verification_answer: '' })
  const [files, setFiles] = useState([])
  const [errs, setErrs] = useState({})
  const [top, setTop] = useState('')
  const [dups, setDups] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value })

  // AI image auto-fill handler: auto-fills fields AND attaches the photo to the item
  const handleAiResult = (details, file) => {
    setV(prev => ({
      ...prev,
      title: details.title || prev.title,
      color: details.color || prev.color,
      brand: details.brand || prev.brand,
      description: details.description || prev.description,
      ...(details.category_id ? { category_id: String(details.category_id) } : {}),
    }))
    if (file) {
      setFiles(prev => {
        const exists = prev.some(f => f.name === file.name && f.size === file.size)
        return exists ? prev : [file, ...prev].slice(0, 4)
      })
      toast('Photo attached to item profile and details auto-filled!', 'success')
    }
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const submit = async (confirm = false) => {
    setErrs({}); setTop(''); setBusy(true)
    const fd = new FormData()
    Object.entries(v).forEach(([k, val]) => val !== '' && fd.append(k, val))
    if (confirm) fd.append('confirm_duplicate', '1')
    files.forEach((f) => fd.append('images', f))
    try {
      const d = await api.post(kind === 'lost' ? '/lost' : '/found', fd)
      toast(kind === 'lost' ? 'Lost item reported. Checking for matches…' : (d.item.status === 'pending' ? 'Submitted for officer review.' : 'Item registered and published.'))
      onDone(d)
    } catch (x) {
      if (x.status === 409 && x.data.duplicate) setDups(x.data.duplicates)
      else { setErrs(x.fields || {}); setTop(x.message) }
    } finally { setBusy(false) }
  }
  if (meta.loading) return <Spinner />
  const word = kind === 'lost' ? 'lost' : 'found'
  return (
    <form className="card space-y-5 p-5" onSubmit={(e) => { e.preventDefault(); submit(false) }} noValidate>
      {top && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{top}</div>}
      {/* AI Image Analyzer */}
      <AiImageAnalyzer onResult={handleAiResult} />
      {dups && (
        <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
          <p className="font-medium">A very similar report already exists:</p>
          <ul className="mt-1 list-disc pl-5">{dups.map((d) => <li key={d.id}>{d.title} ({d.similarity}% similar)</li>)}</ul>
          <div className="mt-3 flex gap-2"><button type="button" className="btn-outline" onClick={() => setDups(null)}>Review my entry</button><button type="button" className="btn-accent" disabled={busy} onClick={() => submit(true)}>It is different — submit anyway</button></div>
        </div>)}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="md:col-span-2"><Input id="title" label="Short title" placeholder={kind === 'lost' ? 'e.g. Black Samsung phone' : 'e.g. Navy backpack'} value={v.title} onChange={set('title')} error={errs.title} maxLength={150} /></div>
        <Select id="cat" label="Category" placeholder="Choose…" options={meta.data.categories} value={v.category_id} onChange={set('category_id')} error={errs.category_id} />
        <Select id="loc" label={`Where was it ${word}?`} placeholder="Choose campus location…" options={meta.data.locations} value={v.location_id} onChange={set('location_id')} error={errs.location_id} />
        <Input id="date" label={`Date ${word}`} type="date" max={today()} value={v.date} onChange={set('date')} error={errs.date} />
        <Input id="color" label="Main colour" placeholder="e.g. navy blue" value={v.color} onChange={set('color')} />
        <Input id="brand" label="Brand / make" placeholder="e.g. Samsung" value={v.brand} onChange={set('brand')} />
        <div className="md:col-span-2"><Textarea id="desc" label={kind === 'lost' ? 'Description' : 'Public description'} hint={kind === 'found' ? 'Shown publicly. Do NOT include secret details such as serial numbers or names inside.' : 'Size, condition, contents, anything that helps recognise it.'} value={v.description} onChange={set('description')} error={errs.description} /></div>
        {kind === 'lost' && <div className="md:col-span-2"><Textarea id="feat" label="Distinguishing features (optional)" rows={2} value={v.distinguishing_features} onChange={set('distinguishing_features')} /></div>}
      </div>
      {kind === 'found' && (
        <fieldset className="rounded-lg border border-teal-300 bg-teal-50/60 p-4 dark:border-teal-800 dark:bg-teal-950/20">
          <legend className="px-2 text-sm font-semibold text-teal-800 dark:text-teal-200">🔒 Private verification (never shown publicly)</legend>
          <div className="grid gap-4 md:grid-cols-2">
            <Input id="vq" label="Verification question" placeholder="e.g. What is the lock-screen picture?" value={v.verification_question} onChange={set('verification_question')} />
            <Input id="va" label="Correct answer" value={v.verification_answer} onChange={set('verification_answer')} error={errs.verification_answer} hint="Stored only as a salted hash." />
            <div className="md:col-span-2"><Textarea id="priv" label="Private identifying details (optional)" rows={2} hint="Visible only to officers/administrators reviewing a claim." value={v.private_details} onChange={set('private_details')} /></div>
            {staff && <div className="md:col-span-2"><Input id="store" label="Storage location" placeholder="e.g. Security office, shelf B2" value={v.storage_location} onChange={set('storage_location')} /></div>}
          </div>
        </fieldset>)}
      <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 dark:border-navy-800 dark:bg-navy-900/40">
        <label className="label font-medium" htmlFor="imgs">Item photos (up to 4, JPG/PNG/WEBP, max 5 MB each)</label>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">The first photo will be used as the item's main profile picture across the platform.</p>
        <input id="imgs" type="file" accept="image/jpeg,image/png,image/webp" multiple className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-navy-800 file:px-3 file:py-2 file:text-white" onChange={(e) => setFiles(prev => [...prev, ...e.target.files].slice(0, 4))} />
        {errs.images && <p role="alert" className="mt-1 text-xs text-red-600">{errs.images}</p>}
        {files.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3">
            {files.map((f, i) => (
              <div key={f.name + f.size + i} className="group relative">
                <img src={URL.createObjectURL(f)} alt={`Preview of ${f.name}`} className="h-20 w-20 rounded-lg border-2 border-teal-500 object-cover shadow-sm" />
                {i === 0 && (
                  <span className="absolute bottom-1 left-1 rounded bg-teal-600 px-1 text-[9px] font-bold text-white shadow">
                    Profile
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => removeFile(i)}
                  className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white shadow hover:bg-red-700"
                  title="Remove photo"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="flex gap-2"><button className="btn-primary" disabled={busy}>{busy ? 'Submitting…' : `Submit ${word} item`}</button><Link to="/app" className="btn-outline">Cancel</Link></div>
    </form>
  )
}
