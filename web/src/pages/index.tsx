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

export function SkillMapPage() {
  const [courseId, setCourseId] = useState<number>()
  const [graph, setGraph] = useState<any>()
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=>{ if(cs[0]) { setCourseId(cs[0].id); api<any>(`/api/graph?course_id=${cs[0].id}`).then(setGraph) }})},[])
  const rebuild = async ()=> { if(!courseId) return; await api(`/api/graph/rebuild?course_id=${courseId}`,{method:'POST'}); setGraph(await api<any>(`/api/graph?course_id=${courseId}`)) }
  return <div><h2>Skill Map</h2><button onClick={rebuild}>Rebuild Graph</button>
    <div style={{display:'flex',gap:12,flexWrap:'wrap'}}>{(graph?.concepts||[]).slice(0,80).map((c:any)=><div key={c.id} style={{border:'1px solid #ddd',padding:8,background: (graph?.mastery?.[c.id]?.bucket==='Mastered'?'#bbf7d0':graph?.mastery?.[c.id]?.bucket==='Comfortable'?'#bfdbfe':graph?.mastery?.[c.id]?.bucket==='Learning'?'#fde68a':'#fecaca')}}>{c.title}<br/><small>{graph?.mastery?.[c.id]?.bucket||'New'}</small></div>)}</div>
    <pre>{JSON.stringify((graph?.edges||[]).slice(0,40),null,2)}</pre>
  </div>
}

export function MasteryPage() {
  const [rows, setRows] = useState<any[]>([])
  const [filter, setFilter] = useState('')
  useEffect(()=>{ api<any[]>('/api/courses').then(cs=> cs[0] && api<any[]>(`/api/mastery?course_id=${cs[0].id}`).then(setRows))},[])
  const filtered = rows.filter(r=> !filter || (r.bucket||'').toLowerCase().includes(filter.toLowerCase()))
  return <div><h2>Mastery Map</h2><input placeholder='filter bucket' value={filter} onChange={e=>setFilter(e.target.value)}/><button onClick={()=>alert('Start concept-based review from /today session')}>Start Review Session</button><pre>{JSON.stringify(filtered,null,2)}</pre></div>
}

export function StudioPage() {
  const [title,setTitle]=useState('New Draft'); const [topic,setTopic]=useState('General'); const [template,setTemplate]=useState('Guitar Beginner'); const [status,setStatus]=useState('')
  const create = async ()=>{ const r=await api<any>('/api/studio/course',{method:'POST',body:JSON.stringify({title,topic,template})}); setStatus(`Created course ${r.id}`) }
  const gen = async ()=>{ const cs=await api<any[]>('/api/courses'); if(!cs[0]) return; const c=await api<any>(`/api/courses/${cs[0].id}`); const ids=(c.lessons||[]).slice(0,3).map((l:any)=>l.id); await api('/api/studio/lesson/generate',{method:'POST',body:JSON.stringify({lesson_ids:ids})}); setStatus('Generated selected lessons') }
  return <div><h2>Studio</h2><input value={title} onChange={e=>setTitle(e.target.value)}/><input value={topic} onChange={e=>setTopic(e.target.value)}/><select value={template} onChange={e=>setTemplate(e.target.value)}><option>Kids Math</option><option>Coding Basics</option><option>Guitar Beginner</option><option>Tech for Seniors</option></select><button onClick={create}>Create Draft</button><button onClick={gen}>Generate content for selected lessons</button><a href='/studio/import'>Go to Import</a><p>{status}</p></div>
}

export function StudioImportPage() {
  const [status,setStatus]=useState('')
  const mdImport = async (e: FormEvent<HTMLFormElement>)=>{ e.preventDefault(); const fd=new FormData(e.currentTarget); const r=await fetch('/api/studio/import/markdown',{method:'POST',body:fd,headers:{'X-Growora-Profile': localStorage.getItem('growora_profile_id')||''}}); setStatus(await r.text()) }
  const pdfImport = async (e: FormEvent<HTMLFormElement>)=>{ e.preventDefault(); const fd=new FormData(e.currentTarget); const r=await fetch('/api/studio/import/pdf_outline',{method:'POST',body:fd,headers:{'X-Growora-Profile': localStorage.getItem('growora_profile_id')||''}}); setStatus(await r.text()) }
  return <div><h2>Studio Import</h2><form onSubmit={mdImport}><input name='title' defaultValue='Imported Markdown'/><textarea name='markdown_text' defaultValue='# Lesson 1\nIntro\n# Lesson 2\nPractice'/><button>Import markdown</button></form><form onSubmit={pdfImport}><input name='title' defaultValue='Imported PDF'/><input name='file' type='file'/><button>Import PDF outline</button></form><pre>{status}</pre></div>
}

export function BackupPage() {
  const [status,setStatus]=useState('')
  const create = async (e: FormEvent<HTMLFormElement>)=>{ e.preventDefault(); const fd=new FormData(e.currentTarget); const r=await fetch('/api/backup/create',{method:'POST',body:fd}); setStatus(await r.text()) }
  const restore = async (e: FormEvent<HTMLFormElement>)=>{ e.preventDefault(); const fd=new FormData(e.currentTarget); const r=await fetch('/api/backup/restore',{method:'POST',body:fd,headers:{'X-Growora-Profile': localStorage.getItem('growora_profile_id')||''}}); setStatus(await r.text()) }
  return <div><h2>Backup & Restore</h2><form onSubmit={create}><label><input type='checkbox' name='include_attachments'/>Include attachments</label><label><input type='checkbox' name='include_exports' defaultChecked/>Include exports</label><button>Create backup</button></form><form onSubmit={restore}><input type='file' name='file'/><label><input type='checkbox' name='overwrite'/>Overwrite DB</label><button>Restore backup</button></form><pre>{status}</pre></div>
}

export function ClassroomsPage() {
  const [rooms, setRooms] = useState<any[]>([])
  const [name, setName] = useState('Family Classroom')
  const [courseId, setCourseId] = useState<number | null>(null)
  const [profiles, setProfiles] = useState<any[]>([])
  const [selectedProfile, setSelectedProfile] = useState<number | null>(null)
  const nav = useNavigate()
  const load = async ()=>{
    setRooms(await api<any[]>('/api/classrooms'))
    const cs = await api<any[]>('/api/courses'); if(cs[0]) setCourseId(cs[0].id)
    const ps = await api<any[]>('/api/profiles'); setProfiles(ps); if(ps[0]) setSelectedProfile(ps[0].id)
  }
  useEffect(()=>{ load() },[])
  const create = async ()=>{ await api('/api/classrooms',{method:'POST',body:JSON.stringify({name})}); load() }
  const start = async (id:number)=>{ if(!courseId) return; const s=await api<any>(`/api/classrooms/${id}/sessions/start`,{method:'POST',body:JSON.stringify({course_id:courseId,agenda:['Warmup','Practice','Teach-back'],mode:'live',title:'Live tutoring'})}); nav(`/classroom/${id}/session/${s.id}`) }
  const addMember = async (id:number)=>{ if(!selectedProfile) return; await api(`/api/classrooms/${id}/members`,{method:'POST',body:JSON.stringify({profile_id:selectedProfile,role:'learner'})}); load() }
  return <div><h2>Classroom Mode</h2><input value={name} onChange={e=>setName(e.target.value)}/><button onClick={create}>Create classroom</button>
    <div><label>Add member profile:</label><select value={selectedProfile || ''} onChange={e=>setSelectedProfile(Number(e.target.value))}><option value=''>select</option>{profiles.map(p=><option key={p.id} value={p.id}>{p.display_name}</option>)}</select></div>
    <ul>{rooms.map(r=><li key={r.id}>{r.name} <button onClick={()=>addMember(r.id)}>Add member</button> <button onClick={()=>start(r.id)}>Start session</button></li>)}</ul></div>
}

export function ClassroomPage() {
  const { classroomId, sessionId } = useParams()
  const [detail, setDetail] = useState<any>()
  const [summary, setSummary] = useState<any>()
  const [drawMode, setDrawMode] = useState<'pen'|'erase'|'line'|'rect'|'circle'|'text'>('pen')
  const [kiosk, setKiosk] = useState(false)
  const canvasRef = (globalThis as any).__classCanvasRef || ((globalThis as any).__classCanvasRef = { current: null as HTMLCanvasElement | null })
  const [stack, setStack] = useState<string[]>([])
  const [redoStack, setRedoStack] = useState<string[]>([])
  const [chatQ, setChatQ] = useState('')
  const [deck, setDeck] = useState<any>()
  const [slideIdx, setSlideIdx] = useState(0)
  const [liveQuiz, setLiveQuiz] = useState<any>()
  const [teachPrompt, setTeachPrompt] = useState<any>()
  const [teachResp, setTeachResp] = useState('')
  const [lanRoom, setLanRoom] = useState<any>()
  const [lanStatus, setLanStatus] = useState<any>()
  const [readAloud, setReadAloud] = useState(false)
  const [dictate, setDictate] = useState(false)

  const load = ()=> api<any>(`/api/classrooms/sessions/${sessionId}`).then(setDetail)
  useEffect(()=>{ load(); const t=setInterval(load,1500); return ()=>clearInterval(t)},[sessionId])

  useEffect(()=>{
    const c = canvasRef.current as HTMLCanvasElement | null
    if(!c) return
    const ctx = c.getContext('2d')!
    ctx.lineWidth = 2; ctx.strokeStyle = '#0f172a'; ctx.lineCap = 'round'
    let drawing=false, sx=0, sy=0
    const pos=(e:any)=>{
      const r=c.getBoundingClientRect();
      const t=e.touches?.[0];
      return {x:(t?t.clientX:e.clientX)-r.left,y:(t?t.clientY:e.clientY)-r.top}
    }
    const down=(e:any)=>{ drawing=true; const p=pos(e); sx=p.x; sy=p.y; if(drawMode==='text'){ const txt=prompt('Text')||''; ctx.fillText(txt,sx,sy); sendDraw({mode:'text',x:sx,y:sy,text:txt}); snapshot() } }
    const move=(e:any)=>{ if(!drawing || drawMode==='text') return; e.preventDefault?.(); const p=pos(e); if(drawMode==='pen'||drawMode==='erase'){ ctx.globalCompositeOperation = drawMode==='erase'?'destination-out':'source-over'; ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(p.x,p.y); ctx.stroke(); sendDraw({mode:drawMode,from:[sx,sy],to:[p.x,p.y]}); sx=p.x; sy=p.y } }
    const up=(e:any)=>{ if(!drawing) return; drawing=false; const p=pos(e); if(['line','rect','circle'].includes(drawMode)){ ctx.globalCompositeOperation='source-over'; if(drawMode==='line'){ ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(p.x,p.y); ctx.stroke() } if(drawMode==='rect'){ ctx.strokeRect(sx,sy,p.x-sx,p.y-sy) } if(drawMode==='circle'){ const r=Math.hypot(p.x-sx,p.y-sy); ctx.beginPath(); ctx.arc(sx,sy,r,0,Math.PI*2); ctx.stroke() } sendDraw({mode:drawMode,from:[sx,sy],to:[p.x,p.y]}) }
      snapshot()
    }
    c.addEventListener('mousedown',down); c.addEventListener('mousemove',move); window.addEventListener('mouseup',up)
    c.addEventListener('touchstart',down,{passive:false}); c.addEventListener('touchmove',move,{passive:false}); window.addEventListener('touchend',up)
    return ()=>{ c.removeEventListener('mousedown',down); c.removeEventListener('mousemove',move); window.removeEventListener('mouseup',up); c.removeEventListener('touchstart',down as any); c.removeEventListener('touchmove',move as any); window.removeEventListener('touchend',up as any)}
  },[drawMode])

  const sendDraw = async (payload:any)=> api(`/api/classrooms/sessions/${sessionId}/event`,{method:'POST',body:JSON.stringify({type:'draw',payload})})
  const snapshot = ()=>{
    const c = canvasRef.current as HTMLCanvasElement | null; if(!c) return
    const data = c.toDataURL('image/png'); setStack([...stack,data]); setRedoStack([])
  }
  const undo = ()=>{ if(stack.length<2) return; const c=canvasRef.current as HTMLCanvasElement; const ctx=c.getContext('2d')!; const ns=[...stack]; const last=ns.pop()!; setRedoStack([...redoStack,last]); const img=new Image(); img.onload=()=>{ctx.clearRect(0,0,c.width,c.height); ctx.drawImage(img,0,0)}; img.src=ns[ns.length-1]; setStack(ns) }
  const redo = ()=>{ if(!redoStack.length) return; const c=canvasRef.current as HTMLCanvasElement; const ctx=c.getContext('2d')!; const rs=[...redoStack]; const imgData=rs.pop()!; const img=new Image(); img.onload=()=>{ctx.drawImage(img,0,0)}; img.src=imgData; setRedoStack(rs); setStack([...stack,imgData]) }
  const clearBoard = ()=>{ const c=canvasRef.current as HTMLCanvasElement; c.getContext('2d')!.clearRect(0,0,c.width,c.height); snapshot() }
  const saveBoard = async ()=>{ const c=canvasRef.current as HTMLCanvasElement; const blob=await new Promise<Blob|null>(r=>c.toBlob(r)); if(!blob) return; const fd=new FormData(); fd.append('file',blob,'snapshot.png'); await fetch(`/api/classrooms/sessions/${sessionId}/whiteboard/snapshot`,{method:'POST',body:fd}) }
  const exportPNG = ()=>{ const c=canvasRef.current as HTMLCanvasElement; const a=document.createElement('a'); a.href=c.toDataURL('image/png'); a.download=`whiteboard_${sessionId}.png`; a.click() }

  const makeDeck = async ()=>{ const cs=await api<any[]>(`/api/courses`); if(!cs[0]) return; const c=await api<any>(`/api/courses/${cs[0].id}`); const lesson=c.lessons?.[0]; if(!lesson) return; const d=await api<any>(`/api/classrooms/sessions/${sessionId}/deck/from_lesson?lesson_id=${lesson.id}`,{method:'POST'}); setDeck(await api<any>(`/api/classrooms/sessions/${sessionId}/deck/${d.id}`)); setSlideIdx(0) }
  const present = async ()=>{ if(!deck?.deck?.id) return; await api(`/api/classrooms/sessions/${sessionId}/present`,{method:'POST',body:JSON.stringify({deck_id:deck.deck.id,slide_index:slideIdx})}) }

  const createQuiz = async ()=>{ const cs=await api<any[]>('/api/courses'); if(!cs[0]) return; await api(`/api/graph/rebuild?course_id=${cs[0].id}`,{method:'POST'}); const g=await api<any>(`/api/graph?course_id=${cs[0].id}`); const concept=g.concepts?.[0]; const q=await api<any>(`/api/classrooms/sessions/${sessionId}/livequiz/create`,{method:'POST',body:JSON.stringify({title:'Quick poll',concept_id:concept?.id,questions_json:[{prompt:'Do you get it?',answer:'yes'}]})}); await api(`/api/classrooms/livequiz/${q.id}/open`,{method:'POST'}); setLiveQuiz(q) }
  const submitQuiz = async ()=>{ const pid=Number(localStorage.getItem('growora_profile_id')||0); if(!liveQuiz||!pid) return; await api(`/api/classrooms/livequiz/${liveQuiz.id}/submit`,{method:'POST',body:JSON.stringify({profile_id:pid,answers:['yes']})}); alert('Submitted') }

  const createTeach = async ()=>{ const cs=await api<any[]>('/api/courses'); if(!cs[0]) return; const g=await api<any>(`/api/graph?course_id=${cs[0].id}`); const concept=g.concepts?.[0]; if(!concept) return; const p=await api<any>(`/api/classrooms/sessions/${sessionId}/teachback/create`,{method:'POST',body:JSON.stringify({concept_id:concept.id})}); setTeachPrompt(p) }
  const submitTeach = async ()=>{ const pid=Number(localStorage.getItem('growora_profile_id')||0); if(!teachPrompt||!pid) return; const r=await api<any>(`/api/classrooms/teachback/${teachPrompt.id}/submit`,{method:'POST',body:JSON.stringify({profile_id:pid,response_text:teachResp})}); alert(r.feedback_md) }
  const applyTeach = async ()=>{ if(!teachPrompt) return; await api(`/api/classrooms/teachback/${teachPrompt.id}/apply_mastery`,{method:'POST'}); alert('Applied to mastery') }

  const confused = async ()=>{ await api(`/api/classrooms/sessions/${sessionId}/event`,{method:'POST',body:JSON.stringify({type:'confused',payload:{q:chatQ}})}); setChatQ('') }
  const endSession = async ()=>{ await api(`/api/classrooms/sessions/${sessionId}/end`,{method:'POST'}); setSummary(await api<any>(`/api/classrooms/sessions/${sessionId}/summary`)) }
  const assignHomework = async ()=>{ const members=detail?.members||[]; const refs=[1,2,3]; for(const m of members){ await api(`/api/classrooms/sessions/${sessionId}/assign`,{method:'POST',body:JSON.stringify({profile_id:m.profile_id,kind:'drill',ref_id:refs[0]})}) } alert('Homework assigned') }
  const summaryPdf = ()=>{ const w=window.open('','_blank'); if(!w||!summary) return; w.document.write('<pre>'+JSON.stringify(summary,null,2)+'</pre>'); w.print() }
  const startNext = ()=> window.location.reload()


  const createLanRoom = async ()=>{ const r=await api<any>('/api/lan/rooms/create',{method:'POST',body:JSON.stringify({classroom_id:Number(classroomId),session_id:Number(sessionId)})}); setLanRoom(r); setLanStatus(await api<any>(`/api/lan/rooms/${r.room_code}/status`)) }
  const refreshLan = async ()=>{ if(!lanRoom?.room_code) return; setLanStatus(await api<any>(`/api/lan/rooms/${lanRoom.room_code}/status`)) }
  const approveClient = async (id:number)=>{ const pid=Number(localStorage.getItem('growora_profile_id')||1); await api(`/api/lan/rooms/${lanRoom.room_code}/approve`,{method:'POST',body:JSON.stringify({client_id:id,profile_id:pid,permissions:{view:true,draw:true,quiz:true,teachback:true}})}); refreshLan() }
  const denyClient = async (id:number)=>{ await api(`/api/lan/rooms/${lanRoom.room_code}/deny`,{method:'POST',body:JSON.stringify({client_id:id})}); refreshLan() }
  const rotateLan = async ()=>{ if(!lanRoom?.room_code) return; setLanRoom(await api<any>(`/api/lan/rooms/${lanRoom.room_code}/rotate`,{method:'POST'})) }

  const readText = (t:string)=>{ if(readAloud && 'speechSynthesis' in window){ const u=new SpeechSynthesisUtterance(t); window.speechSynthesis.speak(u) } }
  const doDictate = ()=>{
    const SR=(window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    if(!dictate || !SR) return
    const rec = new SR(); rec.lang='en-US'; rec.onresult=(e:any)=> setTeachResp((e.results?.[0]?.[0]?.transcript)||teachResp); rec.start()
  }

  useEffect(()=>{ if(teachPrompt?.prompt) readText(teachPrompt.prompt) },[teachPrompt,readAloud])

  return <div style={{display:'grid',gridTemplateColumns:'240px 1fr 320px',gap:8}}>
    <section><h3>Agenda</h3><pre>{JSON.stringify(detail?.agenda||[],null,2)}</pre><h4>Members</h4><pre>{JSON.stringify(detail?.members||[],null,2)}</pre><button onClick={()=>setKiosk(!kiosk)}>Kiosk {kiosk?'Off':'On'}</button>{kiosk&&document.documentElement.requestFullscreen?.()}</section>
    <section>
      <h3>Whiteboard</h3>
      <div><select value={drawMode} onChange={e=>setDrawMode(e.target.value as any)}><option>pen</option><option>erase</option><option>line</option><option>rect</option><option>circle</option><option>text</option></select>
      <button onClick={undo}>Undo</button><button onClick={redo}>Redo</button><button onClick={clearBoard}>Clear</button><button onClick={saveBoard}>Save Snapshot</button><button onClick={exportPNG}>Export PNG</button></div>
      <canvas ref={(el)=>{canvasRef.current=el}} width={800} height={440} style={{border:'1px solid #ccc',touchAction:'none'}} />
      <h4>Presenter</h4><button onClick={makeDeck}>Generate Deck</button><button onClick={()=>setSlideIdx(Math.max(0,slideIdx-1))}>Prev</button><button onClick={()=>setSlideIdx(slideIdx+1)}>Next</button><button onClick={present}>Push slide</button><pre>{JSON.stringify(deck?.slides?.[slideIdx]||{},null,2)}</pre>
      <h4>Learner quick signal</h4><input value={chatQ} onChange={e=>setChatQ(e.target.value)} placeholder="I'm confused because..."/><button onClick={confused}>Send</button>
    </section>
    <section>
      <h3>Teacher Panel</h3>
      <button onClick={createQuiz}>Create Live Quiz</button><button onClick={submitQuiz}>Submit as learner</button>
      <button onClick={createTeach}>Create Teach-back</button><textarea value={teachResp} onChange={e=>setTeachResp(e.target.value)} placeholder='Explain concept in your words' /><button onClick={submitTeach}>Submit Teach-back</button><button onClick={applyTeach}>Apply to Mastery</button>
      <div><label><input type='checkbox' checked={readAloud} onChange={e=>setReadAloud(e.target.checked)} />Read instructions aloud</label></div>
      <div><label><input type='checkbox' checked={dictate} onChange={e=>setDictate(e.target.checked)} />Dictate teach-back</label><button onClick={doDictate}>Start dictation</button></div>

      <h4>LAN Room</h4><button onClick={createLanRoom}>Create Room</button><button onClick={refreshLan}>Refresh</button><button onClick={rotateLan}>Rotate Code</button>{lanRoom && <div><p>Code: {lanRoom.room_code}</p><p>Join: {lanRoom.join_url}</p><img src={`/api/lan/rooms/${lanRoom.room_code}/qr.png`} alt='lan qr' style={{width:180}}/></div>}{lanStatus && <div><h5>Pending</h5>{(lanStatus.pending_clients||[]).map((c:any)=><div key={c.id}>{c.client_name} <button onClick={()=>approveClient(c.id)}>Approve</button><button onClick={()=>denyClient(c.id)}>Deny</button></div>)}<h5>Approved</h5><pre>{JSON.stringify(lanStatus.approved_clients||[],null,2)}</pre></div>}
      <button onClick={endSession}>End Session</button>
      {summary && <><h4>Session Summary</h4><pre>{JSON.stringify(summary,null,2)}</pre><button onClick={summaryPdf}>Export Summary PDF</button><button onClick={assignHomework}>Assign homework</button><button onClick={startNext}>Start next session</button></>}
    </section>
  </div>
}

export function LanHostPage() {
  const [net, setNet] = useState<any>()
  const [rooms, setRooms] = useState<any[]>([])
  const [selected, setSelected] = useState<any>()
  const [qr, setQr] = useState('')
  const [pairing, setPairing] = useState<any>()

  const load = async () => {
    setNet(await api<any>('/api/network/addresses'))
    const cs = await api<any[]>('/api/classrooms')
    setRooms(cs)
  }
  useEffect(()=>{ load() },[])

  const createRoom = async () => {
    const classes = await api<any[]>('/api/classrooms')
    if(!classes[0]) return alert('Create classroom first')
    const det = await api<any>(`/api/classrooms/${classes[0].id}/sessions/start`, {method:'POST', body: JSON.stringify({course_id: (await api<any[]>('/api/courses'))[0]?.id || 1, agenda:['LAN'], mode:'live', title:'LAN Session'})})
    const room = await api<any>('/api/lan/rooms/create', {method:'POST', body: JSON.stringify({classroom_id: classes[0].id, session_id: det.id})})
    setSelected(room)
    setQr(`/api/lan/rooms/${room.room_code}/qr.png`)
  }

  const rotate = async () => {
    if(!selected?.room_code) return
    setSelected(await api<any>(`/api/lan/rooms/${selected.room_code}/rotate`, {method:'POST'}))
  }
  const createPairing = async () => {
    if(!selected?.room_code) return
    const fd = new FormData(); fd.append('room_code', selected.room_code); fd.append('scope','learning_record_only'); fd.append('days','30'); fd.append('events','500')
    const r = await fetch('/api/lan/sync/pairing/create',{method:'POST', body:fd}); setPairing(await r.json())
  }

  return <div><h2>LAN Host Mode</h2>
    <p style={{color:'#b91c1c'}}>Warning: LAN mode exposes host to your Wi-Fi network. Use private networks only.</p>
    <pre>{JSON.stringify(net,null,2)}</pre>
    <button onClick={createRoom}>Create LAN room</button>
    {selected && <div><p>Join URL: {selected.join_url}</p><button onClick={()=>navigator.clipboard.writeText(selected.join_url)}>Copy join link</button><button onClick={rotate}>Rotate room code</button><button onClick={createPairing}>Request Sync From Learner</button>{pairing && <pre>{JSON.stringify(pairing,null,2)}</pre>}{qr && <img src={qr} alt='qr' style={{width:220}}/>}</div>}
  </div>
}

export function JoinRoomPage() {
  const { roomCode } = useParams();
  const [name, setName] = useState('Learner')
  const [status, setStatus] = useState('')
  const nav = useNavigate()
  const join = async () => {
    const r = await api<any>(`/api/lan/rooms/${roomCode}/join`, {method:'POST', body: JSON.stringify({client_name:name,device_type:'web'})})
    localStorage.setItem('growora_lan_token', r.token)
    localStorage.setItem('growora_lan_client_id', String(r.client_id))
    setStatus('Waiting for approval...')
    const poll = setInterval(async ()=>{
      try{
        const st = await api<any>(`/api/lan/rooms/${roomCode}/status`)
        const me = (st.approved_clients||[]).find((c:any)=> String(c.id)===localStorage.getItem('growora_lan_client_id'))
        if(me){ clearInterval(poll); nav(`/lan/session/${roomCode}`) }
      }catch{}
    },1500)
  }
  return <div><h2>Join LAN Room {roomCode}</h2><input value={name} onChange={e=>setName(e.target.value)}/><button onClick={join}>Connect</button><p>{status}</p></div>
}

export function LanSessionPage() {
  const { roomCode } = useParams();
  const [msgs, setMsgs] = useState<any[]>([])
  const [connected, setConnected] = useState(false)
  const [draw, setDraw] = useState(true)
  const [text, setText] = useState('')
  const [pairCode, setPairCode] = useState('')
  const [syncPass, setSyncPass] = useState('')
  const wsRef = (globalThis as any).__lanws || ((globalThis as any).__lanws = { current: null as WebSocket | null })

  useEffect(()=>{
    const token = localStorage.getItem('growora_lan_token') || ''
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/lan/${roomCode}?token=${encodeURIComponent(token)}`)
    wsRef.current = ws
    ws.onopen = ()=>setConnected(true)
    ws.onmessage = (ev)=>{ try { setMsgs(m=>[...m, JSON.parse(ev.data)].slice(-120)) } catch {} }
    ws.onclose = ()=>setConnected(false)
    return ()=> ws.close()
  },[roomCode])

  const send = (type:string,payload:any)=> wsRef.current?.send(JSON.stringify({type, ts:new Date().toISOString(), room_code: roomCode, payload}))
  const sendSync = async (f?: File) => {
    if(!f || !pairCode) return
    const fd = new FormData(); fd.append('room_code', roomCode || ''); fd.append('pairing_code', pairCode); fd.append('passphrase', syncPass); fd.append('file', f)
    const r = await fetch('/api/lan/sync/upload', {method:'POST', body:fd, headers:{Authorization:`Bearer ${localStorage.getItem('growora_lan_token')||''}`}})
    alert(await r.text())
  }

  return <div><h2>LAN Learner Session {roomCode}</h2><p>{connected ? 'Connected' : 'Disconnected'}</p>
    <button onClick={()=>send('slide_present',{deck_id:1,slide_index:1})}>Sync slide</button>
    <button disabled={!draw} onClick={()=>send('whiteboard_draw',{stroke:[[1,2],[3,4]]})}>Draw stroke</button>
    <button onClick={()=>send('livequiz_submit',{answers:['A']})}>Submit quiz</button>
    <textarea value={text} onChange={e=>setText(e.target.value)} placeholder='Teach-back response'/><button onClick={()=>send('teachback_submit',{response:text})}>Submit teach-back</button>
    <h4>Send progress to host</h4><input value={pairCode} onChange={e=>setPairCode(e.target.value)} placeholder='Pairing code'/><input type='password' value={syncPass} onChange={e=>setSyncPass(e.target.value)} placeholder='Passphrase'/><input type='file' accept='.zip,.growora-sync.zip' onChange={e=>sendSync(e.target.files?.[0])}/>
    <button onClick={()=>{ localStorage.removeItem('growora_lan_token'); location.href='/' }}>Disconnect</button>
    <pre>{JSON.stringify(msgs,null,2)}</pre>
  </div>
}

export function SyncSettingsPage() {
  const [profileId, setProfileId] = useState('1')
  const [scope, setScope] = useState('learning_record_only')
  const [days, setDays] = useState('30')
  const [events, setEvents] = useState('1000')
  const [passphrase, setPassphrase] = useState('')
  const [importPass, setImportPass] = useState('')
  const [result, setResult] = useState<any>()
  const [audit, setAudit] = useState<any[]>([])

  const loadAudit = ()=> api<any[]>('/api/sync/audit').then(setAudit).catch(()=>{})
  useEffect(()=>{ loadAudit() },[])

  const exportPkg = async ()=> {
    const fd = new FormData()
    fd.append('profile_id', profileId)
    fd.append('scope', scope)
    fd.append('days', days)
    fd.append('events', events)
    fd.append('passphrase', passphrase)
    const r = await fetch('/api/sync/export', { method:'POST', body: fd })
    if(!r.ok) return alert(await r.text())
    const blob = await r.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `growora-${profileId}.growora-sync.zip`
    a.click()
    loadAudit()
  }

  const importPkg = async (f?: File)=> {
    if(!f) return
    const fd = new FormData()
    fd.append('file', f)
    fd.append('passphrase', importPass)
    const r = await fetch('/api/sync/import', { method:'POST', body: fd })
    const j = await r.json()
    setResult(j)
    loadAudit()
  }

  return <div><h2>Offline Sync</h2>
    <p>Encrypted Triad369 sync package export/import. Keep passphrases private.</p>
    <h4>Export</h4>
    <input value={profileId} onChange={e=>setProfileId(e.target.value)} placeholder='Profile ID'/>
    <select value={scope} onChange={e=>setScope(e.target.value)}><option>learning_record_only</option><option>include_sessions</option><option>include_notes</option></select>
    <input value={days} onChange={e=>setDays(e.target.value)} placeholder='Days'/>
    <input value={events} onChange={e=>setEvents(e.target.value)} placeholder='Events limit'/>
    <input type='password' value={passphrase} onChange={e=>setPassphrase(e.target.value)} placeholder='Passphrase'/>
    <button onClick={exportPkg}>Export .growora-sync.zip</button>
    <h4>Import</h4>
    <input type='password' value={importPass} onChange={e=>setImportPass(e.target.value)} placeholder='Passphrase'/>
    <input type='file' accept='.zip,.growora-sync.zip' onChange={e=>importPkg(e.target.files?.[0])}/>
    <pre>{JSON.stringify(result,null,2)}</pre>
    <h4>Sync Audit</h4>
    <pre>{JSON.stringify(audit,null,2)}</pre>
  </div>
}
