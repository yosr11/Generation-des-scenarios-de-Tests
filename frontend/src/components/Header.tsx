import React from 'react'

export default function Header() {
  return (
    <header className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700 shadow-xl">
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-center gap-4 text-white">
        <img src="/synapTest1.png" alt="Synaptest" className="h-12 w-auto object-contain"
          style={{ filter: 'grayscale(1) brightness(1.75)', opacity: 0.95 }} />
        <div>
          <h1 className="text-2xl font-semibold">Agent Test</h1>
          <p className="text-sm text-slate-200">Génération automatisée de scénarios de test</p>
        </div>
      </div>
    </header>
  )
}
