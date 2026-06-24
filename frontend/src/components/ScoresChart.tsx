import React from 'react'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface TestScore {
  storyId: string
  storyName: string
  score: number
  status: 'pass' | 'fail' | 'pending'
}

interface ScoresChartProps {
  data: TestScore[]
}

export default function ScoresChart({ data }: ScoresChartProps) {
  // Limiter à 10 derniers tests pour la lisibilité
  const chartData = data.slice(-10)

  const labels = chartData.map(d => d.storyName.substring(0, 15) + '...')
  const scores = chartData.map(d => d.score)
  const colors = chartData.map(d => {
    if (d.score >= 9) return '#10b981'
    if (d.score >= 7) return '#3b82f6'
    if (d.score >= 5) return '#f59e0b'
    return '#ef4444'
  })

  const dataset = {
    labels,
    datasets: [
      {
        label: 'Score de Qualité (0-10)',
        data: scores,
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 2,
        borderRadius: 8,
        tension: 0.3,
        fill: false,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: true,
        labels: {
          usePointStyle: true,
          padding: 15,
          font: { size: 12 },
        },
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 10,
        grid: {
          drawBorder: false,
          color: '#e5e7eb',
        },
        ticks: {
          font: { size: 11 },
        },
      },
      x: {
        grid: {
          display: false,
          drawBorder: false,
        },
        ticks: {
          font: { size: 10 },
        },
      },
    },
  }

  return (
    <div className="chart-container">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Scores de Qualité Récents</h3>
      <Bar data={dataset} options={options} height={300} />
    </div>
  )
}
