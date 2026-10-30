import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { ItemCard, ItemCardSkeleton, KpiCard, Spinner } from '../components/ui'

export default function Landing() {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const stats = useAsync(() => api.get('/stats/public'), [])
  const recent = useAsync(() => api.get('/found?per_page=4'), [])
  const s = stats.data
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-b from-navy-950 via-navy-900 to-navy-800 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-teal-500/10 via-transparent to-transparent pointer-events-none" />
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-24 relative z-10">
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-500/20 px-3 py-1 text-xs font-semibold text-teal-300 ring-1 ring-inset ring-teal-500/30">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-ping" />
              AI-Powered Campus Lost &amp; Found
            </span>
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-navy-200">
              Smart Matching · Secure QR Handover · Real-time Auditing
            </span>
          </div>

          <h1 className="max-w-3xl text-4xl font-extrabold tracking-tight !text-white md:text-5xl lg:text-6xl">
            Lost something on campus? <br />
            <span className="bg-gradient-to-r from-teal-300 to-teal-100 bg-clip-text text-transparent">
              Let’s get it back to you.
            </span>
          </h1>

          <p className="mt-4 max-w-2xl text-base md:text-lg text-navy-100 leading-relaxed">
            UniFind AI pairs TF-IDF multimodal signals to match lost reports with items found across campus. With built-in AI image classification, private verification questions, and secure cryptographic handover codes.
          </p>

          <form className="mt-8 flex max-w-2xl flex-col gap-2 sm:flex-row shadow-2xl rounded-xl p-1 bg-white/10 backdrop-blur-md border border-white/20" role="search" onSubmit={(e) => { e.preventDefault(); nav(`/browse?q=${encodeURIComponent(q)}`) }}>
            <label htmlFor="hero-q" className="sr-only">Search found items</label>
            <input id="hero-q" className="input flex-1 !border-none !bg-white !text-slate-900 focus:!ring-0 text-base py-3" placeholder="Search by keywords e.g. blue backpack, iPhone, silver key, glasses…" value={q} onChange={(e) => setQ(e.target.value)} />
            <button className="btn-accent px-8 py-3 text-base font-semibold shadow-md">Search Items</button>
          </form>

          <div className="mt-6 flex flex-wrap gap-3 items-center">
            <Link to="/register" className="btn bg-white text-navy-900 hover:bg-navy-50 font-semibold shadow-sm">
              📝 Report a lost item
            </Link>
            <Link to="/register" className="btn border border-white/30 text-white hover:bg-white/10">
              📦 I found something
            </Link>
            <Link to="/browse" className="text-sm font-medium text-teal-300 hover:text-white underline ml-2">
              Browse public catalog →
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto -mt-8 max-w-6xl px-4 relative z-20">
        {stats.loading ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[1, 2, 3, 4].map(n => <div key={n} className="card p-4 h-24 animate-pulse bg-white/80 dark:bg-navy-900/80" />)}
          </div>
        ) : s && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 shadow-lg rounded-xl">
            <KpiCard label="Items awaiting owners" value={s.available_found} />
            <KpiCard label="Lost reports filed" value={s.lost_reports} />
            <KpiCard label="Items returned" value={s.returned} accent />
            <KpiCard label="Recovery rate" value={`${s.recovery_rate}%`} hint="Live database audit" />
          </div>
        )}
      </section>

      {/* Feature Highlights Grid */}
      <section className="mx-auto max-w-6xl px-4 pt-16">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl md:text-3xl font-bold">Intelligent Campus Features</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Everything designed to make lost property recovery fast, fraud-resistant and accountable.</p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div className="card p-5 hover:border-teal-500/50 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 text-lg mb-3">
              🤖
            </div>
            <h3 className="text-base font-semibold">AI Assistant &amp; Vision</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Drop an item photo to instantly auto-detect title, category, and dominant colors using AI image analysis.
            </p>
          </div>

          <div className="card p-5 hover:border-teal-500/50 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 text-lg mb-3">
              ⚖️
            </div>
            <h3 className="text-base font-semibold">Multimodal Match Engine</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Combines TF-IDF NLP text vectors, color histogram distances, and campus location proximity to rank possible matches.
            </p>
          </div>

          <div className="card p-5 hover:border-teal-500/50 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 text-lg mb-3">
              🛡️
            </div>
            <h3 className="text-base font-semibold">Private Verification Claims</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Identifying details stay shielded. Claimants answer private questions verified by campus desk officers.
            </p>
          </div>

          <div className="card p-5 hover:border-teal-500/50 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 text-lg mb-3">
              📱
            </div>
            <h3 className="text-base font-semibold">QR Code Handover Receipts</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Claimants receive instant QR codes and 6-digit tokens. Officers verify student ID and produce signed PDF recovery receipts.
            </p>
          </div>

          <div className="card p-5 hover:border-teal-500/50 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 text-lg mb-3">
              📊
            </div>
            <h3 className="text-base font-semibold">Audit Logs &amp; Analytics</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Full lifecycle tracking with immutable audit event histories, monthly recovery metrics, and CSV reporting.
            </p>
          </div>

          <div className="card p-5 hover:border-teal-500/50 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 text-lg mb-3">
              ⚡
            </div>
            <h3 className="text-base font-semibold">Natural Language Search</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Type queries in plain conversational English. The AI parses time frames, colors, and campus buildings automatically.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-2xl font-bold">How it works</h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-4">
          {[['1', 'Report', 'Describe what you lost or found with a photo, category and campus zone.'], ['2', 'Match', 'The matching engine ranks possible pairs and explains why in plain language.'], ['3', 'Verify', 'Claimants answer private questions; officers review the proof.'], ['4', 'Return', 'A unique handover QR code and PDF receipt complete the recovery.']].map(([n, t, d]) => (
            <li key={n} className="card p-5 relative overflow-hidden">
              <span className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-teal-500 text-sm font-bold text-white shadow-sm">{n}</span>
              <h3 className="text-base font-semibold">{t}</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{d}</p>
            </li>))}
        </ol>

        <div className="mt-14 flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-bold">Recently found items</h2>
            <p className="text-xs text-slate-500 mt-1">Live updates from campus reporting offices</p>
          </div>
          <Link to="/browse" className="text-sm font-semibold text-teal-700 hover:underline dark:text-teal-300">
            View full catalog →
          </Link>
        </div>

        {recent.loading ? (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map(n => <ItemCardSkeleton key={n} />)}
          </div>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {recent.data?.items?.map((i) => <ItemCard key={i.id} item={i} />)}
          </div>
        )}
      </section>
    </>
  )
}
