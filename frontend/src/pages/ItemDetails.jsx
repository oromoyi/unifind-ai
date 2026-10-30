import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync } from '../lib/hooks'
import { ErrorBox, Modal, Spinner, StatusBadge, ItemTimeline } from '../components/ui'
import { fmtDate, fmtDateTime, getItemPhoto } from '../lib/format'

export default function ItemDetails() {
  const { id } = useParams()
  const { user } = useAuth()
  const item = useAsync(() => api.get(`/found/${id}`), [id])
  const tl = useAsync(() => api.get(`/found/${id}/timeline`).catch(() => null), [id])
  const [activeImg, setActiveImg] = useState(0)
  const [zoomImg, setZoomImg] = useState(null)

  if (item.loading) return <Spinner />
  if (item.error) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <ErrorBox
          error={
            item.error.status === 404
              ? new Error('This item is not available (it may have been claimed, returned or is awaiting review).')
              : item.error
          }
        />
        <Link to="/browse" className="mt-4 inline-block text-teal-700 underline">
          ← Back to browse
        </Link>
      </div>
    )
  }

  const it = item.data.item
  const canClaim = user?.role === 'student' && it.status === 'available'
  const images = it.images || []
  const hasUploadedPhoto = images.length > 0
  const currentPhoto = images[activeImg] || images[0] || getItemPhoto(it)

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link to="/browse" className="text-sm font-medium text-teal-700 hover:underline dark:text-teal-300">
        ← Back to browse
      </Link>

      <ItemTimeline status={it.status} kind="found" />

      <div className="mt-4 grid gap-8 md:grid-cols-2">
        {/* Material Profile Photo Showcase */}
        <div className="space-y-4">
          <div className="card group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-sm dark:border-navy-700 dark:bg-navy-900">
            {currentPhoto ? (
              <div
                className="relative aspect-[4/3] w-full cursor-zoom-in overflow-hidden rounded-xl bg-slate-100 dark:bg-navy-950"
                onClick={() => setZoomImg(currentPhoto)}
                title="Click to zoom in"
              >
                <img
                  src={currentPhoto}
                  alt={it.title}
                  className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
                <span className="absolute top-3 left-3 rounded-md bg-navy-900/80 px-2 py-1 text-[11px] font-semibold text-white backdrop-blur-sm">
                  📷 {hasUploadedPhoto ? `Item Photo ${images.length > 1 ? `${activeImg + 1} of ${images.length}` : ''}` : 'Material Reference Photo'}
                </span>
                <span className="absolute bottom-3 right-3 rounded-md bg-white/90 px-2 py-1 text-[11px] font-medium text-slate-800 shadow dark:bg-navy-900/90 dark:text-white">
                  🔍 Click to enlarge
                </span>
              </div>
            ) : (
              <div className="flex aspect-[4/3] flex-col items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-navy-950">
                <span className="text-4xl">📦</span>
                <p className="mt-2 text-sm font-medium text-slate-500 dark:text-slate-400">No photo provided for this material</p>
                <p className="text-xs text-slate-400">Finder did not attach an image</p>
              </div>
            )}
          </div>

          {/* Thumbnail Gallery */}
          {images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {images.map((src, i) => (
                <button
                  key={src + i}
                  type="button"
                  onClick={() => setActiveImg(i)}
                  className={`relative h-18 w-18 shrink-0 overflow-hidden rounded-lg border-2 transition ${
                    activeImg === i
                      ? 'border-teal-500 ring-2 ring-teal-500/30'
                      : 'border-slate-200 opacity-70 hover:opacity-100 dark:border-navy-700'
                  }`}
                >
                  <img src={src} alt={`Thumbnail ${i + 1}`} className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Material Profile Information */}
        <div>
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-teal-600 dark:text-teal-400">Material Profile</p>
              <h1 className="text-2xl font-bold">{it.title}</h1>
            </div>
            <StatusBadge status={it.status} />
          </div>

          <dl className="mt-5 grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-sm dark:border-navy-700 dark:bg-navy-900/50">
            {[
              ['Category', it.category],
              ['Found at', it.location],
              ['Date found', fmtDate(it.date)],
              ['Colour', it.color || '-'],
              ['Brand', it.brand || '-'],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs uppercase text-slate-500 dark:text-slate-400">{k}</dt>
                <dd className="font-semibold text-navy-900 dark:text-white">{v}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Public Description</h3>
            <p className="mt-1 text-slate-700 dark:text-slate-300 leading-relaxed">{it.description}</p>
          </div>

          <p className="mt-4 rounded-lg bg-slate-100 p-3 text-xs text-slate-600 dark:bg-navy-800 dark:text-slate-300">
            🔒 Identifying details are kept private to protect the true owner. To claim this item you will be asked a verification question, and an officer must approve your claim.
          </p>

          {it.private_details && (
            <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950/30">
              <strong>Private details (staff / reporter only):</strong> {it.private_details}
            </div>
          )}

          <div className="mt-5">
            {canClaim ? (
              <Link className="btn-accent w-full text-center sm:w-auto" to={`/app/claim/${it.id}`}>
                This is mine — start a claim
              </Link>
            ) : !user ? (
              <Link className="btn-primary w-full text-center sm:w-auto" to="/login">
                Log in to claim this item
              </Link>
            ) : user.role !== 'student' && it.status === 'available' ? (
              <p className="text-sm text-slate-500">Only student/staff accounts can submit claims.</p>
            ) : null}
          </div>

          {tl.data?.events?.length > 0 && (
            <section className="mt-8 border-t border-slate-200 pt-5 dark:border-navy-800" aria-labelledby="tl">
              <h2 id="tl" className="text-base font-semibold">
                Item lifecycle & audit
              </h2>
              <ol className="mt-3 space-y-3 border-l-2 border-teal-400 pl-4 text-sm">
                {tl.data.events.map((e, i) => (
                  <li key={i}>
                    <span className="font-medium text-navy-900 dark:text-white">{e.label}</span>
                    <br />
                    <span className="text-xs text-slate-500">{fmtDateTime(e.at)}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      </div>

      {/* Lightbox Zoom Modal */}
      {zoomImg && (
        <Modal open={!!zoomImg} title={`Photo of ${it.title}`} onClose={() => setZoomImg(null)}>
          <div className="flex flex-col items-center">
            <img src={zoomImg} alt={it.title} className="max-h-[75vh] w-full rounded-lg object-contain" />
            <div className="mt-3 flex w-full justify-between items-center text-xs text-slate-500">
              <span>{it.title} · {it.category}</span>
              <button className="btn-outline !py-1" onClick={() => setZoomImg(null)}>Close</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
