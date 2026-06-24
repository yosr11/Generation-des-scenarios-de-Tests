import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export const AppLayout: React.FC = () => {
  return (
    <div className="flex min-h-screen bg-brand-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-brand-navy text-white flex items-center px-6 shadow-sm shrink-0">
          <p className="text-sm text-white/80">AI-powered test generation &amp; validation</p>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
