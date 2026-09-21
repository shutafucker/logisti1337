import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MapPanel } from './MapPanel'

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Marker: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Polyline: () => <div data-testid="route-line" />,
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TileLayer: ({ url }: { url: string }) => <div data-testid="tiles">{url}</div>,
}))

describe('MapPanel', () => {
  it('uses OpenStreetMap tiles and exposes vehicle and stop markers', () => {
    render(
      <MapPanel
        vehicles={[{ external_id: 'VAN-01', latitude: 43.24, longitude: 76.94, capacity: 10, status: 'available' }]}
        routes={[{ vehicle_external_id: 'VAN-01', distance_km: 2, duration_minutes: 9, stops: [{ order_external_id: 'ORD-1', latitude: 43.238, longitude: 76.945, eta_minutes: 5 }] }]}
        orders={[]}
      />,
    )
    expect(screen.getByTestId('tiles')).toHaveTextContent('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
    expect(screen.getByText('VAN-01')).toBeInTheDocument()
    expect(screen.getByText('ORD-1')).toBeInTheDocument()
    expect(screen.getByTestId('route-line')).toBeInTheDocument()
  })
})
