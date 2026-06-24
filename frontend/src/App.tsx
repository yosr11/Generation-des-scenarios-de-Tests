import React, { useState } from 'react'
import { Navbar } from './components/layout'
import { DashboardPage, PipelinePage, AnalysisPage, HistoryPage } from './pages'

function App() {
  const [currentPage, setCurrentPage] = useState('pipeline')

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />
      case 'pipeline':
        return <PipelinePage />
      case 'analysis':
        return <AnalysisPage />
      case 'history':
        return <HistoryPage />
      default:
        return <PipelinePage />
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <Navbar currentPage={currentPage} onPageChange={setCurrentPage} />
      <main className="flex-1">
        {renderPage()}
      </main>
    </div>
  )
}

export default App

