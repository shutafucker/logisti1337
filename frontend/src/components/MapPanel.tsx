import { useEffect, useState } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import type { Order, Route, UnassignedOrder, Vehicle } from '../api/types'
import { number, reasonLabel, routeColor, statusLabel } from './labels'
import 'leaflet/dist/leaflet.css'

type Props = { vehicles: Vehicle[]; routes: Route[]; orders: Order[]; unassigned?: UnassignedOrder[]; excludedVehicleIds?: string[] }
const fallbackCenter: [number, number] = [51.1694, 71.4491]
const pin = (label: string, color: string) => L.divIcon({ className: 'map-pin', html: `<span style="background:${color}">${label}</span>`, iconSize: [28, 28], iconAnchor: [14, 14] })

function FitPoints({ coordinates }: { coordinates: string }) {
  const map = useMap()
  useEffect(() => {
    const points = JSON.parse(coordinates) as [number, number][]
    if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [32, 32], maxZoom: 14 })
    else map.setView(fallbackCenter, 12)
  }, [map, coordinates])
  return null
}

export function MapPanel({ vehicles, routes, orders, unassigned = [], excludedVehicleIds = [] }: Props) {
  const [tileError, setTileError] = useState(false)
  const vehicleById = new Map(vehicles.map(vehicle => [vehicle.external_id, vehicle]))
  const orderById = new Map(orders.map(order => [order.external_id, order]))
  const coordinates = JSON.stringify([...vehicles, ...orders, ...routes.flatMap(route => route.stops)].map(point => [point.latitude, point.longitude]))
  return <section className="map-card" aria-label="Карта маршрутов">
    <div className="map-card__header"><h2>Карта плана доставки</h2><span>OpenStreetMap</span></div>
    <p className="map-caption">Линии соединяют точки напрямую. Дороги, пробки и GPS-перемещение не учитываются.</p>
    {tileError && <p className="warning" role="status">Подложка карты недоступна. Маршруты и заказы доступны в таблицах ниже.</p>}
    <MapContainer center={fallbackCenter} zoom={12} scrollWheelZoom className="map">
      <FitPoints coordinates={coordinates} />
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{ tileerror: () => setTileError(true), tileload: () => setTileError(false) }} />
      {vehicles.map(vehicle => <Marker key={vehicle.external_id} position={[vehicle.latitude, vehicle.longitude]} icon={pin('М', excludedVehicleIds.includes(vehicle.external_id) ? '#64748b' : routeColor(vehicle.external_id))}>
        <Popup><strong>{vehicle.external_id}</strong><br />{excludedVehicleIds.includes(vehicle.external_id) ? 'Исключена из плана' : statusLabel(vehicle.status)} · Вместимость {number(vehicle.capacity, 1)}</Popup>
      </Marker>)}
      {routes.flatMap(route => route.stops.map((stop, index) => <Marker key={`${route.vehicle_external_id}-${stop.order_external_id}`} position={[stop.latitude, stop.longitude]} icon={pin(String(index + 1), routeColor(route.vehicle_external_id))}>
        <Popup><strong>{stop.order_external_id}</strong><br />Машина {route.vehicle_external_id} · Остановка {index + 1}<br />ETA {number(stop.eta_minutes)} мин, с обслуживанием</Popup>
      </Marker>))}
      {unassigned.map(item => {
        const order = orderById.get(item.order_external_id)
        return order ? <Marker key={`unassigned-${item.order_external_id}`} position={[order.latitude, order.longitude]} icon={pin('!', '#b91c1c')}><Popup><strong>{item.order_external_id}</strong><br />Без машины: {reasonLabel(item.reason)}</Popup></Marker> : null
      })}
      {routes.map(route => {
        const vehicle = vehicleById.get(route.vehicle_external_id)
        const positions: [number, number][] = [...(vehicle ? [[vehicle.latitude, vehicle.longitude] as [number, number]] : []), ...route.stops.map(stop => [stop.latitude, stop.longitude] as [number, number])]
        return positions.length > 1 ? <Polyline key={route.vehicle_external_id} positions={positions} pathOptions={{ color: routeColor(route.vehicle_external_id), weight: 4 }} /> : null
      })}
    </MapContainer>
    <div className="map-legend" aria-label="Легенда карты">{routes.map(route => <span key={route.vehicle_external_id}><i style={{ background: routeColor(route.vehicle_external_id) }} />{route.vehicle_external_id}</span>)}<span><i style={{ background: '#b91c1c' }} />! Без машины</span><span>М — машина · цифра — остановка</span></div>
  </section>
}
