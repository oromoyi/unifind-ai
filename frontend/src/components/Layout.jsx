import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useTheme } from '../lib/hooks'
import { ROLE_HOME } from '../lib/format'

function Logo({ light }) {
  return (
    <span className="flex items-center gap-2 font-semibold">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy-800 text-teal-300" aria-hidden>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="11" cy="11" r="6" /><path d="m20 20-4-4" /></svg>
      </span>
      <span className={light ? 'text-white' : 'text-navy-900 dark:text-white'}>UniFind <span className="text-teal-600 dark:text-teal-300">AI</span></span>
    </span>
  )
}

function ThemeToggle() {
  const [dark, toggle] = useTheme()
  return (
    <button onClick={toggle} className="btn-outline px-2.5" aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'} title="Toggle theme">
      {dark ? '☀️' : '🌙'}
    </button>
  )
}

const publicLinks = [['/browse', 'Browse found items'], ['/help', 'Help'], ['/faq', 'FAQ'], ['/about', 'About'], ['/contact', 'Contact']]
const linkCls = ({ isActive }) => `rounded-md px-3 py-2 text-sm font-medium ${isActive ? 'bg-navy-50 text-navy-800 dark:bg-navy-800 dark:text-white' : 'text-slate-600 hover:text-navy-800 dark:text-slate-300 dark:hover:text-white'}`

export function PublicLayout() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  useEffect(() => setOpen(false), [loc.pathname])
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-navy-800 dark:bg-navy-950/90">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" aria-label="UniFind AI home"><Logo /></Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">{publicLinks.map(([to, l]) => <NavLink key={to} to={to} className={linkCls}>{l}</NavLink>)}</nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user ? <Link className="btn-primary" to="/app">Dashboard</Link> : <>
              <Link className="btn-outline hidden sm:inline-flex" to="/login">Log in</Link>
              <Link className="btn-primary hidden sm:inline-flex" to="/register">Register</Link></>}
            <button className="btn-outline md:hidden" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Menu">☰</button>
          </div>
        </div>
        {open && <nav className="border-t border-slate-200 p-3 md:hidden dark:border-navy-800" aria-label="Mobile">
          <div className="flex flex-col">{publicLinks.map(([to, l]) => <NavLink key={to} to={to} className={linkCls}>{l}</NavLink>)}
            {!user && <><NavLink to="/login" className={linkCls}>Log in</NavLink><NavLink to="/register" className={linkCls}>Register</NavLink></>}</div></nav>}
      </header>
      <main id="main" className="flex-1"><Outlet /></main>
      <footer className="border-t border-slate-200 bg-white py-8 text-sm text-slate-500 dark:border-navy-800 dark:bg-navy-900">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4">
          <Logo /><p>© {new Date().getFullYear()} UniFind AI · Graduation project demonstration system</p>
          <div className="flex gap-4"><Link to="/help">Help</Link><Link to="/faq">FAQ</Link><Link to="/contact">Contact</Link></div>
        </div>
      </footer>
    </div>
  )
}

function navFor(role) {
  const common = [['/app', 'Dashboard', '🏠'], ['/app/notifications', 'Notifications', '🔔']]
  const by = {
    student: [['/app/report-lost', 'Report lost item', '📝'], ['/browse', 'Browse found items', '🔍'], ['/app/matches', 'Suggested matches', '✨'], ['/app/my-reports', 'My reports', '📂'], ['/app/my-claims', 'My claims', '🧾'], ['/app/handovers', 'Handovers', '🤝']],
    finder: [['/app/report-found', 'Register found item', '📦'], ['/app/my-reports', 'My found items', '📂'], ['/browse', 'Browse found items', '🔍']],
    officer: [['/app/report-found', 'Register received item', '📦'], ['/app/admin/manage', 'Items & claims', '🗂️'], ['/app/handovers', 'Handovers', '🤝'], ['/app/admin/analytics', 'Analytics', '📊']],
    admin: [['/app/admin/manage', 'Items & claims', '🗂️'], ['/app/admin/users', 'Users & roles', '👥'], ['/app/admin/analytics', 'Analytics & research', '📊'], ['/app/report-found', 'Register found item', '📦'], ['/app/handovers', 'Handovers', '🤝']],
  }
  return [...common.slice(0, 1), ...by[role], ...common.slice(1), ['/app/profile', 'Profile', '⚙️']]
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const loc = useLocation()
  useEffect(() => setOpen(false), [loc.pathname])
  useEffect(() => {
    let alive = true
    const load = () => api.get('/notifications/unread-count').then((d) => alive && setUnread(d.unread)).catch(() => {})
    load(); const t = setInterval(load, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [loc.pathname])
  const items = navFor(user.role)
  const sidebar = (
    <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Dashboard">
      {items.map(([to, label, icon]) => (
        <NavLink key={to + label} to={to} end={to === '/app'} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-teal-500/20 text-white' : 'text-navy-100 hover:bg-white/10'}`}>
          <span aria-hidden>{icon}</span><span className="flex-1">{label}</span>
          {label === 'Notifications' && unread > 0 && <span className="rounded-full bg-teal-400 px-2 py-0.5 text-xs font-semibold text-navy-950" aria-label={`${unread} unread`}>{unread}</span>}
        </NavLink>
      ))}
    </nav>
  )
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-navy-900 md:flex">
        <div className="p-4"><Link to="/"><Logo light /></Link></div>{sidebar}
        <div className="border-t border-white/10 p-4 text-xs text-navy-200">{user.full_name}<br />{ROLE_HOME[user.role]}</div>
      </aside>
      {open && <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setOpen(false)}>
        <aside className="flex h-full w-64 flex-col bg-navy-900" onClick={(e) => e.stopPropagation()}><div className="p-4"><Logo light /></div>{sidebar}</aside></div>}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur dark:border-navy-800 dark:bg-navy-950/90">
          <button className="btn-outline md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">☰</button>
          <div className="hidden text-sm text-slate-500 md:block">Signed in as <strong className="text-navy-800 dark:text-white">{user.full_name}</strong></div>
          <div className="flex items-center gap-2">
            <Link to="/app/notifications" className="btn-outline relative px-2.5" aria-label={`Notifications, ${unread} unread`}>🔔{unread > 0 && <span className="absolute -right-1 -top-1 h-4 min-w-4 rounded-full bg-red-500 px-1 text-[10px] leading-4 text-white">{unread}</span>}</Link>
            <ThemeToggle />
            <button className="btn-outline" onClick={() => { logout(); nav('/') }}>Log out</button>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-6"><Outlet /></main>
      </div>
    </div>
  )
}
