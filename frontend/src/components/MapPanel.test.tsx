import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MapPanel } from './MapPanel'
const map = vi.hoisted(() => ({ fitBounds: vi.fn(), setView: vi.fn() }))
vi.mock('react-leaflet', () => ({
  useMap: () => map,
  MapContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Marker: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Polyline: ({ pathOptions }: { pathOptions: { color: string } }) => <div data-testid="route-line" data-color={pathOptions.color} />,
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TileLayer: ({ eventHandlers }: { eventHandlers: { tileerror: () => void } }) => <button onClick={eventHandlers.tileerror}>Сбой тайлов</button>,
}))
const vehicles = [{ external_id: 'VAN-01', latitude: 51.1, longitude: 71.4, capacity: 10, status: 'available' }]
const routes = [{ vehicle_external_id: 'VAN-01', distance_km: 2, duration_minutes: 9, stops: [{ order_external_id: 'ORD-1', latitude: 51.2, longitude: 71.5, eta_minutes: 5 }] }]
describe('MapPanel', () => {
  it('shows stop sequence, vehicle, unassigned orders and fits changed bounds', () => {
    const props = { vehicles, routes, orders: [{ external_id: 'ORD-2', latitude: 51.3, longitude: 71.6, demand: 20, priority: 1, status: 'pending' }], unassigned: [{ order_external_id: 'ORD-2', reason: 'capacity_exceeded' }] }
    const { rerender } = render(<MapPanel {...props} />)
    expect(screen.getByText('ORD-1')).toBeInTheDocument()
    expect(screen.getByText(/Машина VAN-01 · Остановка 1/)).toBeInTheDocument()
    expect(screen.getByText(/Без машины: Недостаточно вместимости/)).toBeInTheDocument()
    expect(screen.getByTestId('route-line')).toHaveAttribute('data-color')
    const calls = map.fitBounds.mock.calls.length
    rerender(<MapPanel {...props} orders={[{ ...props.orders[0], latitude: 52 }]} />)
    expect(map.fitBounds.mock.calls.length).toBe(calls + 1)
  })
  it('keeps route details and shows a notice when tiles fail', () => {
    render(<MapPanel vehicles={vehicles} routes={routes} orders={[]} />)
    fireEvent.click(screen.getByText('Сбой тайлов'))
    expect(screen.getByRole('status')).toHaveTextContent('Подложка карты недоступна')
    expect(screen.getByText('ORD-1')).toBeInTheDocument()
  })
})
