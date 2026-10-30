/**
 * AiImageAnalyzer – drop an image, get AI-suggested item fields back.
 * Called from ItemForm to auto-fill title, category, color, brand, description.
 */
import { useRef, useState } from 'react'
import { api } from '../lib/api'

export default function AiImageAnalyzer({ onResult }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  const inputRef = useRef(null)

  const analyze = async (file) => {
    if (!file) return
    setError('')
    setBusy(true)
    setPreview(URL.createObjectURL(file))

    // Convert to base64
    const reader = new FileReader()
    reader.onload = async (ev) => {
      const dataUrl = ev.target.result                // data:image/jpeg;base64,....
      const [header, b64] = dataUrl.split(',')
      const mime = header.match(/:(.*?);/)?.[1] || 'image/jpeg'
      try {
        const d = await api.post('/ai/analyze-image', { image_base64: b64, mime_type: mime })
        onResult(d.details, file)
      } catch (e) {
        setError(e.message || 'AI could not analyse this image. Fill in the fields manually.')
        // Even if AI text analysis failed, still pass the file to be used as the item's photo!
        onResult({}, file)
      } finally {
        setBusy(false)
      }
    }
    reader.readAsDataURL(file)
  }

  const onDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) analyze(file)
  }

  return (
    <div className="rounded-xl border-2 border-dashed border-teal-400 bg-teal-50/60 dark:border-teal-700 dark:bg-teal-950/20 p-4">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-600 text-white font-bold text-sm">AI</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-teal-800 dark:text-teal-200">AI Image Auto-Fill</p>
          <p className="text-xs text-teal-700 dark:text-teal-400 mt-0.5">
            Upload a photo and AI will suggest the title, category, colour, brand and description for you.
          </p>
        </div>
      </div>

      <div
        onDrop={onDrop}
        onDragOver={e => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="mt-3 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-teal-300 bg-white dark:bg-navy-900 dark:border-teal-800 p-4 text-center hover:bg-teal-50 dark:hover:bg-teal-950/30 transition"
      >
        {busy ? (
          <span className="flex items-center gap-2 text-sm text-teal-700 dark:text-teal-300">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
            Analysing image…
          </span>
        ) : preview ? (
          <div className="flex flex-col items-center gap-2">
            <img src={preview} alt="Preview" className="h-20 w-20 rounded-lg object-cover" />
            <span className="text-xs text-teal-600 dark:text-teal-300">Click to try another photo</span>
          </div>
        ) : (
          <>
            <svg width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-teal-400 mb-1">
              <rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="m21 15-5-5L5 21" />
            </svg>
            <span className="text-sm text-teal-700 dark:text-teal-300">Drop image here or click to upload</span>
            <span className="text-xs text-slate-400 mt-0.5">JPG, PNG, WEBP</span>
          </>
        )}
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
          onChange={e => analyze(e.target.files[0])} />
      </div>

      {error && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}

