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

function JsonSection({ title, content }: { title: string; content: any }) {
  if (!content) return null

  return (
    <FieldCard title={title}>
      <pre className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-700 overflow-auto max-h-72">
        {JSON.stringify(content, null, 2)}
      </pre>
    </FieldCard>
  )
}

function resolveImageUrl(url?: string) {
  if (!url) return undefined
  if (url.startsWith('http') || url.startsWith('data:') || url.startsWith('/api')) return url
  if (url.startsWith('/documents/')) return `/api${url}`
  return url
}

function ImageGallery({ images, title = 'Images' }: { images: any[]; title?: string }) {
  if (!images || images.length === 0) return null
  return (
    <FieldCard title={title}>
      <div className="grid gap-4 sm:grid-cols-2">
        {images.map((image, idx) => {
          const src = resolveImageUrl(image.url)
          return (
            <div key={idx} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              {src ? (
                <div className="h-48 overflow-hidden rounded-2xl bg-slate-100">
                  <img
                    src={src}
                    alt={image.alt_text || image.caption || `Image ${idx + 1}`}
                    className="h-full w-full object-cover"
                  />
                </div>
              ) : (
                <div className="h-48 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 text-sm">
                  Image sans URL
                </div>
              )}
              <div className="mt-4 space-y-2 text-slate-700 text-sm">
                {image.caption && <p className="font-semibold text-slate-900">{image.caption}</p>}
                {image.description && <p className="whitespace-pre-wrap">{image.description}</p>}
              </div>
            </div>
          )
        })}
      </div>
    </FieldCard>
  )
}

function RagContextSection({ ragContext }: { ragContext: any[] }) {
  if (!ragContext || ragContext.length === 0) return null
  return (
    <FieldCard title="Contexte RAG">
      <div className="space-y-4">
        {ragContext.map((item, idx) => (
          <div key={idx} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
            {item.source && (
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500 font-semibold mb-2">{item.source}</p>
            )}
            <p className="text-sm text-slate-700 whitespace-pre-wrap">
              {item.text || item.content || JSON.stringify(item)}
            </p>
          </div>
        ))}
      </div>
    </FieldCard>
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
                <strong>Agent 5 :</strong> {result.requestOptions?.modelAgent5}
              </p>
              <p>
                <strong>Seuil couverture :</strong> {result.requestOptions?.coverageThreshold}
              </p>
            </div>
          </FieldCard>
        )}
      </div>

      {isPipeline && data?.story && (
        <div className="mt-4">
          <FieldCard title="User Story">
            <div className="space-y-2 text-sm text-slate-700">
              <p><strong>ID :</strong> {data.story.id || result.storyId}</p>
              <p><strong>Résumé :</strong> {data.story.summary || data.story.title || 'N/A'}</p>
              {data.story.description && (
                <div>
                  <p className="text-sm font-semibold text-slate-700">Description</p>
                  <p className="text-sm text-slate-600 whitespace-pre-wrap">{data.story.description}</p>
                </div>
              )}
            </div>
          </FieldCard>
        </div>
      )}

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

          {data.agent1_analysis && (
            <FieldCard title="Agent 1">
              <div className="space-y-2 text-sm text-slate-700">
                {data.agent1_analysis.story_title && (
                  <p><strong>Story :</strong> {data.agent1_analysis.story_title}</p>
                )}
                {data.agent1_analysis.story_type && (
                  <p><strong>Type :</strong> {data.agent1_analysis.story_type}</p>
                )}
                {data.agent1_analysis.actors?.length > 0 && (
                  <p><strong>Acteurs :</strong> {data.agent1_analysis.actors.join(', ')}</p>
                )}
                {data.agent1_analysis.actions?.length > 0 && (
                  <p><strong>Actions :</strong> {data.agent1_analysis.actions.join('; ')}</p>
                )}
                {data.agent1_analysis.testable_points?.length > 0 && (
                  <p><strong>Points testables :</strong> {data.agent1_analysis.testable_points.length}</p>
                )}
              </div>
            </FieldCard>
          )}

          {data.agent15_business_model && (
            <FieldCard title="Agent 1.5">
              <div className="space-y-2 text-sm text-slate-700">
                {data.agent15_business_model.business_goals?.length != null && (
                  <p><strong>Objectifs :</strong> {data.agent15_business_model.business_goals.length}</p>
                )}
                {data.agent15_business_model.business_workflows?.length != null && (
                  <p><strong>Workflows :</strong> {data.agent15_business_model.business_workflows.length}</p>
                )}
                {data.agent15_business_model.modeling_notes && (
                  <p><strong>Notes :</strong> {data.agent15_business_model.modeling_notes}</p>
                )}
              </div>
            </FieldCard>
          )}

          {data.agent2_tests && (
            <FieldCard title="Agent 2">
              <div className="space-y-2 text-sm text-slate-700">
                <p>
                  <strong>Tests :</strong> {data.agent2_tests.length}
                </p>
                {data.agent2_tests[0]?.test_name && (
                  <p><strong>Premier test :</strong> {data.agent2_tests[0].test_name}</p>
                )}
                <p>
                  <strong>Rapport :</strong> {data.report_status ?? 'N/A'}
                </p>
              </div>
            </FieldCard>
          )}

          {data.agent3_validation && (
            <FieldCard title="Agent 3">
              <div className="space-y-2 text-sm text-slate-700">
                {data.agent3_validation.validation_status && (
                  <p><strong>Validation :</strong> {data.agent3_validation.validation_status}</p>
                )}
                {data.agent3_validation.report?.coverage_rate != null && (
                  <p><strong>Couverture :</strong> {data.agent3_validation.report.coverage_rate}</p>
                )}
                {data.agent3_validation.report?.ambiguity_count != null && (
                  <p><strong>Ambiguïtés :</strong> {data.agent3_validation.report.ambiguity_count}</p>
                )}
              </div>
            </FieldCard>
          )}

          {data.agent5_report && (
            <FieldCard title="Agent 5">
              <div className="space-y-2 text-sm text-slate-700">
                {data.agent5_report.report_title && (
                  <p><strong>Rapport :</strong> {data.agent5_report.report_title}</p>
                )}
                {data.agent5_report.executive_summary?.overall_status && (
                  <p><strong>Statut :</strong> {data.agent5_report.executive_summary.overall_status}</p>
                )}
                {data.agent5_report.coverage_metrics?.coverage_rate != null && (
                  <p><strong>Couverture :</strong> {data.agent5_report.coverage_metrics.coverage_rate}%</p>
                )}
              </div>
            </FieldCard>
          )}

          {(data.story?.legacy_examples || data.legacy_examples)?.length > 0 && (
            <JsonSection title="Exemples legacy RAG" content={data.story?.legacy_examples || data.legacy_examples} />
          )}

          {(data.story?.rag_context || data.rag_context)?.length > 0 && (
            <RagContextSection ragContext={data.story?.rag_context || data.rag_context} />
          )}

          {(data.story?.images || data.images)?.length > 0 && (
            <ImageGallery images={data.story?.images || data.images} title="Images Agent 1" />
          )}

          {data.agent1_analysis && (
            <JsonSection title="Agent 1 Analysis" content={data.agent1_analysis} />
          )}

          {data.agent2_tests && data.agent2_tests.length > 0 && (
            <JsonSection title="Agent 2 Tests" content={data.agent2_tests} />
          )}

          {data.agent3_validation && (
            <JsonSection title="Agent 3 Validation" content={data.agent3_validation} />
          )}

          {data.agent5_report && (
            <JsonSection title="Agent 5 Report" content={data.agent5_report} />
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
