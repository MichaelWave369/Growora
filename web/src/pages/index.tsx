import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'

export const HomePage = () => <div><h1>Growora</h1><p>Tell me what you want to learn. I'll build your course offline.</p></div>

export function IntakePage() {
  const nav = useNavigate();
  const [form, setForm] = useState<any>({ topic: 'Guitar', goal: 'Play 3 songs', level: 'beginner', schedule_days_per_week: 5, daily_minutes: 30, constraints: 'night shift', learner_type: 'adult', preferred_style: 'guided', day_starts_at: '18:00' })
  const submit = async () => {
    const r = await api<{course_id:number}>('/api/courses', { method: 'POST', body: JSON.stringify(form) })
    nav(`/course/${r.course_id}`)
  }
  return <div><h2>Intake Wizard</h2><input value={form.topic} onChange={e=>setForm({...form,topic:e.target.value})}/><button onClick={submit}>Build Course</button></div>
}

export function CoursePage() {
  const { id } = useParams();
  const [data, setData] = useState<any>()
  useEffect(()=>{ api<any>(`/api/courses/${id}`).then(setData)}, [id])
  return <div><h2>Course {id}</h2><pre>{JSON.stringify(data?.course, null, 2)}</pre></div>
}

export function TodayPage() {
  const [courses, setCourses] = useState<any[]>([]); const [today, setToday] = useState<any>()
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=>{ setCourses(cs); if(cs[0]) api<any>(`/api/courses/${cs[0].id}/today`).then(setToday)}) }, [])
  return <div><h2>Today</h2><pre>{JSON.stringify(today, null, 2)}</pre></div>
}

export function LessonPage() { const { lessonId } = useParams(); return <div><h2>Lesson {lessonId}</h2></div> }

export function FlashcardsPage() {
  const [due, setDue] = useState<any[]>([])
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=> cs[0] && api<any[]>(`/api/flashcards/due?course_id=${cs[0].id}`).then(setDue))}, [])
  return <div><h2>Flashcards due</h2><pre>{JSON.stringify(due, null, 2)}</pre></div>
}

export function DashboardPage() {
  const [summary, setSummary] = useState<any>()
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=> cs[0] && api<any>(`/api/progress/summary?course_id=${cs[0].id}`).then(setSummary))}, [])
  return <div><h2>Dashboard</h2><pre>{JSON.stringify(summary, null, 2)}</pre></div>
}

export function ExportPage() {
  const [status, setStatus] = useState('')
  const doExport = async () => { const cs = await api<any[]>('/api/courses'); if(!cs[0]) return; const r = await api<any>(`/api/export/course/${cs[0].id}`, {method:'POST'}); setStatus(r.file) }
  return <div><h2>Export</h2><button onClick={doExport}>Package as course</button><p>{status}</p></div>
}
