import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync, useToast } from '../lib/hooks'
import MatchCard from '../components/MatchCard'
import { EmptyState, ErrorBox, Modal, PageHeader, Spinner, StatusBadge, ItemTimeline } from '../components/ui'
import { fmtDate, getItemPhoto } from '../lib/format'

export default function LostDetail() {
  const { id } = useParams()
  const toast = useToast()
  const { data, loading, error, reload } = useAsync(() => api.get(`/lost/${id}/matches?refresh=1`), [id])
  const [activeImg, setActiveImg] = useState(0)
  const [zoomImg, setZoomImg] = useState(null)

  if (loading) return <Spinner />
  if (error) return <ErrorBox error={error} />
  const r = data.report
  const images = r.images || []
  const hasUploadedPhoto = images.length > 0
  const currentPhoto = images[activeImg] || images[0] || getItemPhoto(r)

  const close = async () => {
    if (!confirm('Close this report? Matches will be removed.')) return
    try {
      await api.post(`/lost/${id}/close`)
      toast('Report closed.')
      reload()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  return (
    <>
      <PageHeader
        title={r.title}
        subtitle={`Reported ${fmtDate(r.created_at)}`}
        actions={r.status === 'open' && <button className="btn-outline" onClick={close}>Close report</button>}
      />

      <ItemTimeline status={r.status} kind="lost" />

      {/* Material Profile Card */}
      <div className="card mb-8 overflow-hidden p-5">
        <div className="grid gap-6 md:grid-cols-3">
          {/* Details */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-teal-600 dark:text-teal-400">
                Lost Material Profile
              </span>
              <StatusBadge status={r.status} />
            </div>

            <p className="text-base text-slate-800 dark:text-slate-200 leading-relaxed">{r.description}</p>

            {r.distinguishing_features && (
              <div className="mt-3 rounded-lg bg-teal-50/70 p-3 text-sm text-teal-900 dark:bg-teal-950/30 dark:text-teal-200">
                <strong>Distinguishing features:</strong> {r.distinguishing_features}
              </div>
            )}

            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm border-t border-slate-100 pt-3 dark:border-navy-800">
              <div>
                <dt className="text-xs uppercase text-slate-500">Category</dt>
                <dd className="font-medium">{r.category}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">Lost location</dt>
                <dd className="font-medium">{r.location}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">Date lost</dt>
                <dd className="font-medium">{fmtDate(r.date)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">Colour & Brand</dt>
                <dd className="font-medium">{[r.color, r.brand].filter(Boolean).join(' · ') || 'Not specified'}</dd>
              </div>
            </dl>
          </div>

          {/* Photo Showcase */}
          <div className="space-y-3">
            {currentPhoto ? (
              <div
                className="relative aspect-[4/3] w-full cursor-zoom-in overflow-hidden rounded-xl bg-slate-100 dark:bg-navy-950"
                onClick={() => setZoomImg(currentPhoto)}
                title="Click to enlarge"
              >
                <img
                  src={currentPhoto}
                  alt={r.title}
                  className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                />
                <span className="absolute top-2 left-2 rounded bg-navy-900/80 px-2 py-0.5 text-[10px] font-semibold text-white">
                  📷 Photo {images.length > 1 ? `${activeImg + 1}/${images.length}` : ''}
                </span>
              </div>
            ) : (
              <div className="flex aspect-[4/3] flex-col items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-navy-950">
                <span className="text-3xl">📦</span>
                <p className="mt-1 text-xs text-slate-500">No photo uploaded</p>
              </div>
            )}

            {/* Thumbnail switcher if multiple images */}
            {images.length > 1 && (
              <div className="flex gap-2">
                {images.map((src, i) => (
                  <button
                    key={src + i}
                    type="button"
                    onClick={() => setActiveImg(i)}
                    className={`h-12 w-12 overflow-hidden rounded-lg border-2 ${
                      activeImg === i ? 'border-teal-500 ring-2 ring-teal-500/30' : 'border-slate-200 opacity-70'
                    }`}
                  >
                    <img src={src} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Suggested matches section */}
      <h2 className="mb-1 text-lg font-semibold">Suggested matches</h2>
      <p className="mb-3 text-xs text-slate-500">
        {data.disclaimer} Minimum score shown: {data.min_score}.
      </p>

      {data.matches.length === 0 ? (
        <EmptyState
          title="No matches yet"
          text="Check back later — the AI matching engine will automatically notify you when an item matching this description or photo is turned in."
          action={<Link to="/browse" className="btn-outline">Browse all found items</Link>}
        />
      ) : (
        <div className="space-y-4">
          {data.matches.map((m) => (
            <MatchCard key={m.id} m={m} />
          ))}
        </div>
      )}

      {/* Zoom Modal */}
      {zoomImg && (
        <Modal open={!!zoomImg} title={`Photo of ${r.title}`} onClose={() => setZoomImg(null)}>
          <div className="flex flex-col items-center">
            <img src={zoomImg} alt={r.title} className="max-h-[75vh] w-full rounded-lg object-contain" />
            <div className="mt-3 flex w-full justify-end">
              <button className="btn-outline !py-1" onClick={() => setZoomImg(null)}>Close</button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
