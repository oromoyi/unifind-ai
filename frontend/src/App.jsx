import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { PublicLayout, AppLayout } from './components/Layout'
import { Spinner } from './components/ui'
import { useAuth } from './lib/auth'
import AiChat from './components/AiChat'

const L = (f) => lazy(f)
const Landing = L(() => import('./pages/Landing'))
const Browse = L(() => import('./pages/Browse'))
const ItemDetails = L(() => import('./pages/ItemDetails'))
const Login = L(() => import('./pages/Auth').then((m) => ({ default: m.Login })))
const Register = L(() => import('./pages/Auth').then((m) => ({ default: m.Register })))
const Info = (name) => L(() => import('./pages/Info').then((m) => ({ default: m[name] })))
const About = Info('About'), Contact = Info('Contact'), Help = Info('Help'), Faq = Info('Faq')
const Dashboard = L(() => import('./pages/Dashboard'))
const ReportLost = L(() => import('./pages/ReportLost'))
const ReportFound = L(() => import('./pages/ReportFound'))
const Matches = L(() => import('./pages/Matches'))
const LostDetail = L(() => import('./pages/LostDetail'))
const ClaimForm = L(() => import('./pages/ClaimForm'))
const Notifications = L(() => import('./pages/Notifications'))
const MyReports = L(() => import('./pages/MyReports'))
const MyClaims = L(() => import('./pages/MyClaims'))
const Handovers = L(() => import('./pages/Handovers'))
const Profile = L(() => import('./pages/Profile'))
const AdminUsers = L(() => import('./pages/admin/Users'))
const AdminManage = L(() => import('./pages/admin/Manage'))
const AdminAnalytics = L(() => import('./pages/admin/Analytics'))

function Guard({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/app" replace />
  return children
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>        <Route element={<PublicLayout />}>
          <Route path="/" element={<Landing />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/items/:id" element={<ItemDetails />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/help" element={<Help />} />
          <Route path="/faq" element={<Faq />} />
        </Route>
        <Route path="/app" element={<Guard><AppLayout /></Guard>}>
          <Route index element={<Dashboard />} />
          <Route path="report-lost" element={<Guard roles={['student']}><ReportLost /></Guard>} />
          <Route path="report-found" element={<Guard roles={['finder', 'officer', 'admin']}><ReportFound /></Guard>} />
          <Route path="matches" element={<Guard roles={['student']}><Matches /></Guard>} />
          <Route path="lost/:id" element={<LostDetail />} />
          <Route path="claim/:id" element={<Guard roles={['student']}><ClaimForm /></Guard>} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="my-reports" element={<MyReports />} />
          <Route path="my-claims" element={<Guard roles={['student']}><MyClaims /></Guard>} />
          <Route path="handovers" element={<Handovers />} />
          <Route path="profile" element={<Profile />} />
          <Route path="admin/users" element={<Guard roles={['admin']}><AdminUsers /></Guard>} />
          <Route path="admin/manage" element={<Guard roles={['admin', 'officer']}><AdminManage /></Guard>} />
          <Route path="admin/analytics" element={<Guard roles={['admin', 'officer']}><AdminAnalytics /></Guard>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AiChat />
    </Suspense>
  )
}
