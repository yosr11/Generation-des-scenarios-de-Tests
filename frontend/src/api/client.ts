/**
 * Centralized API client with Axios
 * Handles all communication with FastAPI backend
 * Provides proper error handling, loading states, and request/response types
 */

/// <reference types="vite/client" />

import axios, { AxiosInstance } from 'axios'

// ─────────────────────────────────────────────────────────────
// API Configuration
// ─────────────────────────────────────────────────────────────

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
// Request/Response Types
// ─────────────────────────────────────────────────────────────

// ── Auth ──────────────────────────────────────────────────────

export interface ProjectInfo {
  key:           string
  name:          string
  id?:           string
  project_type?: string
}

export interface UserInfo {
  id?:            number
  email:          string
  role:           'admin' | 'tester'
  display_name?:  string
  jira_username?: string
}

/** Réponse du POST /auth/login unifié */
export interface LoginResponse {
  user:      UserInfo
  role:      'admin' | 'tester'
  projects?: ProjectInfo[]
}

// ── Orchestrator ──────────────────────────────────────────────

export interface OrchestratorRequest {
  use_rag?: boolean
  use_legacy_rag?: boolean
  model_agent1?: string
  model_agent15?: string
  model_agent2?: string
  model_agent3_quality?: string
  model_agent5?: string
  coverage_threshold?: number
  max_correction_iterations?: number
  force_refresh?: boolean
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

// ── Analysis ──────────────────────────────────────────────────

export interface AnalysisRequest {
  model_alias?: string
  use_rag?: boolean
  force_refresh?: boolean
}

export interface AnalysisResponse {
  storyId: string
  model?: string
  story_title?: string
  story_type?: string
  actors?: string[]
  actions?: string[]
  business_rules?: string[]
  technical_scope?: string[]
  testable_points?: string[]
  acceptance_criteria_explicit?: string | string[]
  acceptance_criteria_inferred?: string | string[]
  clarification_questions?: string[]
  analysis_reason?: string[]
  user_flows?: string[]
  resolved_from_references?: string[]
  created_at?: string
  enriched_story?: any
  analysis?: any
  scenarios?: any[]
  tests?: any[]
  recommendations?: string[]
}

// ── Story ─────────────────────────────────────────────────────

export interface Story {
  id: string
  title: string
  description?: string
  epic?: string
  priority?: string
  created_at?: string
  updated_at?: string
}

export interface StoredStory extends Story {
  summary?: string
  status?: string
  description_clean?: string
  description_raw?: string
  acceptance_criteria_clean?: string
  labels?: string[]
  images?: any[]
  rag_context?: any[]
}

// ── Scenario ──────────────────────────────────────────────────

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

// ── Manual Test ───────────────────────────────────────────────

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

// ── Agent5 Report ─────────────────────────────────────────────

export interface Agent5ReportRequest {
  include_recommendations?: boolean
  output_format?: 'json' | 'markdown'
}

export interface Agent5ReportResponse {
  status: string
  report?: any
  report_markdown?: string
  error_message?: string
  generation_duration_ms: number
}

export interface Agent5ReportSummaryResponse {
  status: string
  story_id: string
  overall_status: string
  key_findings: string[]
  next_steps: string[]
  coverage_rate: string
  validation_status: string
  duplicate_count: number
  ambiguity_count: number
}

// ─────────────────────────────────────────────────────────────
// Error Handling
// ─────────────────────────────────────────────────────────────

function handleError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const responseData = error.response?.data
    const message =
      typeof responseData === 'string'
        ? responseData
        : responseData?.detail || responseData?.message || error.message || 'API request failed'
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
// API Client
// ─────────────────────────────────────────────────────────────

export const apiClient = {

  // ── Auth ────────────────────────────────────────────────────
  //
  // Un seul endpoint POST /auth/login.
  // Le backend détecte le rôle (admin | tester) depuis l'identifier.
  // loginAdmin() et loginTester() sont supprimés.
  //
  auth: {
    /**
     * Connexion unifiée admin + testeur.
     * @param identifier  Email admin  OU  username Jira du testeur
     * @param password    Mot de passe correspondant
     */
    async login(identifier: string, password: string): Promise<LoginResponse> {
      try {
        const response = await axiosInstance.post<LoginResponse>('/auth/login', {
          identifier,
          password,
        })
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async me(): Promise<UserInfo> {
      try {
        const response = await axiosInstance.get<UserInfo>('/auth/me')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async projects(): Promise<{ projects: ProjectInfo[] }> {
      try {
        const response = await axiosInstance.get<{ projects: ProjectInfo[] }>('/auth/projects')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async logout(): Promise<{ status: string }> {
      try {
        const response = await axiosInstance.post<{ status: string }>('/auth/logout')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async getProfile(): Promise<any> {
      try {
        const response = await axiosInstance.get('/auth/profile')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async updateProfile(data: {
      display_name?: string
      jira_username?: string
      current_password?: string
      new_password?: string
    }): Promise<any> {
      try {
        const response = await axiosInstance.patch('/auth/profile', data)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async requestPasswordReset(email: string): Promise<any> {
      try {
        const response = await axiosInstance.post('/auth/password-reset/request', { email })
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async confirmPasswordReset(data: { token: string; new_password: string }): Promise<any> {
      try {
        const response = await axiosInstance.post('/auth/password-reset/confirm', data)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Orchestrator ─────────────────────────────────────────────
  orchestrator: {
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

    async getStatus(jobId: string): Promise<OrchestratorResponse> {
      try {
        const response = await axiosInstance.get<OrchestratorResponse>(
          `/orchestrator/status/${jobId}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async cancel(jobId: string): Promise<{ status: string }> {
      try {
        const response = await axiosInstance.post(`/orchestrator/cancel/${jobId}`)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Analysis ─────────────────────────────────────────────────
  analysis: {
    async run(storyId: string, options: AnalysisRequest): Promise<AnalysisResponse> {
      try {
        const params = new URLSearchParams()
        if (options.model_alias)                params.append('model_alias', options.model_alias)
        if (options.use_rag !== undefined)       params.append('use_rag', String(options.use_rag))
        if (options.force_refresh !== undefined) params.append('force_refresh', String(options.force_refresh))

        const response = await axiosInstance.get<AnalysisResponse>(
          `/analysis/${encodeURIComponent(storyId)}?${params.toString()}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Stories ───────────────────────────────────────────────────
  stories: {
    async fetch(storyId: string): Promise<Story> {
      try {
        const response = await axiosInstance.get<Story>(`/stories/${encodeURIComponent(storyId)}`)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async list(): Promise<Story[]> {
      try {
        const response = await axiosInstance.get<Story[]>('/stories')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Database / Stored Stories ─────────────────────────────────
  db: {
    async listStories(): Promise<StoredStory[]> {
      try {
        const response = await axiosInstance.get<StoredStory[]>('/db/stories')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async getStory(storyId: string): Promise<StoredStory> {
      try {
        const response = await axiosInstance.get<StoredStory>(
          `/db/stories/${encodeURIComponent(storyId)}`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async deleteStory(storyId: string): Promise<void> {
      try {
        await axiosInstance.delete(`/db/stories/${encodeURIComponent(storyId)}`)
      } catch (error) {
        throw handleError(error)
      }
    },

    async listAnalyses(storyId: string): Promise<AnalysisResponse[]> {
      try {
        const response = await axiosInstance.get<AnalysisResponse[]>(
          `/db/stories/${encodeURIComponent(storyId)}/analyses`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async getLatestAnalysis(storyId: string, model?: string): Promise<AnalysisResponse> {
      try {
        const url = `/db/stories/${encodeURIComponent(storyId)}/analysis/latest${
          model ? `?model=${encodeURIComponent(model)}` : ''
        }`
        const response = await axiosInstance.get<AnalysisResponse>(url)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async listScenarios(storyId: string): Promise<Scenario[]> {
      try {
        const response = await axiosInstance.get<any>(
          `/db/stories/${encodeURIComponent(storyId)}/scenarios`
        )
        return response.data.scenarios || response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async getAllScenarios(): Promise<Scenario[]> {
      try {
        const response = await axiosInstance.get<any>('/db/scenarios')
        return response.data.scenarios || response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async getManualTests(storyId: string): Promise<any> {
      try {
        const response = await axiosInstance.get<any>(
          `/db/stories/${encodeURIComponent(storyId)}/manual-tests`
        )
        return response.data.tests || response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async getValidations(storyId: string): Promise<any> {
      try {
        const response = await axiosInstance.get<any>(
          `/db/stories/${encodeURIComponent(storyId)}/validations`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Agent 1.5 — Business Modeling ───────────────────────────
  agent15: {
    async getLatest(storyId: string): Promise<any> {
      const response = await axiosInstance.get<any>(
        `/agent15/${encodeURIComponent(storyId)}/latest`
      )
      return response.data
    },

    async run(storyId: string, options?: { model_alias?: string; force?: boolean }): Promise<any> {
      const params = new URLSearchParams()
      if (options?.model_alias) params.append('model_alias', options.model_alias)
      if (options?.force !== undefined) params.append('force', String(options.force))
      const response = await axiosInstance.get<any>(
        `/agent15/${encodeURIComponent(storyId)}?${params.toString()}`
      )
      return response.data
    },
  },

  // ── Agent5 Report ─────────────────────────────────────────────
  agent5: {
    async generateReport(storyId: string, options: Agent5ReportRequest): Promise<Agent5ReportResponse> {
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

    async getReportMarkdown(storyId: string): Promise<string> {
      try {
        const response = await axiosInstance.get<{ report_markdown: string }>(
          `/agent5/story/${encodeURIComponent(storyId)}/report/markdown`
        )
        return response.data.report_markdown
      } catch (error) {
        throw handleError(error)
      }
    },

    async getReportSummary(storyId: string): Promise<Agent5ReportSummaryResponse> {
      try {
        const response = await axiosInstance.get<Agent5ReportSummaryResponse>(
          `/agent5/story/${encodeURIComponent(storyId)}/report/summary`
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

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

    async health(): Promise<{ status: string }> {
      try {
        const response = await axiosInstance.get('/agent5/health')
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Test Editing ──────────────────────────────────────────────
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
        const response = await axiosInstance.post(
          `/manual-tests/save-edited/${encodeURIComponent(storyId)}`,
          { tests, generation_model: 'manual-edit' }
        )
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

  // ── Integration ───────────────────────────────────────────────
  integration: {
    async integrateTest(test: { project_key?: string; test: any }): Promise<any> {
      try {
        const response = await axiosInstance.post('/integrate-test', test)
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },

    async addStepToTest(
      testKey: string,
      step: { action: string; expected_result: string }
    ): Promise<any> {
      try {
        const response = await axiosInstance.post(
          `/tests/${encodeURIComponent(testKey)}/add-step`,
          step
        )
        return response.data
      } catch (error) {
        throw handleError(error)
      }
    },
  },

  // ── Health ────────────────────────────────────────────────────
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

  // ── Admin ─────────────────────────────────────────────────────
  admin: {
    async getStats(): Promise<any> {
      try { return (await axiosInstance.get('/admin/stats')).data } catch (e) { throw handleError(e) }
    },
    async listUsers(): Promise<any[]> {
      try { return (await axiosInstance.get('/admin/users')).data } catch (e) { throw handleError(e) }
    },
    async createUser(data: {
      email: string
      role: string
      display_name?: string
      jira_username?: string
    }): Promise<any> {
      try { return (await axiosInstance.post('/admin/users', data)).data } catch (e) { throw handleError(e) }
    },
    async updateUser(id: number, data: {
      display_name?: string
       email?: string 
      jira_username?: string
      password?: string
      role?: string
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
    async getPipelineHistory(params?: {
      limit?: number
      offset?: number
      launched_by?: string
    }): Promise<any> {
      try { return (await axiosInstance.get('/admin/pipelines', { params })).data } catch (e) { throw handleError(e) }
    },
    async getAuditLog(params?: { limit?: number; offset?: number }): Promise<any> {
      try { return (await axiosInstance.get('/admin/audit', { params })).data } catch (e) { throw handleError(e) }
    },
  },
}

// ─────────────────────────────────────────────────────────────
// Interceptors
// ─────────────────────────────────────────────────────────────

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default axiosInstance