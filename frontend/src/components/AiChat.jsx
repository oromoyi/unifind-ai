/**
 * AiChat – floating AI assistant widget available on every page.
 * Talks to POST /api/ai/chat (backend Gemini integration).
 */
import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

const WELCOME = 'Hi! I\'m the UniFind AI assistant 🤖\nAsk me anything about lost items, how to report, claims, or how the system works.'

function Msg({ role, text }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap leading-relaxed
        ${isUser
          ? 'bg-teal-600 text-white rounded-br-sm'
          : 'bg-white dark:bg-navy-800 border border-slate-200 dark:border-navy-700 text-slate-800 dark:text-slate-100 rounded-bl-sm shadow-sm'}`}>
        {text}
      </div>
    </div>
  )
}

export default function AiChat() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([{ role: 'model', text: WELCOME }])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return
    const next = [...messages, { role: 'user', text }]
    setMessages(next)
    setInput('')
    setBusy(true)
    setError('')
    try {
      const d = await api.post('/ai/chat', { messages: next.map(m => ({ role: m.role, text: m.text })) })
      setMessages(m => [...m, { role: 'model', text: d.reply }])
    } catch (e) {
      setError(e.message || 'AI error. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 shadow-lg hover:bg-teal-700 transition-all active:scale-95"
        aria-label={open ? 'Close AI assistant' : 'Open AI assistant'}
        title="UniFind AI Assistant"
      >
        {open
          ? <svg width="20" height="20" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12" /></svg>
          : <svg width="22" height="22" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2a10 10 0 0 1 10 10c0 5.52-4.48 10-10 10a9.96 9.96 0 0 1-4.93-1.3L2 22l1.3-5.07A9.96 9.96 0 0 1 2 12 10 10 0 0 1 12 2z"/><path d="M8 10h.01M12 10h.01M16 10h.01" strokeLinecap="round"/></svg>
        }
        {/* AI badge */}
        <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-navy-800 text-[9px] font-bold text-teal-300">AI</span>
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex w-80 sm:w-96 flex-col rounded-2xl border border-slate-200 bg-slate-50 shadow-2xl dark:border-navy-700 dark:bg-navy-950"
          style={{ height: '480px', maxHeight: 'calc(100vh - 120px)' }}>
          {/* Header */}
          <div className="flex items-center gap-2 rounded-t-2xl bg-teal-600 px-4 py-3 text-white">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20 text-xs font-bold">AI</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold leading-none">UniFind Assistant</p>
              <p className="text-[10px] text-teal-100 mt-0.5">Powered by Gemini</p>
            </div>
            <button onClick={() => setMessages([{ role: 'model', text: WELCOME }])} title="Clear chat"
              className="rounded p-1 hover:bg-white/20 text-white/70 hover:text-white text-xs">↺</button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-3 p-3">
            {messages.map((m, i) => <Msg key={i} role={m.role} text={m.text} />)}
            {busy && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-sm bg-white dark:bg-navy-800 border border-slate-200 dark:border-navy-700 px-3 py-2 shadow-sm">
                  <span className="flex gap-1 items-center">
                    {[0, 150, 300].map(d => <span key={d} className="h-2 w-2 rounded-full bg-teal-400 animate-bounce" style={{ animationDelay: `${d}ms` }} />)}
                  </span>
                </div>
              </div>
            )}
            {error && <p className="text-xs text-red-500 text-center px-2">{error}</p>}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-slate-200 dark:border-navy-800 p-3 flex gap-2">
            <textarea
              className="input flex-1 resize-none text-sm"
              rows={2}
              placeholder="Ask anything about lost items…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={busy}
              aria-label="Chat message"
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="self-end rounded-lg bg-teal-600 px-3 py-2 text-white hover:bg-teal-700 disabled:opacity-40 transition"
              aria-label="Send"
            >
              <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  )
}

