import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet'
import type { Order, Route, Vehicle } from '../api/types'

import 'leaflet/dist/leaflet.css'

type Props = { vehicles: Vehicle[]; routes: Route[]; orders: Order[] }

const fallbackCenter: [number, number] = [43.238, 76.945]
const vehicleIcon = L.divIcon({ className: 'map-pin map-pin--vehicle', html: 'V', iconSize: [26, 26], iconAnchor: [13, 13] })
const stopIcon = L.divIcon({ className: 'map-pin map-pin--stop', html: '•', iconSize: [22, 22], iconAnchor: [11, 11] })

export function MapPanel({ vehicles, routes, orders }: Props) {
  const center = vehicles[0] ? [vehicles[0].latitude, vehicles[0].longitude] as [number, number]
    : orders[0] ? [orders[0].latitude, orders[0].longitude] as [number, number] : fallbackCenter
  const vehicleById = new Map(vehicles.map((vehicle) => [vehicle.external_id, vehicle]))

  return (
    <section className="map-card" aria-label="Routes map">
      <div className="map-card__header"><h2>Live route map</h2><span>OpenStreetMap</span></div>
      <MapContainer center={center} zoom={12} scrollWheelZoom className="map">
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {vehicles.map((vehicle) => (
          <Marker key={vehicle.external_id} position={[vehicle.latitude, vehicle.longitude]} icon={vehicleIcon}>
            <Popup><strong>{vehicle.external_id}</strong><br />{vehicle.status} · Capacity {vehicle.capacity}</Popup>
          </Marker>
        ))}
        {routes.flatMap((route) => route.stops.map((stop) => (
          <Marker key={`${route.vehicle_external_id}-${stop.order_external_id}`} position={[stop.latitude, stop.longitude]} icon={stopIcon}>
            <Popup><strong>{stop.order_external_id}</strong><br />ETA {stop.eta_minutes} min</Popup>
          </Marker>
        )))}
        {routes.map((route) => {
          const vehicle = vehicleById.get(route.vehicle_external_id)
          const positions: [number, number][] = [
            ...(vehicle ? [[vehicle.latitude, vehicle.longitude] as [number, number]] : []),
            ...route.stops.map((stop) => [stop.latitude, stop.longitude] as [number, number]),
          ]
          return positions.length > 1 ? <Polyline key={route.vehicle_external_id} positions={positions} pathOptions={{ color: '#2563eb', weight: 4 }} /> : null
        })}
      </MapContainer>
    </section>
  )
}
