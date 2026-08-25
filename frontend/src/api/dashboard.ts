import axios from 'axios'
import { API_BASE_URL } from './client'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

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

/**
 * Récupère les statistiques du dashboard
 * À adapter selon ton API réelle
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    // Exemple: remplace par ton endpoint réel
    const response = await api.get('/api/stats/dashboard')
    return response.data
  } catch (error) {
    console.error('Error fetching dashboard stats:', error)
    // Retour des données de démonstration
    return {
      totalStories: 45,
      totalTests: 128,
      passRate: 87,
      avgScore: 8.5,
    }
  }
}

/**
 * Récupère les scores des tests
 * À adapter selon ton API réelle
 */
export async function getTestScores(): Promise<TestScore[]> {
  try {
    // Exemple: remplace par ton endpoint réel
    const response = await api.get('/api/tests/scores')
    return response.data
  } catch (error) {
    console.error('Error fetching test scores:', error)
    // Retour des données de démonstration
    return [
      { storyId: 'NUXEPM-2144', storyName: 'User Registration', score: 9.2, status: 'pass' },
      { storyId: 'NUXEPM-2143', storyName: 'Login Flow', score: 8.7, status: 'pass' },
      { storyId: 'NUXEPM-1412', storyName: 'Password Reset', score: 8.5, status: 'pass' },
      { storyId: 'NUXEPM-1345', storyName: 'User Profile', score: 7.9, status: 'pass' },
      { storyId: 'NUXEPM-1234', storyName: 'Permissions', score: 8.1, status: 'pass' },
      { storyId: 'NUXEPM-1123', storyName: 'Data Filtering', score: 6.8, status: 'pending' },
      { storyId: 'NUXEPM-1023', storyName: 'Error Handling', score: 7.5, status: 'pass' },
      { storyId: 'NUXEPM-0923', storyName: 'Export Reports', score: 5.2, status: 'fail' },
    ]
  }
}

/**
 * Lance l'analyse d'une story
 */
export async function analyzeStory(storyId: string) {
  try {
    const response = await api.post(`/api/analysis/${storyId}`)
    return response.data
  } catch (error) {
    console.error(`Error analyzing story ${storyId}:`, error)
    throw error
  }
}

/**
 * Lance la génération de tests
 */
export async function generateTests(storyId: string, model: string = 'llama4') {
  try {
    const response = await api.post(`/api/manual-tests/generate/${storyId}`, {
      model_alias: model,
    })
    return response.data
  } catch (error) {
    console.error(`Error generating tests for ${storyId}:`, error)
    throw error
  }
}

export default api
