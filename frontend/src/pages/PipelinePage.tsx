import React from 'react'
import { useOrchestrator } from '../hooks'
import { Loader } from '../components/ui/Loader'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { ManualTestsTable } from '../components/tests/ManualTestsTable'
import { useToast } from '../contexts/ToastContext'
import { Play, Square } from 'lucide-react'

export const PipelinePage: React.FC = () => {
  const [storyId, setStoryId] = React.useState('')
  const [useRag, setUseRag] = React.useState(true)
  const [useLegacyRag, setUseLegacyRag] = React.useState(false)
  const [runAgent4, setRunAgent4] = React.useState(true)
  const [manualTests, setManualTests] = React.useState<any[]>([])

  const toast = useToast()
  const orchestrator = useOrchestrator(storyId)
  const { data, loading, error, progress, isCompleted, isFailed, run, cancel } = orchestrator

  const handleRun = async () => {
    if (!storyId.trim()) return
    try {
      const resp = await run({
        use_rag: useRag,
        use_legacy_rag: useLegacyRag,
        run_agent4: runAgent4,
        force_refresh: false,
      })
      const tests = (resp as any)?.agent2_tests || (resp as any)?.result?.agent2_tests || []
      setManualTests(tests)
      if (isCompleted || (resp as any)?.status === 'completed') {
        toast.success('Pipeline completed successfully')
      }
    } catch (err: any) {
      toast.error(err?.message || 'Pipeline failed')
    }
  }

  React.useEffect(() => {
    if (data) {
      const tests = (data as any)?.agent2_tests || (data as any)?.result?.agent2_tests || []
      if (tests.length) setManualTests(tests)
    }
  }, [data])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-navy">Pipeline Orchestrator</h1>
        <p className="text-sm text-gray-600 mt-1">Run the full AI-powered test generation pipeline</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader title="Settings" />
          <CardBody className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-brand-navy mb-1.5">Story ID</label>
              <input
                type="text"
                placeholder="e.g., NUXEPM-2144"
                value={storyId}
                onChange={(e) => setStoryId(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div className="space-y-2">
              {[
                { label: 'Use RAG Context', checked: useRag, onChange: setUseRag },
                { label: 'Use Legacy RAG', checked: useLegacyRag, onChange: setUseLegacyRag },
                { label: 'Run Agent 4 Report', checked: runAgent4, onChange: setRunAgent4 },
              ].map((opt) => (
                <label key={opt.label} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={opt.checked}
                    onChange={(e) => opt.onChange(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  {opt.label}
                </label>
              ))}
            </div>

            {loading ? (
              <Button variant="danger" fullWidth onClick={cancel}>
                <Square size={16} />
                Stop
              </Button>
            ) : (
              <Button variant="primary" fullWidth disabled={!storyId} onClick={handleRun}>
                <Play size={16} />
                Run Pipeline
              </Button>
            )}
          </CardBody>
        </Card>

        <div className="lg:col-span-3 space-y-4">
          {error && (
            <Alert type="error" title="Pipeline Error" description={error.message} />
          )}

          {!data && !loading && (
            <Card className="py-12 text-center">
              <p className="text-gray-600">Enter a Story ID and click Run Pipeline to start</p>
            </Card>
          )}

          {loading && (
            <Card className="py-12">
              <Loader size="lg" text="Running pipeline..." />
            </Card>
          )}

          {data && (
            <Card>
              <CardHeader
                title="Pipeline Execution"
                description={`Story: ${(data as any).storyId || storyId}`}
                action={
                  <Badge variant={isCompleted ? 'success' : isFailed ? 'error' : 'warning'}>
                    {(data as any).status}
                  </Badge>
                }
              />
              <CardBody>
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-brand-navy">Progress</span>
                    <span className="text-sm font-bold">{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-brand-red h-full transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                {(data as any).steps?.length > 0 && (
                  <div className="space-y-2">
                    {(data as any).steps.map((step: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 bg-brand-bg rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-brand-navy text-sm">{step.agent}</p>
                          {step.error && <p className="text-xs text-red-600 mt-0.5">{step.error}</p>}
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
                )}

                {isCompleted && (
                  <Alert
                    type="success"
                    title="Pipeline Completed"
                    description="All agents finished successfully"
                    className="mt-4"
                  />
                )}
              </CardBody>
            </Card>
          )}

          {manualTests.length > 0 && storyId && (
            <ManualTestsTable
              tests={manualTests}
              storyId={storyId}
              onTestsChange={setManualTests}
            />
          )}
        </div>
      </div>
    </div>
  )
}
