import React from 'react'

export default function Header() {
  return (
    <header className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700 shadow-xl">
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-center gap-4 text-white">
        <div className="w-12 h-12 rounded-3xl bg-white/10 shadow-lg flex items-center justify-center">
          <img src="/sopra-logo.png" alt="Sopra Steria" className="h-9 w-auto object-contain" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Agent Test</h1>
          <p className="text-sm text-slate-200">Génération automatisée de scénarios de test</p>
        </div>
      </div>
    </header>
  )
}
