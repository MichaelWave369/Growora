import { Link, Route, Routes } from 'react-router-dom'
import { DashboardPage, ExportPage, FlashcardsPage, HomePage, IntakePage, LessonPage, TodayPage, CoursePage } from './pages'

export function App() {
  return (
    <div className="app">
      <nav>
        <Link to="/">Growora</Link> | <Link to="/intake">Intake</Link> | <Link to="/today">Today</Link> | <Link to="/flashcards">Flashcards</Link> | <Link to="/dashboard">Dashboard</Link> | <Link to="/export">Export</Link>
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/intake" element={<IntakePage />} />
        <Route path="/course/:id" element={<CoursePage />} />
        <Route path="/today" element={<TodayPage />} />
        <Route path="/lesson/:lessonId" element={<LessonPage />} />
        <Route path="/flashcards" element={<FlashcardsPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/export" element={<ExportPage />} />
      </Routes>
    </div>
  )
}
