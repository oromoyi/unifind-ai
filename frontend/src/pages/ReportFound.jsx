import { useNavigate } from 'react-router-dom'
import ItemForm from '../components/ItemForm'
import { PageHeader } from '../components/ui'
import { useAuth } from '../lib/auth'

export default function ReportFound() {
  const nav = useNavigate()
  const { can } = useAuth()
  return (<><PageHeader title="Register a found item" subtitle="Add a public description and, ideally, a private question only the owner can answer." />
    <ItemForm kind="found" staff={can('items.review')} onDone={() => nav('/app/my-reports')} /></>)
}
