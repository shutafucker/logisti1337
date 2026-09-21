import { ChangeEvent, useCallback, useEffect, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { DashboardData, ImportError, Route, RoutePlan } from '../api/types'
import { MapPanel } from './MapPanel'

const initialData: DashboardData = {
  summary: { total_orders: 0, assigned_orders: 0, unassigned_orders: 0, active_vehicles: 0 },
  orders: [], vehicles: [], metrics: { total_distance_km: 0, total_duration_minutes: 0 }, unassigned: [],
}

const humanize = (value: string) => value.replace(/_/g, ' ')
const errorSummary = (error: unknown) => error instanceof ApiError ? error.message : 'Unexpected request error. Please try again.'

function ImportControl({ resource, onError, onSuccess }: { resource: 'orders' | 'vehicles'; onError: (message: string) => void; onSuccess: () => void }) {
  const label = `${resource[0].toUpperCase()}${resource.slice(1)} file`
  const importFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const result = await api.importFile(resource, file)
      const details = result.errors ?? []
      if (details.length) {
        onError(formatImportErrors(details))
      } else {
        onSuccess()
      }
    } catch (error) {
      const details = error instanceof ApiError ? error.details : []
      onError(details.length ? formatImportErrors(details) : errorSummary(error))
    } finally {
      event.target.value = ''
    }
  }
  return <label className="file-control">{label}<input aria-label={label} type="file" accept=".csv,.json,application/json,text/csv" onChange={importFile} /></label>
}

function formatImportErrors(errors: ImportError[]) {
  return errors.map((error) => `Row ${error.row ?? '?'}${error.field ? ` · ${error.field}` : ''}: ${error.reason}`).join('. ')
}

function Stat({ label, value, tone = '' }: { label: string; value: string | number; tone?: string }) {
  return <div className={`stat ${tone}`}><span>{label}</span><strong>{value}</strong></div>
}

function RouteCards({ routes }: { routes: Route[] }) {
  if (!routes.length) return <p className="empty">No calculated routes yet. Choose “Calculate routes” to create a plan.</p>
  return <div className="route-grid">{routes.map((route) => <article className="route-card" key={route.vehicle_external_id}>
    <h3>Route · {route.vehicle_external_id}</h3>
    <p>{route.distance_km.toFixed(1)} km · {Math.round(route.duration_minutes)} min · {route.stops.length} stops</p>
    <ol>{route.stops.map((stop) => <li key={stop.order_external_id}><strong>{stop.order_external_id}</strong><span>ETA {Math.round(stop.eta_minutes)} min</span></li>)}</ol>
  </article>)}</div>
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData>(initialData)
  const [plan, setPlan] = useState<RoutePlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true); setError(null)
    try { setData(await api.getDashboard()) }
    catch (requestError) { setError(`Couldn't load the dispatcher dashboard. ${errorSummary(requestError)}`) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void loadDashboard() }, [loadDashboard])

  const calculate = async () => {
    setCalculating(true); setError(null); setNotice(null)
    try {
      const created = await api.createRoutePlan()
      const detailedPlan = await api.getRoutePlan(created.id)
      setPlan(detailedPlan)
      setData((current) => ({ ...current, metrics: detailedPlan.metrics, unassigned: detailedPlan.unassigned }))
    } catch (requestError) { setError(`Couldn't calculate routes. ${errorSummary(requestError)}`) }
    finally { setCalculating(false) }
  }

  const onImportSuccess = () => { setNotice('Import accepted. Dashboard data has been refreshed.'); void loadDashboard() }
  const visibleRoutes = plan?.routes ?? []
  const unassigned = plan?.unassigned ?? data.unassigned
  const metrics = plan?.metrics ?? data.metrics

  return <main className="dashboard-shell">
    <header className="header"><div><p className="eyebrow">LOGISTIAI · DISPATCH</p><h1>Move every order with confidence.</h1><p className="subtitle">Route health, capacity risk, and field status in one operational view.</p></div><button className="primary-button" onClick={calculate} disabled={loading || calculating}>{calculating ? 'Calculating…' : 'Calculate routes'}</button></header>
    <section className="controls" aria-label="Scenario controls"><div><strong>Import a scenario</strong><span>CSV or JSON files are validated by the API.</span></div><div className="control-actions"><ImportControl resource="orders" onError={setError} onSuccess={onImportSuccess} /><ImportControl resource="vehicles" onError={setError} onSuccess={onImportSuccess} /></div></section>
    {error && <section className="message message--error" role="alert"><span>{error}</span><button onClick={() => void loadDashboard()}>Try again</button></section>}
    {notice && <section className="message message--success" role="status">{notice}</section>}
    {loading ? <section className="loading" aria-live="polite">Loading dispatcher data…</section> : <>
      <section className="stats" aria-label="Operational summary"><Stat label="Orders" value={data.summary.total_orders} /><Stat label="Assigned" value={data.summary.assigned_orders} tone="good" /><Stat label="At risk" value={data.summary.unassigned_orders} tone="risk" /><Stat label="Active vehicles" value={data.summary.active_vehicles} /><Stat label="Route distance" value={`${metrics.total_distance_km.toFixed(1)} km`} /></section>
      <section className="content-grid"><MapPanel vehicles={data.vehicles} routes={visibleRoutes} orders={data.orders} /><aside className="risk-panel"><p className="eyebrow">EXCEPTIONS</p><h2>Unassigned orders</h2>{unassigned.length ? <ul>{unassigned.map((item) => <li key={item.order_external_id}><strong>{item.order_external_id}</strong><span>{humanize(item.reason)}</span></li>)}</ul> : <p className="empty">No unassigned orders. Capacity is clear.</p>}</aside></section>
      <section className="section"><div className="section-heading"><div><p className="eyebrow">PLAN DETAIL</p><h2>Vehicle routes</h2></div><span>{Math.round(metrics.total_duration_minutes)} min total</span></div><RouteCards routes={visibleRoutes} /></section>
      <section className="tables"><DataTable title="Orders" headers={['Order', 'Priority', 'Demand', 'Status']} rows={data.orders.map((order) => [order.external_id, String(order.priority), String(order.demand), order.status])} empty="No orders in this scenario." /><DataTable title="Vehicles" headers={['Vehicle', 'Capacity', 'Status']} rows={data.vehicles.map((vehicle) => [vehicle.external_id, String(vehicle.capacity), vehicle.status])} empty="No vehicles in this scenario." /></section>
    </>}
  </main>
}

function DataTable({ title, headers, rows, empty }: { title: string; headers: string[]; rows: string[][]; empty: string }) {
  return <section className="table-card"><h2>{title}</h2>{rows.length ? <div className="table-wrap"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row[0]}>{row.map((value, index) => <td key={`${row[0]}-${index}`} className={index === row.length - 1 ? 'status' : ''}>{value}</td>)}</tr>)}</tbody></table></div> : <p className="empty">{empty}</p>}</section>
}
