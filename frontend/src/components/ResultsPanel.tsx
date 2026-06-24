import React from 'react'

interface AnalysisResult {
  storyId: string
  status: 'loading' | 'success' | 'error'
  data?: any
  error?: string
  requestType?: 'analysis' | 'pipeline'
  requestOptions?: Record<string, any>
}

interface ResultsPanelProps {
  result: AnalysisResult
}

function FieldCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900 mb-3">{title}</h3>
      {children}
    </div>
  )
}

export default function ResultsPanel({ result }: ResultsPanelProps) {
  if (result.status === 'loading') {
    return (
      <div className="bg-gradient-to-r from-white via-slate-100 to-sky-50 rounded-3xl border border-slate-200 p-8 shadow-xl flex items-center justify-center min-h-80">
        <div className="text-center">
          <div className="inline-block animate-spin mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <p className="text-slate-700 font-semibold">Analyse en cours...</p>
          <p className="text-sm text-slate-500 mt-1">Cela peut prendre quelques secondes</p>
        </div>
      </div>
    )
  }

  if (result.status === 'error') {
    return (
      <div className="bg-red-50 rounded-3xl border border-red-200 p-6 shadow-sm">
        <div className="flex items-start space-x-3">
          <div className="text-red-700 text-3xl">⚠️</div>
          <div>
            <h3 className="font-semibold text-red-800">Erreur d'analyse</h3>
            <p className="text-sm text-red-700 mt-1">{result.error}</p>
            <p className="text-sm text-slate-500 mt-3">Vérifie que le backend est bien démarré et que le Story ID existe.</p>
          </div>
        </div>
      </div>
    )
  }

  if (!result.data) return null

  const isPipeline = result.requestType === 'pipeline'
  const data = result.data
  const analysisData = isPipeline ? null : data.analysis || data

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <FieldCard title="Requête">
          <div className="space-y-2 text-sm text-slate-700">
            <p>
              <strong>Mode :</strong> {isPipeline ? 'Pipeline complet' : 'Analyse simple'}
            </p>
            <p>
              <strong>Story ID :</strong> {result.storyId}
            </p>
            <p>
              <strong>Model Agent 1 :</strong> {result.requestOptions?.modelAgent1 ?? 'qwen3'}
            </p>
            <p>
              <strong>RAG :</strong> {result.requestOptions?.useRag ? 'activé' : 'désactivé'}
            </p>
            <p>
              <strong>Force refresh :</strong> {result.requestOptions?.forceRefresh ? 'oui' : 'non'}
            </p>
          </div>
        </FieldCard>

        {isPipeline && (
          <FieldCard title="Pipeline complet">
            <div className="space-y-2 text-sm text-slate-700">
              <p>
                <strong>Agent 2 :</strong> {result.requestOptions?.modelAgent2}
              </p>
              <p>
                <strong>Agent 3 :</strong> {result.requestOptions?.modelAgent3}
              </p>
              <p>
                <strong>Agent 4 :</strong> {result.requestOptions?.runAgent4 ? `activé (${result.requestOptions?.modelAgent4})` : 'désactivé'}
              </p>
              <p>
                <strong>Agent 5 :</strong> {result.requestOptions?.modelAgent5}
              </p>
              <p>
                <strong>Seuil couverture :</strong> {result.requestOptions?.coverageThreshold}
              </p>
            </div>
          </FieldCard>
        )}
      </div>

      {isPipeline ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <FieldCard title="Statut final">
            <div className="space-y-2 text-sm text-slate-700">
              <p>
                <strong>Status :</strong> {data.status}
              </p>
              <p>
                <strong>Tests générés :</strong> {data.tests_count ?? 0}
              </p>
              <p>
                <strong>Couverture :</strong> {data.coverage_rate ?? 'N/A'}
              </p>
              <p>
                <strong>Validation :</strong> {data.validation_status ?? 'N/A'}
              </p>
              <p>
                <strong>Durée :</strong> {data.duration_ms ?? 0} ms
              </p>
            </div>
          </FieldCard>

          {data.token_usage && (
            <FieldCard title="Utilisation tokens">
              <pre className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-700 overflow-auto">{JSON.stringify(data.token_usage, null, 2)}</pre>
            </FieldCard>
          )}

          {data.agent2_tests && (
            <FieldCard title="Agent 2">
              <div className="space-y-2 text-sm text-slate-700">
                <p>
                  <strong>Tests :</strong> {data.agent2_tests.length}
                </p>
                <p>
                  <strong>Rapport :</strong> {data.report_status ?? 'N/A'}
                </p>
              </div>
            </FieldCard>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {analysisData && (
            <>
              <FieldCard title="Type de Story">
                <p className="text-xl font-semibold text-slate-900">{analysisData.story_type || 'N/A'}</p>
              </FieldCard>

              {analysisData.testable_points?.length > 0 && (
                <FieldCard title="Points testables">
                  <ul className="space-y-2 text-slate-700 text-sm">
                    {analysisData.testable_points.map((point: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600">✓</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </FieldCard>
              )}

              {analysisData.actors?.length > 0 && (
                <FieldCard title="Acteurs">
                  <div className="flex flex-wrap gap-2">
                    {analysisData.actors.map((actor: string, idx: number) => (
                      <span key={idx} className="inline-block rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800">
                        {actor}
                      </span>
                    ))}
                  </div>
                </FieldCard>
              )}

              {analysisData.business_rules?.length > 0 && (
                <FieldCard title="Règles métier">
                  <ul className="space-y-2 text-slate-700 text-sm">
                    {analysisData.business_rules.map((rule: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-slate-400">•</span>
                        <span>{rule}</span>
                      </li>
                    ))}
                  </ul>
                </FieldCard>
              )}

              {(analysisData.acceptance_criteria_explicit || analysisData.acceptance_criteria_inferred) && (
                <FieldCard title="Critères d'acceptation">
                  {analysisData.acceptance_criteria_explicit && (
                    <div className="mb-3">
                      <p className="text-sm font-semibold text-slate-700">Explicites</p>
                      <p className="text-sm text-slate-600">{analysisData.acceptance_criteria_explicit}</p>
                    </div>
                  )}
                  {analysisData.acceptance_criteria_inferred && (
                    <div>
                      <p className="text-sm font-semibold text-slate-700">Inférés</p>
                      <p className="text-sm text-slate-600">{analysisData.acceptance_criteria_inferred}</p>
                    </div>
                  )}
                </FieldCard>
              )}

              {analysisData.quality_score != null && (
                <FieldCard title="Score de qualité">
                  <p className="text-3xl font-semibold text-slate-900">{analysisData.quality_score.toFixed(1)}/10</p>
                </FieldCard>
              )}
            </>
          )}
        </div>
      )}

      <FieldCard title="Données brutes">
        <pre className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-700 overflow-auto max-h-72">{JSON.stringify(data, null, 2)}</pre>
      </FieldCard>
    </div>
  )
}
