import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useToast } from '../lib/hooks'
import { Input, Textarea } from '../components/ui'

const Page = ({ title, children }) => <div className="mx-auto max-w-3xl px-4 py-10"><h1 className="text-3xl">{title}</h1><div className="mt-5 space-y-4 text-slate-700 dark:text-slate-300">{children}</div></div>

export const About = () => (
  <Page title="About UniFind AI">
    <p>UniFind AI is a Computer Science and Engineering graduation project: a centralised platform where students, lecturers, administrative staff and campus security report lost belongings, register found items, review suggested matches, verify ownership and record returns.</p>
    <h2 className="text-xl">What is implemented</h2>
    <ul className="list-disc space-y-1 pl-6"><li>Explainable weighted matching (category, TF-IDF description similarity, colour/brand, location, date, colour-histogram photo similarity).</li><li>Private verification questions stored as salted hashes, attempt limits and suspicious-claim flags.</li><li>Officer review, unique handover codes, receipts, audit trail, analytics and CSV/PDF exports.</li></ul>
    <h2 className="text-xl">What it does not do</h2>
    <p>The matching engine <strong>only suggests</strong> candidates. It never establishes ownership or releases an item; a human officer always decides. Photo similarity is a simple colour comparison, not facial or deep-learning recognition.</p>
  </Page>
)

const FAQS = [
  ['Does the AI decide who owns an item?', 'No. Suggestions are ranked and explained, but ownership is only established after you answer private verification questions and an officer approves your claim.'],
  ['Why can’t I see every detail of a found item?', 'Finders and officers keep identifying details private (for example a lock-screen picture) so that only the true owner can answer correctly.'],
  ['How many times can I try to claim an item?', 'By default three attempts per item. After that you must visit the Lost-and-Found office in person.'],
  ['What do I bring to collect an item?', 'Your student ID (or staff ID) and the unique handover code shown in your Handovers page after approval.'],
  ['Who can see my phone number?', 'Only authorised officers and administrators reviewing a claim. It is never shown in public search.'],
  ['What happens to unclaimed items?', 'Administrators may archive items after the university’s retention period. Archived items are no longer public.'],
]

export function Faq() {
  return (
    <Page title="Frequently asked questions">
      {FAQS.map(([q, a]) => <details key={q} className="card p-4"><summary className="cursor-pointer font-medium text-navy-900 dark:text-white">{q}</summary><p className="mt-2 text-sm">{a}</p></details>)}
    </Page>
  )
}

export function Help() {
  return (
    <Page title="Help centre">
      <div className="grid gap-4 sm:grid-cols-2">
        {[['I lost something', 'Register, then use “Report lost item”. Add a photo if you have one, plus colour, brand and distinguishing marks.'],
          ['I found something', 'Register as a Finder, use “Register found item”, and add a private verification question only the owner could answer. Then hand it to Security.'],
          ['I want to claim an item', 'Open the item, press “This is mine”, describe it in detail and answer the verification question.'],
          ['Collecting my item', 'After approval you receive a notification and a handover code. Bring your ID to the office; the officer completes the handover.']].map(([t, d]) => (
          <div key={t} className="card p-5"><h2 className="text-base">{t}</h2><p className="mt-1 text-sm">{d}</p></div>))}
      </div>
      <p className="text-sm">More answers are in the <Link className="text-teal-700 underline dark:text-teal-300" to="/faq">FAQ</Link>, or <Link className="text-teal-700 underline dark:text-teal-300" to="/contact">contact us</Link>.</p>
    </Page>
  )
}

export function Contact() {
  const toast = useToast()
  const [v, setV] = useState({ name: '', email: '', message: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { const d = await api.post('/contact', v); toast(d.message); setV({ name: '', email: '', message: '' }) }
    catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  return (
    <Page title="Contact us">
      <p>Questions about the system or a stuck handover? Send a message and the administrators will reply by email.</p>
      <div className="card space-y-3 p-5">
        <h2 className="text-base font-semibold text-navy-900 dark:text-white">Direct contact</h2>
        <p className="flex items-center gap-3 text-sm">
          <span className="text-lg" aria-hidden>📞</span>
          <a href="tel:0922750429" className="text-teal-700 underline dark:text-teal-300">0922750429</a>
        </p>
        <p className="flex items-center gap-3 text-sm">
          <span className="text-lg" aria-hidden>✉️</span>
          <a href="mailto:deressafufa54@gmail.com" className="text-teal-700 underline dark:text-teal-300">deressafufa54@gmail.com</a>
        </p>
      </div>
      <form onSubmit={submit} className="card space-y-4 p-5">
        {err && <p role="alert" className="text-sm text-red-600">{err}</p>}
        <Input id="name" label="Name" value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} />
        <Input id="email" label="Email" type="email" value={v.email} onChange={(e) => setV({ ...v, email: e.target.value })} />
        <Textarea id="msg" label="Message" value={v.message} onChange={(e) => setV({ ...v, message: e.target.value })} />
        <button className="btn-primary" disabled={busy}>{busy ? 'Sending…' : 'Send message'}</button>
      </form>
    </Page>
  )
}
