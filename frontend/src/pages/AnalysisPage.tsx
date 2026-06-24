import React from 'react'
import { useAnalysis, useAgent5Report } from '../hooks'
import { Loader } from '../components/ui/Loader'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { useToast } from '../contexts/ToastContext'

export const AnalysisPage: React.FC = () => {
  const [storyId, setStoryId] = React.useState('')
  const [submitted, setSubmitted] = React.useState(false)
  const toast = useToast()

  const analysis = useAnalysis(storyId)
  const report = useAgent5Report(submitted ? storyId : undefined)

  const handleAnalyze = async () => {
    if (!storyId.trim()) return
    setSubmitted(true)
    try {
      await analysis.run({ use_rag: true })
      toast.success('Analysis completed')
    } catch (err: any) {
      toast.error(err?.message || 'Analysis failed')
    }
  }

  const handleGenerateReport = async () => {
    try {
      await report.generate({ include_recommendations: true })
      toast.success('Report generated')
    } catch (err: any) {
      toast.error(err?.message || 'Report generation failed')
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-navy">Analysis</h1>
        <p className="text-sm text-gray-600 mt-1">Perform detailed analysis and generate test scenarios</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader title="Options" />
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
            <Button
              variant="primary"
              fullWidth
              disabled={!storyId}
              isLoading={analysis.loading}
              onClick={handleAnalyze}
            >
              Analyze
            </Button>
          </CardBody>
        </Card>

        <div className="lg:col-span-3 space-y-4">
          {analysis.error && (
            <Alert type="error" title="Analysis Error" description={analysis.error.message} />
          )}

          {analysis.loading ? (
            <Card className="py-12">
              <Loader size="lg" text="Analyzing story..." />
            </Card>
          ) : analysis.data ? (
            <>
              {analysis.data.testable_points && (
                <Card>
                  <CardHeader title="Testable Points" />
                  <CardBody>
                    <ul className="space-y-2">
                      {analysis.data.testable_points.map((point: string, idx: number) => (
                        <li key={idx} className="flex gap-2 text-sm text-gray-700">
                          <span className="text-brand-orange font-bold">✓</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  </CardBody>
                </Card>
              )}

              {submitted && (
                <Card>
                  <CardBody>
                    <Button
                      variant="primary"
                      fullWidth
                      isLoading={report.loading}
                      onClick={handleGenerateReport}
                    >
                      Generate Agent5 Report
                    </Button>
                  </CardBody>
                </Card>
              )}

              {report.data && (
                <Card>
                  <CardHeader
                    title="Report Generated"
                    action={<Badge variant="success">Complete</Badge>}
                  />
                  <CardBody className="space-y-4">
                    <div>
                      <p className="text-sm font-medium text-brand-navy mb-1">Verdict</p>
                      <Badge
                        variant={
                          report.data.verdict === 'APPROVED'
                            ? 'success'
                            : report.data.verdict === 'REQUIRES_REVIEW'
                            ? 'warning'
                            : 'error'
                        }
                      >
                        {report.data.verdict}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-brand-navy mb-1">Summary</p>
                      <p className="text-sm text-gray-600">{report.data.summary}</p>
                    </div>
                  </CardBody>
                </Card>
              )}
            </>
          ) : (
            <Card className="py-12 text-center">
              <p className="text-gray-600">
                {submitted ? 'No results available' : 'Enter a Story ID and click Analyze to start'}
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
