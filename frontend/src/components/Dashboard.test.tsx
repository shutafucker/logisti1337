import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Dashboard } from './Dashboard'

vi.mock('./MapPanel', () => ({ MapPanel: () => <div>Карта</div> }))
const plan = { id: 42, routes: [{ vehicle_external_id: 'VAN-01', distance_km: 7.2, duration_minutes: 24, stops: [{ order_external_id: 'ORD-100', latitude: 51.1, longitude: 71.4, eta_minutes: 12 }] }], metrics: { total_distance_km: 7.2, total_duration_minutes: 24 }, unassigned: [{ order_external_id: 'ORD-200', reason: 'capacity_exceeded' }] }
const data = { summary: { total_orders: 2, assigned_orders: 99, unassigned_orders: 99, active_vehicles: 1 }, orders: [{ external_id: 'ORD-100', latitude: 51.1, longitude: 71.4, demand: 2, priority: 5, status: 'pending' }, { external_id: 'ORD-200', latitude: 51.2, longitude: 71.5, demand: 12, priority: 1, status: 'pending' }], vehicles: [{ external_id: 'VAN-01', latitude: 51.1, longitude: 71.4, capacity: 10, status: 'available' }], metrics: plan.metrics, unassigned: plan.unassigned, route_plan: plan }
const replanned = { base_plan_id: 42, plan: { id: 43, routes: [], metrics: { total_distance_km: 0, total_duration_minutes: 0 }, unassigned: data.orders.map(order => ({ order_external_id: order.external_id, reason: 'no_available_vehicle' })) }, comparison: { before: { assigned_orders: 1, unassigned_orders: 1, distance_km: 7.2, duration_minutes: 24 }, after: { assigned_orders: 0, unassigned_orders: 2, distance_km: 0, duration_minutes: 0 }, delta: { assigned_orders: -1, unassigned_orders: 1, distance_km: -7.2, duration_minutes: -24 } }, unavailable_vehicle_ids: ['VAN-01'] }
const ready = { status: 'ready', action: { type: 'exclude_vehicles', vehicle_ids: ['VAN-01'] }, explanation: 'Исключим VAN-01.', question: null }
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const deferred = () => { let resolve!: (value: Response) => void; const promise = new Promise<Response>(done => { resolve = done }); return { promise, resolve } }
async function start(...responses: (Response | Promise<Response>)[]) {
  const fetchMock = vi.fn().mockResolvedValueOnce(response(data))
  responses.forEach(item => fetchMock.mockReturnValueOnce(Promise.resolve(item)))
  vi.stubGlobal('fetch', fetchMock)
  render(<Dashboard />)
  await screen.findByText('Маршрут · VAN-01')
  return fetchMock
}
function exclude() {
  fireEvent.click(screen.getByRole('checkbox', { name: /VAN-01/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Исключить и пересчитать' }))
}
function command() {
  fireEvent.change(screen.getByLabelText('Что изменилось?'), { target: { value: 'VAN-01 сломалась' } })
  fireEvent.click(screen.getByRole('button', { name: 'Разобрать команду' }))
}
function upload() {
  fireEvent.change(screen.getByLabelText('Файл заказов'), { target: { files: [new File(['x'], 'orders.csv', { type: 'text/csv' })] } })
}

describe('Dashboard', () => {
  beforeEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
  it('shows loading and derives summary from the actual plan', async () => {
    const pending = deferred()
    vi.stubGlobal('fetch', vi.fn(() => pending.promise))
    render(<Dashboard />)
    expect(screen.getByText('Загрузка данных диспетчера…')).toBeInTheDocument()
    pending.resolve(response(data))
    await screen.findByText('Маршрут · VAN-01')
    expect(screen.getByLabelText('Назначено')).toHaveTextContent('1')
    expect(screen.queryByText('99')).not.toBeInTheDocument()
    expect(screen.getByText('Недостаточно вместимости')).toBeInTheDocument()
  })
  it('recalculates using create and detailed plan endpoints', async () => {
    const fetchMock = await start(response({ id: 44 }), response({ ...plan, id: 44, routes: [] }))
    fireEvent.click(screen.getByRole('button', { name: 'Рассчитать маршруты' }))
    await screen.findByText('План №44 рассчитан.')
    expect(fetchMock).toHaveBeenLastCalledWith('/api/route-plans/44', expect.anything())
    expect(screen.getByLabelText('Назначено')).toHaveTextContent('0')
  })
  it('excludes all vehicles, shows comparison and updates counts', async () => {
    const fetchMock = await start(response(replanned))
    exclude()
    const comparison = await screen.findByRole('region', { name: 'Сравнение планов' })
    expect(within(comparison).getByText(/Доставок стало меньше/)).toBeInTheDocument()
    expect(screen.getByLabelText('Назначено')).toHaveTextContent('0')
    expect(screen.getByLabelText('Без машины')).toHaveTextContent('2')
    expect(screen.getByLabelText('Доступно машин')).toHaveTextContent('0')
    expect(screen.getByText(/Маршрутов нет/)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenLastCalledWith('/api/replans', expect.objectContaining({ method: 'POST', body: JSON.stringify({ base_plan_id: 42, unavailable_vehicle_ids: ['VAN-01'] }) }))
  })
  it('blocks duplicate requests and preserves plan on failure, then retries', async () => {
    const pending = deferred()
    const fetchMock = await start(pending.promise, response(replanned))
    exclude()
    const button = screen.getByRole('button', { name: 'Исключить и пересчитать' })
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    pending.resolve(response({ detail: 'Service unavailable' }, 500))
    await screen.findByRole('alert')
    expect(screen.getByText('Маршрут · VAN-01')).toBeInTheDocument()
    expect(button).toBeEnabled()
    fireEvent.click(button)
    await screen.findByRole('region', { name: 'Сравнение планов' })
  })
  it('shows missing backend endpoint honestly', async () => {
    await start(response({ detail: 'Not Found' }, 404))
    exclude()
    expect(await screen.findByRole('alert')).toHaveTextContent('функция пока недоступна на сервере')
  })
  it('refreshes valid rows of partial import while retaining validation errors', async () => {
    await start(response({ accepted_count: 1, errors: [{ row: 3, field: 'latitude', reason: 'out_of_range' }] }), response({ ...data, route_plan: { ...plan, id: 50 } }))
    upload()
    expect(await screen.findByText(/Принято строк: 1/)).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Строка 3 · latitude: out_of_range')
    expect(screen.getByText(/План №50/)).toBeInTheDocument()
  })
  it('clears comparison after import', async () => {
    await start(response(replanned), response({ accepted_count: 1, errors: [] }), response(data))
    exclude()
    await screen.findByRole('region', { name: 'Сравнение планов' })
    upload()
    await screen.findByText(/Принято строк/)
    expect(screen.queryByRole('region', { name: 'Сравнение планов' })).not.toBeInTheDocument()
    expect(screen.getByText('Маршрут · VAN-01')).toBeInTheDocument()
  })
  it('does not show obsolete routes when import succeeded but reload failed', async () => {
    await start(response({ accepted_count: 1, errors: [] }), response({ detail: 'offline' }, 500))
    upload()
    await screen.findByRole('alert')
    expect(screen.queryByText('Маршрут · VAN-01')).not.toBeInTheDocument()
    expect(screen.getByText('Данные пока недоступны')).toBeInTheDocument()
  })
  it.each(['needs_clarification', 'unsupported'])('does not replan for AI status %s', async status => {
    const fetchMock = await start(response({ status, action: null, explanation: 'Уточните действие.', question: 'Какая машина?' }))
    command()
    await screen.findByText('Уточните действие.')
    expect(screen.queryByRole('button', { name: 'Применить и пересчитать' })).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(screen.getByLabelText('Что изменилось?')).toHaveValue('VAN-01 сломалась')
  })
  it('requires confirmation before applying a valid AI action', async () => {
    const fetchMock = await start(response(ready), response(replanned))
    command()
    const apply = await screen.findByRole('button', { name: 'Применить и пересчитать' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    fireEvent.click(apply)
    await screen.findByRole('region', { name: 'Сравнение планов' })
    expect(fetchMock).toHaveBeenLastCalledWith('/api/replans', expect.objectContaining({ body: JSON.stringify({ base_plan_id: 42, unavailable_vehicle_ids: ['VAN-01'] }) }))
  })
  it('keeps manual controls available if AI returns 503', async () => {
    await start(response({ detail: 'provider offline' }, 503))
    command()
    expect(await screen.findByRole('alert')).toHaveTextContent('AI временно недоступен')
    expect(screen.getByRole('checkbox')).toBeEnabled()
  })
  it('rejects an unknown vehicle returned by AI', async () => {
    await start(response({ ...ready, action: { type: 'exclude_vehicles', vehicle_ids: ['UNKNOWN'] } }))
    command()
    expect(await screen.findByRole('alert')).toHaveTextContent('неизвестную машину')
    expect(screen.queryByRole('button', { name: 'Применить и пересчитать' })).not.toBeInTheDocument()
  })
  it('discards a late AI response after a manual replan', async () => {
    const pending = deferred()
    await start(pending.promise, response(replanned))
    command()
    exclude()
    await screen.findByRole('region', { name: 'Сравнение планов' })
    pending.resolve(response(ready))
    await waitFor(() => expect(screen.queryByText('Разбираем команду…')).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Применить и пересчитать' })).not.toBeInTheDocument()
  })
  it('invalidates an accepted AI response after importing data', async () => {
    await start(response(ready), response({ accepted_count: 1, errors: [] }), response({ ...data, route_plan: { ...plan, id: 50 } }))
    command()
    await screen.findByRole('button', { name: 'Применить и пересчитать' })
    upload()
    await screen.findByText(/Принято строк/)
    expect(screen.queryByRole('button', { name: 'Применить и пересчитать' })).not.toBeInTheDocument()
  })
  it('invalidates AI action when the message is edited', async () => {
    await start(response(ready))
    command()
    await screen.findByRole('button', { name: 'Применить и пересчитать' })
    fireEvent.change(screen.getByLabelText('Что изменилось?'), { target: { value: 'Другая машина' } })
    expect(screen.queryByRole('button', { name: 'Применить и пересчитать' })).not.toBeInTheDocument()
  })
  it('shows a recoverable initial load error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'offline' }, 500)))
    render(<Dashboard />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Загрузка данных')
    expect(screen.getByRole('button', { name: 'Обновить и повторить' })).toBeEnabled()
  })
})
