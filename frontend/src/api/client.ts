/**
 * Centralized API client with Axios
 * Handles all communication with FastAPI backend
 * Provides proper error handling, loading states, and request/response types
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios'

// ─────────────────────────────────────────────────────────────
// API Configuration
// ─────────────────────────────────────────────────────────────

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Create Axios instance with default config
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000,
  withCredentials: true,
})

// ─────────────────────────────────────────────────────────────
// Response/Error Types
// ─────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  status?: number
}

export interface ApiError {
  message: string
  status?: number
  details?: any
}

// ─────────────────────────────────────────────────────────────
// Request/Response Types for All Endpoints
// ─────────────────────────────────────────────────────────────

// Orchestrator
export interface OrchestratorRequest {
  use_rag?: boolean
  use_legacy_rag?: boolean
  model_agent1?: string
  model_agent2?: string
  model_agent3_quality?: string
  model_agent4?: string
  model_agent5?: string
  coverage_threshold?: number
  max_correction_iterations?: number
  force_refresh?: boolean
  run_agent4?: boolean
}

export interface PipelineStep {
  agent: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: any
  error?: string
  startTime?: string
  endTime?: string
}

export interface OrchestratorResponse {
  storyId: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  steps: PipelineStep[]
  result?: any
  error?: string
}

// Analysis
export interface AnalysisRequest {
  model_alias?: string
  use_rag?: boolean
  force_refresh?: boolean
}

export interface AnalysisResponse {
  storyId: string
  enriched_story?: any
  analysis?: any
  testable_points?: string[]
  scenarios?: any[]
  tests?: any[]
  recommendations?: string[]
}

// Story
export interface Story {
  id: string
  title: string
  description?: string
  epic?: string
  priority?: string
  created_at?: string
  updated_at?: string
}

// Scenario
export interface Scenario {
  id: string
  storyId: string
  title: string
  description?: string
  preconditions?: string[]
  steps?: ScenarioStep[]
}

export interface ScenarioStep {
  action: string
  data: string
  expected_result: string
}

// Manual Test
export interface ManualTest {
  id: string
  storyId: string
  title: string
  steps?: TestStep[]
  status?: 'pass' | 'fail' | 'pending'
}

export interface TestStep {
  action: string
  data: string
  expected_result: string
}

// Agent5 Report
export interface Agent5ReportRequest {
  include_recommendations?: boolean
  format?: 'json' | 'markdown'
}

export interface Agent5ReportResponse {
  storyId: string
  summary: string
  recommendations: string[]
  verdict: 'APPROVED' | 'REQUIRES_REVIEW' | 'NEEDS_REWORK'
  details?: any
}

// ─────────────────────────────────────────────────────────────
// Error Handling Utilities
// ─────────────────────────────────────────────────────────────

function handleError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const message = error.response?.data?.detail || error.message || 'API request failed'
    return {
      message: typeof message === 'string' ? message : JSON.stringify(message),
      status,
      details: error.response?.data,
    }
  }
  return {
    message: error instanceof Error ? error.message : 'Unknown error occurred',
  }
}

// ─────────────────────────────────────────────────────────────
// API Client Methods
// ─────────────────────────────────────────────────────────────

export const apiClient = {
  // ─── Auth Endpoints ───
  auth: {
    async loginAdmin(email: string, password: string) {
      try {
        const response = await axiosInstance.post('/auth/login/admin', { email, password })
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async loginTester(username: string, password: string) {
      try {
        const response = await axiosInstance.post('/auth/login/tester', { username, password })
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async me() {
      try {
        const response = await axiosInstance.get('/auth/me')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async projects() {
      try {
        const response = await axiosInstance.get('/auth/projects')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async logout() {
      try {
        const response = await axiosInstance.post('/auth/logout')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Orchestrator Endpoints ───
  orchestrator: {
    /**
     * Run full pipeline for a story
     */
    async run(storyId: string, options: OrchestratorRequest): Promise<OrchestratorResponse> {
      try {
        const response = await axiosInstance.post<OrchestratorResponse>(
          `/orchestrator/run/${encodeURIComponent(storyId)}`,
          options
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Get status of running orchestrator job
     */
    async getStatus(jobId: string): Promise<OrchestratorResponse> {
      try {
        const response = await axiosInstance.get<OrchestratorResponse>(`/orchestrator/status/${jobId}`)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Cancel running orchestrator job
     */
    async cancel(jobId: string): Promise<{ status: string }> {
      try {
        const response = await axiosInstance.post(`/orchestrator/cancel/${jobId}`)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Analysis Endpoints ───
  analysis: {
    /**
     * Run analysis for a story
     */
    async run(storyId: string, options: AnalysisRequest): Promise<AnalysisResponse> {
      try {
        const params = new URLSearchParams()
        if (options.model_alias) params.append('model_alias', options.model_alias)
        if (options.use_rag !== undefined) params.append('use_rag', String(options.use_rag))
        if (options.force_refresh !== undefined)
          params.append('force_refresh', String(options.force_refresh))

        const response = await axiosInstance.get<AnalysisResponse>(
          `/analysis/${encodeURIComponent(storyId)}?${params.toString()}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Stories Endpoints ───
  stories: {
    /**
     * Fetch story from Jira by ID
     */
    async fetch(storyId: string): Promise<Story> {
      try {
        const response = await axiosInstance.get<Story>(
          `/stories/${encodeURIComponent(storyId)}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * List all stories
     */
    async list(): Promise<Story[]> {
      try {
        const response = await axiosInstance.get<Story[]>('/stories')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Database/Stored Stories ───
  db: {
    /**
     * List stored stories
     */
    async listStories(): Promise<Story[]> {
      try {
        const response = await axiosInstance.get<Story[]>('/db/stories')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Get stored story details
     */
    async getStory(storyId: string): Promise<Story> {
      try {
        const response = await axiosInstance.get<Story>(
          `/db/stories/${encodeURIComponent(storyId)}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * List analyses for a story
     */
    async listAnalyses(storyId: string): Promise<AnalysisResponse[]> {
      try {
        const response = await axiosInstance.get<AnalysisResponse[]>(
          `/db/analyses/${encodeURIComponent(storyId)}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Get latest analysis for a story
     */
    async getLatestAnalysis(
      storyId: string,
      model?: string
    ): Promise<AnalysisResponse> {
      try {
        const url = `/db/analyses/${encodeURIComponent(storyId)}/latest${
          model ? `?model=${encodeURIComponent(model)}` : ''
        }`
        const response = await axiosInstance.get<AnalysisResponse>(url)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * List scenarios for a story
     */
    async listScenarios(storyId: string): Promise<Scenario[]> {
      try {
        const response = await axiosInstance.get<Scenario[]>(
          `/db/scenarios/${encodeURIComponent(storyId)}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * List all scenarios
     */
    async getAllScenarios(): Promise<Scenario[]> {
      try {
        const response = await axiosInstance.get<Scenario[]>('/db/scenarios')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Agent5 Report Endpoints ───
  agent5: {
    /**
     * Generate report for a story
     */
    async generateReport(
      storyId: string,
      options: Agent5ReportRequest
    ): Promise<Agent5ReportResponse> {
      try {
        const response = await axiosInstance.post<Agent5ReportResponse>(
          `/agent5/story/${encodeURIComponent(storyId)}/report`,
          options
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Get report as Markdown
     */
    async getReportMarkdown(storyId: string): Promise<string> {
      try {
        const response = await axiosInstance.get(
          `/agent5/story/${encodeURIComponent(storyId)}/report/markdown`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Get report summary
     */
    async getReportSummary(storyId: string): Promise<Agent5ReportResponse> {
      try {
        const response = await axiosInstance.get<Agent5ReportResponse>(
          `/agent5/story/${encodeURIComponent(storyId)}/report/summary`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Generate reports for multiple stories (batch)
     */
    async generateBatchReports(storyIds: string[]): Promise<Agent5ReportResponse[]> {
      try {
        const response = await axiosInstance.post<Agent5ReportResponse[]>(
          '/agent5/batch-reports',
          { story_ids: storyIds }
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    /**
     * Health check
     */
    async health(): Promise<{ status: string }> {
      try {
        const response = await axiosInstance.get('/agent5/health')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Test Editing Endpoints ───
  testEditing: {
    async refineChat(body: {
      test: any
      message: string
      chat_history?: { role: string; content: string }[]
      story_id?: string
      story_summary?: string
      model_alias?: string
    }) {
      try {
        const response = await axiosInstance.post('/manual-tests/refine-chat', body)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async saveEdited(storyId: string, tests: any[]) {
      try {
        const response = await axiosInstance.post(`/manual-tests/save-edited/${encodeURIComponent(storyId)}`, {
          tests,
          generation_model: 'manual-edit',
        })
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async validateAndImprove(storyId: string, options: any): Promise<any> {
      try {
        const response = await axiosInstance.post(
          `/test-editing/validate/${encodeURIComponent(storyId)}`,
          options
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async updateTest(storyId: string, testId: string, data: any): Promise<any> {
      try {
        const response = await axiosInstance.put(
          `/test-editing/tests/${encodeURIComponent(storyId)}/${encodeURIComponent(testId)}`,
          data
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Integration Endpoints ───
  integration: {
    async integrateTest(test: { project_key?: string; test: any }): Promise<any> {
      try {
        const response = await axiosInstance.post('/integrate-test', test)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async addStepToTest(testKey: string, step: { action: string; expected_result: string }): Promise<any> {
      try {
        const response = await axiosInstance.post(`/tests/${encodeURIComponent(testKey)}/add-step`, step)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Health Check ───
  health: {
    async check(): Promise<{ status: string }> {
      try {
        const response = await axiosInstance.get('/')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ─── Admin ───
  admin: {
    async getStats(): Promise<any> {
      try { return (await axiosInstance.get('/admin/stats')).data } catch (e) { throw handleError(e) }
    },
    async listUsers(): Promise<any[]> {
      try { return (await axiosInstance.get('/admin/users')).data } catch (e) { throw handleError(e) }
    },
    async createUser(data: {
      email: string; password: string; role: string;
      display_name?: string; jira_username?: string;
    }): Promise<any> {
      try { return (await axiosInstance.post('/admin/users', data)).data } catch (e) { throw handleError(e) }
    },
    async updateUser(id: number, data: {
      display_name?: string; jira_username?: string;
      password?: string; role?: string;
    }): Promise<any> {
      try { return (await axiosInstance.patch(`/admin/users/${id}`, data)).data } catch (e) { throw handleError(e) }
    },
    async deleteUser(id: number): Promise<void> {
      try { await axiosInstance.delete(`/admin/users/${id}`) } catch (e) { throw handleError(e) }
    },
    async activateUser(id: number): Promise<any> {
      try { return (await axiosInstance.post(`/admin/users/${id}/activate`)).data } catch (e) { throw handleError(e) }
    },
    async deactivateUser(id: number): Promise<any> {
      try { return (await axiosInstance.post(`/admin/users/${id}/deactivate`)).data } catch (e) { throw handleError(e) }
    },
    async getPipelineHistory(params?: { limit?: number; offset?: number; launched_by?: string }): Promise<any> {
      try { return (await axiosInstance.get('/admin/pipelines', { params })).data } catch (e) { throw handleError(e) }
    },
    async getAuditLog(params?: { limit?: number; offset?: number }): Promise<any> {
      try { return (await axiosInstance.get('/admin/audit', { params })).data } catch (e) { throw handleError(e) }
    },
  },
}


// Interceptors for adding authentication or logging
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default axiosInstance
