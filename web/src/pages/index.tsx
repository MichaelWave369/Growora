import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'

export const HomePage = () => <div><h1>Growora v0.3</h1><p>Tutor Sessions + Multi-profile + Worksheet Forge (offline-first).</p></div>

export function ProfilesPage() {
  const [profiles, setProfiles] = useState<any[]>([])
  const [name, setName] = useState('')
  const load = ()=> api<any[]>('/api/profiles').then(setProfiles)
  useEffect(load, [])
  const create = async ()=> { await api('/api/profiles', {method:'POST', body: JSON.stringify({display_name:name||'Learner', role:'adult', timezone:'UTC', day_start_time:'06:00'})}); setName(''); load() }
  return <div><h2>Profiles</h2><input value={name} onChange={e=>setName(e.target.value)} placeholder='Create your first learner'/><button onClick={create}>Create</button><pre>{JSON.stringify(profiles,null,2)}</pre></div>
}

export function IntakePage() {
  const nav = useNavigate();
  const [form, setForm] = useState<any>({ topic: 'Guitar', goal: 'Play 3 songs', level: 'beginner', schedule_days_per_week: 5, daily_minutes: 30, constraints: 'night shift', learner_type: 'adult', preferred_style: 'guided', day_starts_at: '18:00', auto_use_library: true, context_doc_ids: [] })
  const submit = async () => { const r = await api<{course_id:number}>('/api/courses', { method: 'POST', body: JSON.stringify(form) }); nav(`/course/${r.course_id}`) }
  return <div><h2>Intake Wizard</h2><input value={form.topic} onChange={e=>setForm({...form,topic:e.target.value})}/><button onClick={submit}>Build Course</button></div>
}

export function CoursePage() {
  const { id } = useParams(); const [data, setData] = useState<any>()
  useEffect(()=>{ api<any>(`/api/courses/${id}`).then(setData)}, [id])
  return <div><h2>Course {id}</h2><a href={`/course/${id}/edit`}>Edit Course</a><pre>{JSON.stringify(data?.course, null, 2)}</pre></div>
}

export function CourseEditPage() {
  const { id } = useParams(); const [course, setCourse] = useState<any>(); const [lessons, setLessons] = useState<any[]>([])
  const load = ()=> api<any>(`/api/courses/${id}`).then(d=>{setCourse(d.course); setLessons(d.lessons || [])}); useEffect(load, [id])
  const save = async ()=>{ await api(`/api/courses/${id}`, {method:'PATCH', body: JSON.stringify({title: course.title, days_per_week: Number(course.days_per_week), minutes_per_day: Number(course.minutes_per_day), day_start_time: course.day_start_time, difficulty: course.difficulty})}); alert('Saved') }
  const moveLesson = async (idx:number, dir:number) => { const l = lessons[idx]; if(!l) return; await api(`/api/lessons/${l.id}`, {method:'PATCH', body: JSON.stringify({order_index: l.order_index + dir})}); load() }
  const regenWeek = async ()=>{ await api(`/api/courses/${id}/regen/week/1`, {method:'POST'}); load() }
  if(!course) return <div>Loading...</div>
  return <div><h2>Course Editor</h2><input value={course.title} onChange={e=>setCourse({...course,title:e.target.value})}/><button onClick={save}>Save</button><button onClick={regenWeek}>Regenerate Week 1</button><ul>{lessons.slice(0,8).map((l,i)=><li key={l.id}>{l.title} <button onClick={()=>moveLesson(i,-1)}>↑</button><button onClick={()=>moveLesson(i,1)}>↓</button></li>)}</ul></div>
}

export function TodayPage() {
  const nav = useNavigate();
  const [plan, setPlan] = useState<any>(); const [next7, setNext7] = useState<any[]>([]); const [courseId, setCourseId] = useState<number|undefined>()
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=>{ if(cs[0]) { setCourseId(cs[0].id); api<any>(`/api/courses/${cs[0].id}/plan/today`).then(setPlan); api<any[]>(`/api/courses/${cs[0].id}/plan/next7`).then(setNext7)}})}, [])
  const pct = useMemo(()=> plan ? Math.round((plan.used_minutes / Math.max(plan.time_budget,1))*100) : 0, [plan])
  const start = async ()=>{ if(!courseId) return; const s=await api<any>('/api/sessions/start',{method:'POST',body:JSON.stringify({course_id:courseId,planned_minutes:plan?.time_budget||30,mode:'369'})}); nav(`/session/${s.id}`)}
  return <div><h2>Today</h2>{plan && <><p>Budget: {plan.used_minutes}/{plan.time_budget} mins ({pct}%)</p><button onClick={start}>Start Session</button><div style={{background:'#ddd', width:'100%', maxWidth:300}}><div style={{background:'#2563eb', width:`${pct}%`, height:10}}/></div>{plan.rolled_over_count>0 && <p>⚠️ Rolled over {plan.rolled_over_count} tasks.</p>}<pre>{JSON.stringify(plan.tasks, null, 2)}</pre><h3>Next 7 days</h3><pre>{JSON.stringify(next7, null, 2)}</pre></>}</div>
}

export function SessionPage() {
  const { id } = useParams(); const [sec, setSec] = useState(0); const [paused, setPaused] = useState(false); const [notes, setNotes] = useState(''); const [detail, setDetail] = useState<any>()
  useEffect(()=>{const t=setInterval(()=>{ if(!paused) setSec(s=>s+1)},1000); return ()=>clearInterval(t)},[paused])
  useEffect(()=>{ api<any>(`/api/sessions/${id}`).then(setDetail)}, [id])
  const sendEvent = (type:string)=> api('/api/sessions/event',{method:'POST',body:JSON.stringify({session_id:Number(id),type,payload:{sec}})})
  const end = async ()=>{ await api('/api/sessions/end',{method:'POST',body:JSON.stringify({session_id:Number(id),notes_md:notes})}); const d=await api<any>(`/api/sessions/${id}`); setDetail(d) }
  return <div><h2>Session {id}</h2><p>Timer: {Math.floor(sec/60)}:{String(sec%60).padStart(2,'0')}</p><button onClick={()=>{setPaused(!paused); sendEvent(paused?'resume':'pause')}}>{paused?'Resume':'Pause'}</button><button onClick={()=>sendEvent('complete_task')}>Complete Task</button><button onClick={()=>sendEvent('quiz_wrong')}>Wrong Answer</button><textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder='Reflection notes'/><button onClick={end}>End Session</button><pre>{JSON.stringify(detail?.summary, null, 2)}</pre></div>
}

export function LessonPage() { const { lessonId } = useParams(); return <div><h2>Lesson {lessonId}</h2></div> }

export function LibraryPage() {
  const [docs, setDocs] = useState<any[]>([]); const [q, setQ] = useState(''); const [results, setResults] = useState<any[]>([])
  const load = ()=> api<any[]>('/api/library/docs').then(setDocs); useEffect(load, [])
  const upload = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const form = new FormData(e.currentTarget); const res = await fetch('/api/library/upload', {method:'POST', body: form, headers: {'X-Growora-Profile': localStorage.getItem('growora_profile_id') || ''}}); if(res.ok) load() }
  const doSearch = ()=> api<any[]>(`/api/library/search?q=${encodeURIComponent(q)}`).then(setResults)
  return <div><h2>Library</h2><form onSubmit={upload}><input name='tags' placeholder='tags'/><input name='file' type='file'/><button>Upload</button></form><pre>{JSON.stringify(docs,null,2)}</pre><input value={q} onChange={e=>setQ(e.target.value)}/><button onClick={doSearch}>Search</button><pre>{JSON.stringify(results,null,2)}</pre></div>
}

export function ForgePage() {
  const [docs, setDocs] = useState<any[]>([]); const [selected, setSelected] = useState<number[]>([]); const [type, setType] = useState('flashcards'); const [job, setJob] = useState<any>()
  useEffect(()=>{ api<any[]>('/api/library/docs').then(setDocs)}, [])
  const run = async ()=>{ const j = await api<any>('/api/forge/run',{method:'POST',body:JSON.stringify({type,doc_ids:selected,count:8,focus_topics:[]})}); const detail=await api<any>(`/api/forge/jobs/${j.id}`); setJob(detail) }
  const apply = async ()=>{ const cs=await api<any[]>('/api/courses'); if(!cs[0]||!job?.job?.id) return; await api(`/api/forge/jobs/${job.job.id}/apply_to_course`,{method:'POST',body:JSON.stringify({course_id:cs[0].id})}); alert('Applied') }
  return <div><h2>Forge</h2><select value={type} onChange={e=>setType(e.target.value)}><option value='flashcards'>Make flashcards</option><option value='worksheet'>Make worksheet</option><option value='quiz'>Make quiz</option><option value='summary'>Make summary</option></select>{docs.map(d=><label key={d.id}><input type='checkbox' checked={selected.includes(d.id)} onChange={e=>setSelected(e.target.checked?[...selected,d.id]:selected.filter(x=>x!==d.id))}/>{d.filename}</label>)}<button onClick={run}>Run Forge</button><button onClick={apply}>Attach to Course</button><pre>{JSON.stringify(job,null,2)}</pre></div>
}

export function FlashcardsPage() { const [due, setDue] = useState<any[]>([]); useEffect(()=>{ api<any[]>('/api/courses').then(cs=> cs[0] && api<any[]>(`/api/flashcards/due?course_id=${cs[0].id}`).then(setDue))}, []); return <div><h2>Flashcards due</h2><pre>{JSON.stringify(due, null, 2)}</pre></div> }

export function DashboardPage() { const [summary, setSummary] = useState<any>(); const [analytics, setAnalytics] = useState<any>(); useEffect(()=>{ api<any[]>('/api/courses').then(cs=> { if(cs[0]) { api<any>(`/api/progress/summary?course_id=${cs[0].id}`).then(setSummary); api<any>(`/api/dashboard/analytics?course_id=${cs[0].id}`).then(setAnalytics) } })}, []); return <div><h2>Dashboard</h2><pre>{JSON.stringify(summary, null, 2)}</pre><pre>{JSON.stringify(analytics, null, 2)}</pre></div> }

export function ExportPage() {
  const [status, setStatus] = useState(''); const [logs, setLogs] = useState<any[]>([])
  const withCourse = async (cb: (id:number)=>Promise<void>) => { const cs = await api<any[]>('/api/courses'); if(cs[0]) await cb(cs[0].id) }
  return <div><h2>Export</h2><button onClick={()=>withCourse(async id=>{const r=await api<any>(`/api/export/triad369/${id}`,{method:'POST'}); setStatus(r.file)})}>Download Triad369 package</button><button onClick={()=>withCourse(async id=>{try{await api<any>(`/api/publish/coevo/${id}?dry_run=1`,{method:'POST'}); setStatus('dry run ok')}catch(e:any){setStatus(String(e))}})}>Dry Run Publish</button><button onClick={()=>api<any[]>('/api/publish/logs').then(setLogs)}>Publish logs</button><p>{status}</p><pre>{JSON.stringify(logs,null,2)}</pre></div>
}

export function VerifyPage() { const { certId } = useParams(); const [html, setHtml] = useState(''); useEffect(()=>{ fetch(`/api/verify/${certId}`).then(r=>r.text()).then(setHtml)}, [certId]); return <div><h2>Verify certificate</h2><div dangerouslySetInnerHTML={{__html: html}} /></div> }

export function SettingsPage() {
  const [enabled, setEnabled] = useState(localStorage.getItem('growora_reminders') === '1');
  const [windowTime, setWindowTime] = useState(localStorage.getItem('growora_reminder_time') || '18:00');
  const save = async ()=> { localStorage.setItem('growora_reminders', enabled ? '1' : '0'); localStorage.setItem('growora_reminder_time', windowTime); if(enabled && 'Notification' in window){ await Notification.requestPermission() } alert('Saved locally') }
  return <div><h2>Settings</h2><label><input type='checkbox' checked={enabled} onChange={e=>setEnabled(e.target.checked)}/>Enable local reminders</label><input value={windowTime} onChange={e=>setWindowTime(e.target.value)}/><p>Night shift tip: reminders follow your day-start schedule.</p><button onClick={save}>Save</button></div>
}
