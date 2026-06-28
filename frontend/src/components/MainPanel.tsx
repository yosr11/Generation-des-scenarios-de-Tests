import React, { useState } from 'react'
import StoryForm, { StoryFormValues } from './StoryForm'
import ResultsPanel from './ResultsPanel'

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
        response = await fetch(`/api/orchestrator/run/${encodeURIComponent(storyId)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            use_rag: options.useRag,
            use_legacy_rag: options.useLegacyRag,
            model_agent1: options.modelAgent1,
            model_agent2: options.modelAgent2,
            model_agent3_quality: options.modelAgent3,
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
      setResults({ storyId, status: 'success', data, requestType: options.mode, requestOptions: options })
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
