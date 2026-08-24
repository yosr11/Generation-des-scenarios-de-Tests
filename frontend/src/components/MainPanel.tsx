import React, { useState } from 'react'
import StoryForm, { StoryFormValues } from './StoryForm'
import ResultsPanel from './ResultsPanel'
import { apiClient } from '../api/client'

interface AnalysisResult {
  storyId: string
  status: 'loading' | 'success' | 'error'
  data?: any
  error?: string
  requestType?: 'analysis' | 'pipeline'
  requestOptions?: StoryFormValues
}

export default function MainPanel() {
  const [results, setResults] = useState<AnalysisResult | null>(null)

  const handleAnalyze = async (storyId: string, options: StoryFormValues) => {
    setResults({ storyId, status: 'loading', requestType: options.mode, requestOptions: options })

    try {
      let response: Response

      if (options.mode === 'pipeline') {
        let confirmed = true
        try {
          await apiClient.db.getStory(storyId)
          confirmed = window.confirm(
            `Cette story existe déjà dans l'historique. Voulez-vous relancer l'exécution pour ${storyId} ?`
          )
        } catch (error: any) {
          if (error.status !== 404) {
            throw error
          }
        }

        if (!confirmed) {
          setResults(null)
          return
        }

        response = await fetch(`/api/orchestrator/run/${encodeURIComponent(storyId)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            use_rag: options.useRag,
            use_legacy_rag: options.useLegacyRag,
            model_agent1: options.modelAgent1,
            model_agent2: options.modelAgent2,
            model_agent4_quality: options.modelAgent4,
            model_agent5: options.modelAgent5,
            coverage_threshold: options.coverageThreshold,
            max_correction_iterations: options.maxCorrectionIterations,
            force_refresh: options.forceRefresh,
          }),
        })
      } else {
        response = await fetch(
          `/api/analysis/${encodeURIComponent(storyId)}?model_alias=${encodeURIComponent(options.modelAgent1)}&use_rag=${options.useRag}&force_refresh=${options.forceRefresh}`,
        )
      }

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Analyse impossible (${response.status}) : ${errorText}`)
      }

      const data = await response.json()

      // Si pipeline : lancer un polling sur /orchestrator/status/{jobId}
      if (options.mode === 'pipeline') {
        const jobId = data.storyId || storyId
        // Mettre à jour l'UI avec le job initial
        setResults({ storyId, status: 'success', data, requestType: options.mode, requestOptions: options })

        // Poller jusqu'à obtention du résultat final (job.result non nul) ou statut final
        const poll = async () => {
          for (let i = 0; i < 60; i++) {
            try {
              const st = await fetch(`/api/orchestrator/status/${encodeURIComponent(jobId)}`)
              if (!st.ok) break
              const job = await st.json()
              // Si le job contient le résultat, afficher le résultat final (pipeline JSON)
              if (job.result) {
                setResults({ storyId, status: 'success', data: job.result, requestType: options.mode, requestOptions: options })
                return
              }
              // Sinon mettre à jour l'affichage du job (progression)
              setResults({ storyId, status: 'success', data: job, requestType: options.mode, requestOptions: options })
            } catch (e) {
              // Ignore et réessaye
            }
            await new Promise((r) => setTimeout(r, 2000))
          }
        }

        poll()
      } else {
        setResults({ storyId, status: 'success', data, requestType: options.mode, requestOptions: options })
      }
    } catch (error) {
      setResults({ storyId, status: 'error', error: String(error), requestType: options.mode, requestOptions: options })
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <StoryForm onAnalyze={handleAnalyze} isLoading={results?.status === 'loading'} />
        </div>

        <div className="lg:col-span-2">
          {results && <ResultsPanel result={results} />}
          {!results && (
            <div className="rounded-3xl border border-dashed border-slate-300 bg-white/80 p-10 text-center shadow-sm backdrop-blur-sm">
              <p className="text-lg font-semibold text-slate-900 mb-2">Entrez un Story ID pour lancer l'analyse</p>
              <p className="text-sm text-slate-500">Par exemple : NUXEPM-2144</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
