import React, { useState, useEffect } from 'react'
import KPICard from '../components/KPICard'
import ScoresChart from '../components/ScoresChart'
import TestsTable from '../components/TestsTable'
import { getDashboardStats, getTestScores } from '../api/dashboard'

interface DashboardStats {
  totalStories: number
  totalTests: number
  passRate: number
  avgScore: number
}

interface TestScore {
  storyId: string
  storyName: string
  score: number
  status: 'pass' | 'fail' | 'pending'
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalStories: 0,
    totalTests: 0,
    passRate: 0,
    avgScore: 0,
  })
  const [scores, setScores] = useState<TestScore[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const statsData = await getDashboardStats()
        const scoresData = await getTestScores()
        setStats(statsData)
        setScores(scoresData)
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-xl text-gray-600">Chargement des données...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard Agent Test</h1>
        <p className="text-gray-600 mt-2">Génération et suivi des scénarios de test automatisés</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Total Stories"
          value={stats.totalStories}
          icon="📖"
          bgColor="bg-blue-50"
          borderColor="border-blue-200"
        />
        <KPICard
          title="Tests Générés"
          value={stats.totalTests}
          icon="✅"
          bgColor="bg-green-50"
          borderColor="border-green-200"
        />
        <KPICard
          title="Taux de Réussite"
          value={`${stats.passRate}%`}
          icon="📈"
          bgColor="bg-purple-50"
          borderColor="border-purple-200"
        />
        <KPICard
          title="Score Moyen"
          value={`${stats.avgScore.toFixed(1)}/10`}
          icon="⭐"
          bgColor="bg-yellow-50"
          borderColor="border-yellow-200"
        />
      </div>

      {/* Charts and Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ScoresChart data={scores} />
        </div>
        <div className="chart-container">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Distribution des Scores</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Excellent (9-10)</span>
              <span className="text-lg font-bold text-green-600">{scores.filter(s => s.score >= 9).length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Bon (7-8)</span>
              <span className="text-lg font-bold text-blue-600">{scores.filter(s => s.score >= 7 && s.score < 9).length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Moyen (5-6)</span>
              <span className="text-lg font-bold text-yellow-600">{scores.filter(s => s.score >= 5 && s.score < 7).length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">À améliorer (&lt;5)</span>
              <span className="text-lg font-bold text-red-600">{scores.filter(s => s.score < 5).length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tests Table */}
      <TestsTable data={scores} />
    </div>
  )
}
