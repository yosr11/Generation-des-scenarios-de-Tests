import React from 'react'
import { useOrchestrator } from '../hooks'
import { Loader } from '../components/ui/Loader'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Play, Square } from 'lucide-react'

export const PipelinePage: React.FC = () => {
  const [storyId, setStoryId] = React.useState('')
  const [useRag, setUseRag] = React.useState(true)
  const [useLegacyRag, setUseLegacyRag] = React.useState(false)
  const [runAgent4, setRunAgent4] = React.useState(true)

  const orchestrator = useOrchestrator(storyId)
  const { data, loading, error, progress, isCompleted, isFailed, run, cancel } = orchestrator

  const handleRun = async () => {
    if (!storyId.trim()) return
    await run({
      use_rag: useRag,
      use_legacy_rag: useLegacyRag,
      run_agent4: runAgent4,
      force_refresh: false,
    })
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">🔧 Pipeline Orchestrator</h1>
      <p className="text-gray-600 mb-8">Run the full AI-powered test generation pipeline</p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Input */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Settings</h2>

            {/* Story ID Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Story ID</label>
              <input
                type="text"
                placeholder="e.g., NUXEPM-2144"
                value={storyId}
                onChange={(e) => setStoryId(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Checkboxes */}
            <div className="mb-6 space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useRag}
                  onChange={(e) => setUseRag(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm text-gray-700">Use RAG Context</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useLegacyRag}
                  onChange={(e) => setUseLegacyRag(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm text-gray-700">Use Legacy RAG</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={runAgent4}
                  onChange={(e) => setRunAgent4(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm text-gray-700">Run Agent 4 Report</span>
              </label>
            </div>

            {/* Run Button */}
            {loading ? (
              <button
                onClick={cancel}
                className="w-full bg-red-600 text-white py-2 rounded-lg font-medium hover:bg-red-700 flex items-center justify-center gap-2"
              >
                <Square size={18} />
                Stop
              </button>
            ) : (
              <button
                onClick={handleRun}
                disabled={!storyId}
                className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Play size={18} />
                Run Pipeline
              </button>
            )}
          </div>
        </div>

        {/* Right Side - Results */}
        <div className="lg:col-span-3 space-y-4">
          {error && (
            <Alert
              type="error"
              title="Pipeline Error"
              description={error.message}
            />
          )}

          {!data && !loading && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <p className="text-gray-600">Enter a Story ID and click "Run Pipeline" to start</p>
            </div>
          )}

          {loading && (
            <div className="bg-white border border-gray-200 rounded-lg p-8">
              <div className="flex justify-center mb-4">
                <Loader size="lg" text="Running pipeline..." />
              </div>
            </div>
          )}

          {data && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-semibold">Pipeline Execution</h3>
                  <p className="text-sm text-gray-600">Story: {data.storyId}</p>
                </div>
                <Badge
                  variant={
                    isCompleted ? 'success' : isFailed ? 'error' : loading ? 'warning' : 'default'
                  }
                >
                  {data.status}
                </Badge>
              </div>

              {/* Progress Bar */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Progress</span>
                  <span className="text-sm font-medium text-gray-900">{progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-600 h-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              {/* Pipeline Steps */}
              {data.steps && data.steps.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-semibold mb-3 text-gray-900">Pipeline Steps</h4>
                  <div className="space-y-2">
                    {data.steps.map((step: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">{step.agent}</p>
                          {step.error && (
                            <p className="text-sm text-red-600 mt-1">{step.error}</p>
                          )}
                        </div>
                        <Badge
                          variant={
                            step.status === 'completed'
                              ? 'success'
                              : step.status === 'failed'
                              ? 'error'
                              : 'warning'
                          }
                        >
                          {step.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {isCompleted && (
                <Alert
                  type="success"
                  title="✅ Pipeline Completed"
                  description="All agents have completed their analysis successfully"
                />
              )}

              {isFailed && (
                <Alert
                  type="error"
                  title="❌ Pipeline Failed"
                  description="An error occurred during pipeline execution"
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}