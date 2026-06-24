/**
 * Custom React hooks for API interactions
 * Provides data fetching, loading, and error states
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { apiClient, OrchestratorRequest, OrchestratorResponse, ApiError } from '../api/client'

// ─────────────────────────────────────────────────────────────
// Generic Hook for API Requests
// ─────────────────────────────────────────────────────────────

export interface UseAsyncState<T> {
  data: T | null
  loading: boolean
  error: ApiError | null
}

export function useAsync<T>(
  asyncFunction: () => Promise<T>,
  immediate = true
): UseAsyncState<T> & { execute: () => Promise<T> } {
  const [state, setState] = useState<UseAsyncState<T>>({
    data: null,
    loading: immediate,
    error: null,
  })

  const execute = useCallback(async () => {
    setState({ data: null, loading: true, error: null })
    try {
      const response = await asyncFunction()
      setState({ data: response, loading: false, error: null })
      return response
    } catch (error) {
      const apiError = error as ApiError
      setState({ data: null, loading: false, error: apiError })
      throw error
    }
  }, [asyncFunction])

  useEffect(() => {
    if (immediate) {
      execute()
    }
  }, [execute, immediate])

  return { ...state, execute }
}

// ─────────────────────────────────────────────────────────────
// Orchestrator Hook
// ─────────────────────────────────────────────────────────────

export interface UseOrchestratorState {
  data: OrchestratorResponse | null
  loading: boolean
  error: ApiError | null
  progress: number
  isCompleted: boolean
  isFailed: boolean
}

export function useOrchestrator(storyId?: string): UseOrchestratorState & {
  run: (options: OrchestratorRequest) => Promise<OrchestratorResponse>
  cancel: () => Promise<void>
} {
  const [state, setState] = useState<UseOrchestratorState>({
    data: null,
    loading: false,
    error: null,
    progress: 0,
    isCompleted: false,
    isFailed: false,
  })

  const pollingIntervalRef = useRef<number | null>(null)
  const jobIdRef = useRef<string | null>(null)

  const run = useCallback(
    async (options: OrchestratorRequest) => {
      if (!storyId) {
        throw new Error('Story ID is required')
      }

      setState({
        data: null,
        loading: true,
        error: null,
        progress: 0,
        isCompleted: false,
        isFailed: false,
      })

      try {
        const response = await apiClient.orchestrator.run(storyId, options)
        jobIdRef.current = response.storyId

        setState((prev) => ({
          ...prev,
          data: response,
          progress: response.progress || 0,
          isCompleted: response.status === 'completed',
          isFailed: response.status === 'failed',
        }))

        // Start polling if running
        if (response.status === 'running') {
          startPolling()
        }

        return response
      } catch (error) {
        const apiError = error as ApiError
        setState((prev) => ({
          ...prev,
          loading: false,
          error: apiError,
          isFailed: true,
        }))
        throw error
      }
    },
    [storyId]
  )

  const startPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    pollingIntervalRef.current = window.setInterval(async () => {
      if (!jobIdRef.current) return

      try {
        const response = await apiClient.orchestrator.getStatus(jobIdRef.current)
        setState((prev) => ({
          ...prev,
          data: response,
          progress: response.progress || 0,
          isCompleted: response.status === 'completed',
          isFailed: response.status === 'failed',
        }))

        if (response.status !== 'running') {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
          setState((prev) => ({ ...prev, loading: false }))
        }
      } catch (error) {
        const apiError = error as ApiError
        setState((prev) => ({
          ...prev,
          error: apiError,
          isFailed: true,
          loading: false,
        }))

        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
      }
    }, 2000)
  }

  const cancel = useCallback(async () => {
    if (!jobIdRef.current) return

    try {
      await apiClient.orchestrator.cancel(jobIdRef.current)
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      setState((prev) => ({
        ...prev,
        loading: false,
        isFailed: true,
      }))
    } catch (error) {
      console.error('Failed to cancel orchestrator:', error)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  return { ...state, run, cancel }
}

// ─────────────────────────────────────────────────────────────
// Analysis Hook
// ─────────────────────────────────────────────────────────────

export function useAnalysis(storyId?: string) {
  const [state, setState] = useState<UseAsyncState<any>>({
    data: null,
    loading: false,
    error: null,
  })

  const run = useCallback(
    async (options: any = {}) => {
      if (!storyId) {
        throw new Error('Story ID is required')
      }

      setState({ data: null, loading: true, error: null })
      try {
        const response = await apiClient.analysis.run(storyId, options)
        setState({ data: response, loading: false, error: null })
        return response
      } catch (error) {
        const apiError = error as ApiError
        setState({ data: null, loading: false, error: apiError })
        throw error
      }
    },
    [storyId]
  )

  return { ...state, run }
}

// ─────────────────────────────────────────────────────────────
// Story/Database Hooks
// ─────────────────────────────────────────────────────────────

export function useStories(storedOnly = false) {
  const asyncFn = useCallback(
    () =>
      storedOnly
        ? apiClient.db.listStories()
        : apiClient.stories.list(),
    [storedOnly]
  )

  return useAsync(asyncFn, true)
}

export function useStory(storyId: string, stored = false) {
  const asyncFn = useCallback(
    () =>
      stored
        ? apiClient.db.getStory(storyId)
        : apiClient.stories.fetch(storyId),
    [storyId, stored]
  )

  return useAsync(asyncFn, !!storyId)
}

export function useScenarios(storyId?: string) {
  const asyncFn = useCallback(
    () =>
      storyId
        ? apiClient.db.listScenarios(storyId)
        : apiClient.db.getAllScenarios(),
    [storyId]
  )

  return useAsync(asyncFn, true)
}

export function useAnalysisHistory(storyId: string) {
  const asyncFn = useCallback(
    () => apiClient.db.listAnalyses(storyId),
    [storyId]
  )

  return useAsync(asyncFn, !!storyId)
}

// ─────────────────────────────────────────────────────────────
// Agent5 Report Hook
// ─────────────────────────────────────────────────────────────

export function useAgent5Report(storyId?: string) {
  const [state, setState] = useState<UseAsyncState<any>>({
    data: null,
    loading: false,
    error: null,
  })

  const generate = useCallback(
    async (options: any = {}) => {
      if (!storyId) {
        throw new Error('Story ID is required')
      }

      setState({ data: null, loading: true, error: null })
      try {
        const response = await apiClient.agent5.generateReport(storyId, options)
        setState({ data: response, loading: false, error: null })
        return response
      } catch (error) {
        const apiError = error as ApiError
        setState({ data: null, loading: false, error: apiError })
        throw error
      }
    },
    [storyId]
  )

  const getMarkdown = useCallback(async () => {
    if (!storyId) throw new Error('Story ID is required')
    return apiClient.agent5.getReportMarkdown(storyId)
  }, [storyId])

  const getSummary = useCallback(async () => {
    if (!storyId) throw new Error('Story ID is required')
    return apiClient.agent5.getReportSummary(storyId)
  }, [storyId])

  return { ...state, generate, getMarkdown, getSummary }
}
