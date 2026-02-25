import { useEffect, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { BackupPage, CourseEditPage, CoursePage, DashboardPage, ExportPage, FlashcardsPage, ForgePage, HomePage, IntakePage, LessonPage, LibraryPage, MasteryPage, ProfilesPage, SessionPage, SettingsPage, SkillMapPage, StudioImportPage, StudioPage, TodayPage, VerifyPage } from './pages'
import { api } from './api/client'

export function App() {
  const [profiles, setProfiles] = useState<any[]>([])
  const [drawer, setDrawer] = useState(false)
  const [msg, setMsg] = useState('')
  const [chat, setChat] = useState<any[]>([])

  const loadProfiles = () => api<any[]>('/api/profiles').then(setProfiles).catch(() => {})
  useEffect(loadProfiles, [])
  const switchProfile = async (id: string) => {
    localStorage.setItem('growora_profile_id', id)
    await api(`/api/profiles/${id}/select`, { method: 'POST' })
    window.location.reload()
  }

  const askTutor = async () => {
    const r = await api<any>('/api/tutor/chat', { method: 'POST', body: JSON.stringify({ message: msg, privacy_mode: true }) })
    setChat([...chat, { role: 'user', content: msg }, { role: 'assistant', content: r.response }])
    setMsg('')
  }

  return (
    <div className="app">
      <nav>
        <Link to="/">Growora</Link> | <Link to="/profiles">Profiles</Link> | <Link to="/intake">Intake</Link> | <Link to="/today">Today</Link> | <Link to="/library">Library</Link> | <Link to="/forge">Forge</Link> | <Link to="/skillmap">SkillMap</Link> | <Link to="/mastery">Mastery</Link> | <Link to="/studio">Studio</Link> | <Link to="/flashcards">Flashcards</Link> | <Link to="/dashboard">Dashboard</Link> | <Link to="/export">Export</Link> | <Link to="/settings">Settings</Link> | <Link to="/settings/backup">Backup</Link>
        <select onChange={(e)=>switchProfile(e.target.value)} value={localStorage.getItem('growora_profile_id') || ''}>
          <option value="">Profile</option>
          {profiles.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
        </select>
        <button onClick={()=>setDrawer(!drawer)}>Tutor</button>
      </nav>
      {drawer && <aside style={{position:'fixed', right:10, top:60, width:300, background:'#fff', border:'1px solid #ddd', padding:10}}>
        <h4>Tutor</h4>
        <div style={{maxHeight:200, overflow:'auto'}}>{chat.map((c,i)=><p key={i}><b>{c.role}</b>: {c.content}</p>)}</div>
        <input value={msg} onChange={e=>setMsg(e.target.value)} /><button onClick={askTutor}>Send</button>
      </aside>}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/profiles" element={<ProfilesPage />} />
        <Route path="/intake" element={<IntakePage />} />
        <Route path="/course/:id" element={<CoursePage />} />
        <Route path="/course/:id/edit" element={<CourseEditPage />} />
        <Route path="/today" element={<TodayPage />} />
        <Route path="/session/:id" element={<SessionPage />} />
        <Route path="/lesson/:lessonId" element={<LessonPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/forge" element={<ForgePage />} />
        <Route path="/skillmap" element={<SkillMapPage />} />
        <Route path="/mastery" element={<MasteryPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/studio/import" element={<StudioImportPage />} />
        <Route path="/flashcards" element={<FlashcardsPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/export" element={<ExportPage />} />
        <Route path="/verify/:certId" element={<VerifyPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/backup" element={<BackupPage />} />
      </Routes>
    </div>
  )
}
