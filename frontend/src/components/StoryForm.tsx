import React, { useState } from 'react'

export interface StoryFormValues {
  mode: 'analysis' | 'pipeline'
  modelAgent1: string
  modelAgent2: string
  modelAgent3: string
  modelAgent4: string
  modelAgent5: string
  useRag: boolean
  useLegacyRag: boolean
  forceRefresh: boolean
  coverageThreshold: number
  maxCorrectionIterations: number
  runAgent4?: boolean
}

interface StoryFormProps {
  onAnalyze: (storyId: string, options: StoryFormValues) => void
  isLoading: boolean
}

const defaultValues: StoryFormValues = {
  mode: 'analysis',
  modelAgent1: 'llama4',
  modelAgent2: 'llama4',
  modelAgent3: 'qwen3',
  modelAgent4: 'qwen3',
  modelAgent5: 'qwen3',
  useRag: false,
  useLegacyRag: true,
  forceRefresh: false,
  coverageThreshold: 0.7,
  maxCorrectionIterations: 2,
  runAgent4: false,
}

export default function StoryForm({ onAnalyze, isLoading }: StoryFormProps) {
  const [storyId, setStoryId] = useState('')
  const [options, setOptions] = useState<StoryFormValues>(defaultValues)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (storyId.trim()) {
      onAnalyze(storyId.trim(), options)
    }
  }

  const setOption = <K extends keyof StoryFormValues>(key: K, value: StoryFormValues[K]) => {
    setOptions((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl shadow-slate-200/40 p-6">
      <div className="mb-6 rounded-3xl bg-gradient-to-r from-red-600 via-fuchsia-600 to-orange-500 p-5 text-white shadow-inner">
        <h2 className="text-xl font-semibold">Analyse Story</h2>
        <p className="text-sm text-white/80 mt-1">Choisis le mode, le modèle et les options RAG</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid gap-3">
          <div>
            <label className="text-sm font-semibold text-slate-700 mb-2 block">Story ID</label>
            <input
              type="text"
              value={storyId}
              onChange={(e) => setStoryId(e.target.value)}
              placeholder="ex: NUXEPM-2144"
              disabled={isLoading}
              className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-slate-50 focus:ring-2 focus:ring-slate-400 focus:border-transparent transition"
            />
          </div>

          <div>
            <label className="text-sm font-semibold text-slate-700 mb-2 block">Mode</label>
            <select
              value={options.mode}
              onChange={(e) => setOption('mode', e.target.value as StoryFormValues['mode'])}
              className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-white focus:ring-2 focus:ring-slate-400 transition"
            >
              <option value="analysis">Analyse simple</option>
              <option value="pipeline">Pipeline complet</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-semibold text-slate-700 mb-2 block">Modèle Agent 1</label>
            <select
              value={options.modelAgent1}
              onChange={(e) => setOption('modelAgent1', e.target.value)}
              className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-white focus:ring-2 focus:ring-slate-400 transition"
            >
              <option value="qwen3">qwen3</option>
              <option value="gptoss">gptoss</option>
              <option value="llama4">llama4</option>
            </select>
          </div>

          {options.mode === 'pipeline' && (
            <>
              <div className="grid gap-3">
                <div>
                  <label className="text-sm font-semibold text-slate-700 mb-2 block">Modèle Agent 2</label>
                  <select
                    value={options.modelAgent2}
                    onChange={(e) => setOption('modelAgent2', e.target.value)}
                    className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-white focus:ring-2 focus:ring-slate-400 transition"
                  >
                    <option value="llama4">llama4</option>
                    <option value="qwen3">qwen3</option>
                    <option value="gptoss">gptoss</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-700 mb-2 block">Modèle Agent 3</label>
                  <select
                    value={options.modelAgent3}
                    onChange={(e) => setOption('modelAgent3', e.target.value)}
                    className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-white focus:ring-2 focus:ring-slate-400 transition"
                  >
                    <option value="llama4">llama4</option>
                    <option value="qwen3">qwen3</option>
                    <option value="gptoss">gptoss</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-700 mb-2 block">Modèle Agent 5</label>
                  <select
                    value={options.modelAgent5}
                    onChange={(e) => setOption('modelAgent5', e.target.value)}
                    className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-white focus:ring-2 focus:ring-slate-400 transition"
                  >
                    <option value="qwen3">qwen3</option>
                    <option value="llama4">llama4</option>
                    <option value="gptoss">gptoss</option>
                  </select>
                </div>
              </div>

              <div className="grid gap-3">
                <label className="block text-sm font-semibold text-slate-700">Agent 4</label>
                <div className="flex items-center gap-3">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={options.runAgent4}
                      onChange={(e) => setOption('runAgent4', e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                    />
                    Exécuter Agent 4 (AUTO/MANUEL)
                  </label>
                </div>
                {options.runAgent4 && (
                  <select
                    value={options.modelAgent4}
                    onChange={(e) => setOption('modelAgent4', e.target.value)}
                    className="w-full px-4 py-3 border border-slate-300 rounded-2xl bg-white focus:ring-2 focus:ring-slate-400 transition"
                  >
                    <option value="qwen3">qwen3</option>
                    <option value="llama4">llama4</option>
                    <option value="gptoss">gptoss</option>
                  </select>
                )}
              </div>

              <div className="grid gap-3">
                <label className="block text-sm font-semibold text-slate-700">Agent 5</label>
                <p className="text-sm text-slate-500">Le pipeline se termine désormais avec Agent 5 pour générer le rapport final.</p>
              </div>
            </>
          )}

          <div className="grid gap-3">
            <label className="block text-sm font-semibold text-slate-700">Options</label>
            <div className="space-y-3 rounded-2xl bg-slate-50 p-4 border border-slate-200">
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.useRag}
                  onChange={(e) => setOption('useRag', e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                />
                Activer le RAG
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.useLegacyRag}
                  onChange={(e) => setOption('useLegacyRag', e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                />
                Activer le RAG legacy tests
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.forceRefresh}
                  onChange={(e) => setOption('forceRefresh', e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                />
                Forcer le rafraîchissement des données
              </label>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading || !storyId.trim()}
            className="w-full px-4 py-3 bg-gradient-to-r from-red-600 to-orange-500 text-white rounded-2xl hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed transition-all font-semibold"
          >
            {isLoading ? '⏳ Analyse en cours...' : '🔍 Lancer l’analyse'}
          </button>
        </div>
      </form>

      <div className="mt-6 rounded-2xl bg-slate-50 p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Résumé</h3>
        <p className="text-sm text-slate-600 leading-6">
          Choisis le mode de fonctionnement : <strong>Analyse simple</strong> utilise uniquement la route `/analysis`, tandis que <strong>Pipeline complet</strong> lance la route `/orchestrator/run` avec l’ensemble des agents.
        </p>
      </div>
    </div>
  )
}
