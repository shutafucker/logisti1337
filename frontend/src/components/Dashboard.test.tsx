import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Dashboard } from './Dashboard'

vi.mock('./MapPanel', () => ({
  MapPanel: () => <div data-testid="map-panel">Map</div>,
}))

const routePlanPayload = {
  id: 42,
  routes: [{ vehicle_external_id: 'VAN-01', distance_km: 7.2, duration_minutes: 24, stops: [{ order_external_id: 'ORD-100', latitude: 43.238, longitude: 76.945, eta_minutes: 12 }] }],
  metrics: { total_distance_km: 7.2, total_duration_minutes: 24 },
  unassigned: [{ order_external_id: 'ORD-200', reason: 'capacity_exceeded' }],
}

const dashboardPayload = {
  summary: { total_orders: 3, assigned_orders: 2, unassigned_orders: 1, active_vehicles: 2 },
  orders: [
    { external_id: 'ORD-100', latitude: 43.238, longitude: 76.945, demand: 2, priority: 5, status: 'assigned' },
  ],
  vehicles: [
    { external_id: 'VAN-01', latitude: 43.24, longitude: 76.94, capacity: 10, status: 'available' },
  ],
  metrics: { total_distance_km: 12.4, total_duration_minutes: 48 },
  unassigned: [{ order_external_id: 'ORD-200', reason: 'capacity_exceeded' }],
  route_plan: routePlanPayload,
}

function jsonResponse(body: unknown, ok = true) {
  return Promise.resolve(new Response(JSON.stringify(body), { status: ok ? 200 : 500, headers: { 'Content-Type': 'application/json' } }))
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading state before the dashboard request resolves', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<Dashboard />)
    expect(screen.getByText(/loading dispatcher data/i)).toBeInTheDocument()
  })

  it('renders dashboard status, metrics, and unassigned reason from the API', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse(dashboardPayload)))
    render(<Dashboard />)
    expect((await screen.findAllByText('ORD-100')).length).toBeGreaterThan(0)
    expect(screen.getByText('capacity exceeded')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('7.2 km')).toBeInTheDocument()
    expect(screen.getByText('Route · VAN-01')).toBeInTheDocument()
  })

  it('calculates and presents detailed routes after creating a plan', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(dashboardPayload)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 42 })))
      .mockResolvedValueOnce(new Response(JSON.stringify(routePlanPayload)))
    vi.stubGlobal('fetch', fetchMock)
    render(<Dashboard />)
    await screen.findAllByText('ORD-100')
    fireEvent.click(screen.getByRole('button', { name: /calculate routes/i }))
    expect(await screen.findByText('Route · VAN-01')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenLastCalledWith('/api/route-plans/42', expect.anything())
  })

  it('shows an actionable request error when the dashboard cannot load', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({ detail: 'Service unavailable' }, false)))
    render(<Dashboard />)
    expect(await screen.findByText(/couldn't load the dispatcher dashboard/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('shows an import validation error returned by the API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(dashboardPayload)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ accepted: [], errors: [{ row: 2, field: 'latitude', reason: 'must be valid' }] }), { status: 422 }))
    vi.stubGlobal('fetch', fetchMock)
    render(<Dashboard />)
    await screen.findAllByText('ORD-100')
    const input = screen.getByLabelText(/orders file/i)
    const file = new File(['external_id,latitude\nORD-9,nope'], 'orders.csv', { type: 'text/csv' })
    fireEvent.change(input, { target: { files: [file] } })
    expect(await screen.findByText(/row 2.*latitude.*must be valid/i)).toBeInTheDocument()
  })

  it('refreshes a new plan after a partially accepted import while showing its validation errors', async () => {
    const refreshedDashboard = {
      ...dashboardPayload,
      summary: { ...dashboardPayload.summary, total_orders: 4, assigned_orders: 3 },
      route_plan: { ...routePlanPayload, id: 43 },
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(dashboardPayload)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ accepted_count: 1, errors: [{ row: 3, field: 'latitude', reason: 'out_of_range' }] })))
      .mockResolvedValueOnce(new Response(JSON.stringify(refreshedDashboard)))
    vi.stubGlobal('fetch', fetchMock)
    render(<Dashboard />)
    await screen.findAllByText('ORD-100')
    const input = screen.getByLabelText(/orders file/i)
    fireEvent.change(input, { target: { files: [new File(['x'], 'orders.csv', { type: 'text/csv' })] } })

    expect(await screen.findByText(/row 3.*out_of_range/i)).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(screen.getByText('4')).toBeInTheDocument()
  })
})
