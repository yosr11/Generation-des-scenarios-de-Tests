import React from 'react'
import { useAnalysis, useAgent5Report } from '../hooks'
import { Loader } from '../components/ui/Loader'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'

export const AnalysisPage: React.FC = () => {
  const [storyId, setStoryId] = React.useState('')
  const [submitted, setSubmitted] = React.useState(false)

  const analysis = useAnalysis(submitted ? storyId : undefined)
  const report = useAgent5Report(submitted ? storyId : undefined)

  const handleAnalyze = async () => {
    if (!storyId.trim()) return
    setSubmitted(true)
  }

  const handleGenerateReport = async () => {
    await report.generate({ include_recommendations: true })
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">🔍 Analysis</h1>
      <p className="text-gray-600 mb-8">Perform detailed analysis and generate test scenarios</p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Input */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Analysis Options</h2>

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

            <button
              onClick={handleAnalyze}
              disabled={!storyId || analysis.loading}
              className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Analyze
            </button>
          </div>
        </div>

        {/* Right Side - Results */}
        <div className="lg:col-span-3 space-y-4">
          {analysis.error && (
            <Alert
              type="error"
              title="Analysis Error"
              description={analysis.error.message}
            />
          )}

          {analysis.loading ? (
            <div className="bg-white border border-gray-200 rounded-lg p-8">
              <div className="flex justify-center">
                <Loader size="lg" text="Analyzing story..." />
              </div>
            </div>
          ) : analysis.data ? (
            <>
              {/* Testable Points */}
              {analysis.data.testable_points && (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Testable Points</h3>
                  <ul className="space-y-2">
                    {analysis.data.testable_points.map((point: string, idx: number) => (
                      <li key={idx} className="flex gap-2 p-2 rounded hover:bg-gray-50">
                        <span className="text-blue-600 font-bold">✓</span>
                        <span className="text-gray-700">{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Scenarios */}
              {analysis.data.scenarios && analysis.data.scenarios.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">
                    Generated Scenarios ({analysis.data.scenarios.length})
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-2 px-3 font-semibold">Action</th>
                          <th className="text-left py-2 px-3 font-semibold">Data</th>
                          <th className="text-left py-2 px-3 font-semibold">Expected Result</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.data.scenarios.map((scenario: any, idx: number) => (
                          <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-2 px-3">{scenario.action}</td>
                            <td className="py-2 px-3 text-gray-600">{scenario.data || 'N/A'}</td>
                            <td className="py-2 px-3 text-gray-600">
                              {scenario.expected_result || 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Generate Report Button */}
              {submitted && (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <button
                    onClick={handleGenerateReport}
                    disabled={report.loading}
                    className="w-full bg-green-600 text-white py-2 rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-400"
                  >
                    Generate Agent5 Report
                  </button>
                </div>
              )}

              {/* Report Results */}
              {report.data && (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold">Report Generated</h3>
                    <Badge variant="success">Complete</Badge>
                  </div>

                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Verdict</p>
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

                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Summary</p>
                    <p className="text-gray-600">{report.data.summary}</p>
                  </div>

                  {report.data.recommendations && report.data.recommendations.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">Recommendations</p>
                      <ul className="space-y-2">
                        {report.data.recommendations.map((rec: string, idx: number) => (
                          <li key={idx} className="flex gap-2 text-gray-600">
                            <span className="text-amber-600">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : submitted ? (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <p className="text-gray-600">No results available</p>
            </div>
          ) : (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <p className="text-gray-600">Enter a Story ID and click "Analyze" to start</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}