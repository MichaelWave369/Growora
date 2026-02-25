import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'

export const HomePage = () => <div><h1>Growora v0.2</h1><p>Offline-first super tutor with library, adaptive planning, and Triad369 packaging.</p></div>

export function IntakePage() {
  const nav = useNavigate();
  const [form, setForm] = useState<any>({ topic: 'Guitar', goal: 'Play 3 songs', level: 'beginner', schedule_days_per_week: 5, daily_minutes: 30, constraints: 'night shift', learner_type: 'adult', preferred_style: 'guided', day_starts_at: '18:00', auto_use_library: true, context_doc_ids: [] })
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
  return <div><h2>Course {id}</h2><a href={`/course/${id}/edit`}>Edit Course</a><pre>{JSON.stringify(data?.course, null, 2)}</pre></div>
}

export function CourseEditPage() {
  const { id } = useParams();
  const [course, setCourse] = useState<any>();
  const [lessons, setLessons] = useState<any[]>([])
  const load = ()=> api<any>(`/api/courses/${id}`).then(d=>{setCourse(d.course); setLessons(d.lessons || [])})
  useEffect(load, [id])
  const save = async ()=>{
    await api(`/api/courses/${id}`, {method:'PATCH', body: JSON.stringify({title: course.title, days_per_week: Number(course.days_per_week), minutes_per_day: Number(course.minutes_per_day), day_start_time: course.day_start_time, difficulty: course.difficulty})})
    alert('Saved')
  }
  const moveLesson = async (idx:number, dir:number) => {
    const l = lessons[idx]; if(!l) return;
    await api(`/api/lessons/${l.id}`, {method:'PATCH', body: JSON.stringify({order_index: l.order_index + dir})}); load();
  }
  const regenWeek = async ()=>{ await api(`/api/courses/${id}/regen/week/1`, {method:'POST'}); load() }
  if(!course) return <div>Loading...</div>
  return <div><h2>Course Editor</h2>
    <input value={course.title} onChange={e=>setCourse({...course,title:e.target.value})}/>
    <input value={course.day_start_time} onChange={e=>setCourse({...course,day_start_time:e.target.value})}/>
    <input type='number' value={course.days_per_week} onChange={e=>setCourse({...course,days_per_week:e.target.value})}/>
    <input type='number' value={course.minutes_per_day} onChange={e=>setCourse({...course,minutes_per_day:e.target.value})}/>
    <select value={course.difficulty} onChange={e=>setCourse({...course,difficulty:e.target.value})}><option>beginner</option><option>standard</option><option>advanced</option></select>
    <button onClick={save}>Save</button><button onClick={regenWeek}>Regenerate Week 1</button>
    <ul>{lessons.slice(0,8).map((l,i)=><li key={l.id}>{l.title} <button onClick={()=>moveLesson(i,-1)}>↑</button><button onClick={()=>moveLesson(i,1)}>↓</button></li>)}</ul>
  </div>
}

export function TodayPage() {
  const [plan, setPlan] = useState<any>(); const [next7, setNext7] = useState<any[]>([])
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=>{ if(cs[0]) { api<any>(`/api/courses/${cs[0].id}/plan/today`).then(setPlan); api<any[]>(`/api/courses/${cs[0].id}/plan/next7`).then(setNext7)}})}, [])
  const pct = useMemo(()=> plan ? Math.round((plan.used_minutes / Math.max(plan.time_budget,1))*100) : 0, [plan])
  return <div><h2>Today</h2>{plan && <>
    <p>Budget: {plan.used_minutes}/{plan.time_budget} mins ({pct}%)</p>
    <div style={{background:'#ddd', width:'100%', maxWidth:300}}><div style={{background:'#2563eb', width:`${pct}%`, height:10}}/></div>
    {plan.rolled_over_count>0 && <p>⚠️ Rolled over {plan.rolled_over_count} tasks from missed day(s).</p>}
    <pre>{JSON.stringify(plan.tasks, null, 2)}</pre>
    <h3>Next 7 days</h3><pre>{JSON.stringify(next7, null, 2)}</pre>
  </>}</div>
}

export function LessonPage() { const { lessonId } = useParams(); return <div><h2>Lesson {lessonId}</h2></div> }

export function LibraryPage() {
  const [docs, setDocs] = useState<any[]>([]); const [q, setQ] = useState(''); const [results, setResults] = useState<any[]>([]); const [context, setContext] = useState<Record<number, boolean>>({})
  const load = ()=> api<any[]>('/api/library/docs').then(setDocs)
  useEffect(load, [])
  const upload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget)
    const res = await fetch('/api/library/upload', {method:'POST', body: form})
    if(res.ok) load()
  }
  const doSearch = ()=> api<any[]>(`/api/library/search?q=${encodeURIComponent(q)}`).then(setResults)
  const tagDoc = async (id:number) => { await api(`/api/library/docs/${id}/tags`, {method:'POST', body: JSON.stringify({tags:['study']})}); load() }
  const delDoc = async (id:number) => { await api(`/api/library/docs/${id}`, {method:'DELETE'}); load() }
  return <div><h2>Library</h2>
    <form onSubmit={upload}><input name='tags' placeholder='tags comma separated'/><input name='file' type='file'/><button>Upload</button></form>
    <ul>{docs.map(d=><li key={d.id}>{d.filename} <button onClick={()=>tagDoc(d.id)}>Tag</button><button onClick={()=>delDoc(d.id)}>Delete</button></li>)}</ul>
    <input value={q} onChange={e=>setQ(e.target.value)} placeholder='search docs'/> <button onClick={doSearch}>Search</button>
    <ul>{results.map((r,idx)=><li key={idx}><label><input type='checkbox' checked={!!context[r.document.id]} onChange={e=>setContext({...context,[r.document.id]:e.target.checked})}/>Add to Course Context</label> {r.document.filename}: {r.snippet}</li>)}</ul>
  </div>
}

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
  const [publishStatus, setPublishStatus] = useState('')
  const [logs, setLogs] = useState<any[]>([])
  const withCourse = async (cb: (id:number)=>Promise<void>) => { const cs = await api<any[]>('/api/courses'); if(cs[0]) await cb(cs[0].id) }
  const doTriadExport = ()=> withCourse(async id => { const r = await api<any>(`/api/export/triad369/${id}`, {method:'POST'}); setStatus(r.file) })
  const doPublishDryRun = ()=> withCourse(async id => { try { const r = await api<any>(`/api/publish/coevo/${id}?dry_run=1`, {method:'POST'}); setPublishStatus(r.status) } catch(e:any){ setPublishStatus(String(e)) } })
  const testConnection = async ()=> { const r = await api<any>('/api/publish/test'); setPublishStatus(JSON.stringify(r)) }
  const refreshLogs = ()=> api<any[]>('/api/publish/logs').then(setLogs)
  const validatePkg = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const fd=new FormData(e.currentTarget); const r=await fetch('/api/export/triad369/validate',{method:'POST',body:fd}); setStatus(await r.text()) }
  const importPkg = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const fd=new FormData(e.currentTarget); const r=await fetch('/api/import/triad369',{method:'POST',body:fd}); setStatus(await r.text()) }
  return <div><h2>Export</h2><button onClick={doTriadExport}>Download Triad369 package</button><p>{status}</p>
    <form onSubmit={importPkg}><input name='file' type='file'/><button>Import package</button></form>
    <form onSubmit={validatePkg}><input name='file' type='file'/><button>Validate package</button></form>
    <button onClick={testConnection}>Test Connection</button><button onClick={doPublishDryRun}>Dry Run Publish</button><button onClick={refreshLogs}>Show publish logs</button>
    <p>{publishStatus}</p><pre>{JSON.stringify(logs, null, 2)}</pre>
  </div>
}

export function VerifyPage() {
  const { certId } = useParams();
  const [html, setHtml] = useState('')
  useEffect(()=>{ fetch(`/api/verify/${certId}`).then(r=>r.text()).then(setHtml)}, [certId])
  return <div><h2>Verify certificate</h2><div dangerouslySetInnerHTML={{__html: html}} /></div>
}
