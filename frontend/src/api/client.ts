import type { AgentResult, DashboardData, ImportError, ImportResult, ReplanResult, RoutePlan } from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, readonly details: ImportError[] = [], readonly status = 0) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: init.signal ?? AbortSignal.timeout(60000) })
  } catch {
    throw new ApiError('Сервер не ответил. Проверьте соединение и повторите запрос.')
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { loc?: unknown[]; msg?: string }) => `${item.loc?.join('.') ?? 'Данные'}: ${item.msg ?? 'Ошибка проверки'}`).join('; ')
      : 'Не удалось выполнить запрос.'
    throw new ApiError(message, body?.errors ?? [], response.status)
  }
  if (body === null) throw new ApiError('Сервер вернул некорректный ответ.')
  return body as T
}

export const api = {
  getDashboard: () => request<DashboardData>('/dashboard'),
  createRoutePlan: () => request<{ id: number }>('/route-plans', { method: 'POST' }),
  getRoutePlan: (id: number) => request<RoutePlan>(`/route-plans/${id}`),
  replan: (basePlanId: number, vehicleIds: string[]) => request<ReplanResult>('/replans', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_plan_id: basePlanId, unavailable_vehicle_ids: vehicleIds }),
  }),
  interpret: (message: string, basePlanId: number) => request<AgentResult>('/agent/interpret', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, base_plan_id: basePlanId }),
  }),
  importFile: async (resource: 'orders' | 'vehicles', file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ImportResult>(`/imports/${resource}`, { method: 'POST', body: form })
  },
}
