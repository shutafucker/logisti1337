import type { DashboardData, ImportError, ImportResult, RoutePlan } from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, readonly details: ImportError[] = []) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new ApiError('Network request failed. Check that the API is running and try again.')
  }

  const body = await response.json().catch(() => ({})) as { detail?: string; errors?: ImportError[] }
  if (!response.ok) {
    throw new ApiError(body.detail ?? 'The request could not be completed.', body.errors ?? [])
  }
  return body as T
}

export const api = {
  getDashboard: () => request<DashboardData>('/dashboard'),
  createRoutePlan: () => request<{ id: number }>('/route-plans', { method: 'POST' }),
  getRoutePlan: (id: number) => request<RoutePlan>(`/route-plans/${id}`),
  importFile: async (resource: 'orders' | 'vehicles', file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ImportResult>(`/imports/${resource}`, { method: 'POST', body: form })
  },
}
