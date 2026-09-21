import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from './client'

describe('API errors', () => {
  beforeEach(() => vi.unstubAllGlobals())
  it('formats FastAPI validation details instead of rendering an object', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [{ loc: ['body', 'base_plan_id'], msg: 'Field required' }] }), { status: 422 })))
    await expect(api.replan(1, ['VAN-01'])).rejects.toMatchObject({ status: 422, message: 'body.base_plan_id: Field required' })
  })
  it('handles non-JSON proxy errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Bad gateway</html>', { status: 502 })))
    await expect(api.getDashboard()).rejects.toMatchObject({ status: 502, message: 'Не удалось выполнить запрос.' })
  })
  it('handles network failures and timeouts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api.getDashboard()).rejects.toThrow('Сервер не ответил')
  })
  it('rejects non-JSON success responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('invalid')))
    await expect(api.getDashboard()).rejects.toThrow('Сервер вернул некорректный ответ')
  })
})
