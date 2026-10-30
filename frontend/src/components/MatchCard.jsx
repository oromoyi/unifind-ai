import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { getItemPhoto } from '../lib/format'
import { ScoreBar, StatusBadge } from './ui'

function AiExplainButton({ matchId }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  const explain = async () => {
    if (text) { setOpen(o => !o); return }
    setBusy(true)
    try {
      const d = await api.post('/ai/explain-match', { match_id: matchId })
      setText(d.explanation)
      setOpen(true)
    } catch (e) {
      setText(e.message || 'Could not generate explanation.')
      setOpen(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-2">
      <button
        onClick={explain}
        disabled={busy}
        className="flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-800 hover:bg-teal-100 dark:border-teal-700 dark:bg-teal-950/30 dark:text-teal-300 dark:hover:bg-teal-950/50 disabled:opacity-50 transition"
      >
        {busy
          ? <><span className="h-3 w-3 animate-spin rounded-full border border-teal-500 border-t-transparent" /> Generating…</>
          : <><span className="font-bold">AI</span> {open ? 'Hide' : 'Explain this match'}</>
        }
      </button>
      {open && text && (
        <div className="mt-2 rounded-lg border border-teal-200 bg-teal-50/80 px-3 py-2.5 text-sm text-teal-900 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-100">
          <span className="mr-1.5 inline-block rounded bg-teal-600 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">AI</span>
          {text}
        </div>
      )}
    </div>
  )
}

export default function MatchCard({ m }) {
  const it = m.found_item
  const photo = getItemPhoto(it)
  return (
    <article className="card animate-fade-up overflow-hidden md:flex">
      <div className="h-44 shrink-0 bg-slate-100 overflow-hidden md:h-auto md:w-48 dark:bg-navy-800">
        <img
          src={photo}
          alt={it.title}
          className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
          onError={(e) => {
            const fallback = getItemPhoto({ title: it.title, category: it.category })
            if (e.target.src !== fallback) e.target.src = fallback
          }}
        />
      </div>
      <div className="flex-1 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-base">{it.title}</h3><ScoreBar score={m.score} /></div>
        {m.lost_report && <p className="text-xs text-slate-500">For your report: {m.lost_report.title}</p>}
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{it.description}</p>
        <p className="mt-2 rounded-md bg-teal-50 px-3 py-2 text-sm text-teal-900 dark:bg-teal-950/40 dark:text-teal-100"><strong>Why: </strong>{m.explanation}</p>
        {/* AI-powered richer explanation */}
        <AiExplainButton matchId={m.id} />
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer text-slate-500">Score breakdown</summary>
          <table className="mt-2 w-full"><tbody>
            {Object.entries(m.breakdown).map(([k, b]) => (
              <tr key={k}><td className="py-0.5 pr-2">{b.label}</td>
                <td className="w-1/2"><div className="h-1.5 rounded bg-slate-200 dark:bg-navy-700"><div className="h-full rounded bg-teal-500" style={{ width: `${(b.value ?? 0) * 100}%` }} /></div></td>
                <td className="pl-2 text-right text-slate-500">{b.value === null ? 'n/a (not used)' : `${Math.round(b.value * 100)}% → ${b.points} pts`}</td></tr>))}
          </tbody></table>
        </details>
        <div className="mt-3 flex items-center gap-3"><StatusBadge status={it.status} /><Link className="btn-primary" to={`/items/${it.id}`}>View item &amp; claim</Link></div>
      </div>
    </article>
  )
}
