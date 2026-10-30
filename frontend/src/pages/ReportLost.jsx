import { useNavigate } from 'react-router-dom'
import ItemForm from '../components/ItemForm'
import { PageHeader } from '../components/ui'

export default function ReportLost() {
  const nav = useNavigate()
  return (<><PageHeader title="Report a lost item" subtitle="The more detail you give, the better the matching engine can help." />
    <ItemForm kind="lost" onDone={(d) => nav(`/app/lost/${d.report.id}`)} /></>)
}
