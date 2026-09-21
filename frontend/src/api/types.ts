export type Order = {
  external_id: string
  latitude: number
  longitude: number
  demand: number
  priority: number
  status: string
}

export type Vehicle = {
  external_id: string
  latitude: number
  longitude: number
  capacity: number
  status: string
}

export type UnassignedOrder = {
  order_external_id: string
  reason: string
}

export type RouteStop = {
  order_external_id: string
  latitude: number
  longitude: number
  eta_minutes: number
}

export type Route = {
  vehicle_external_id: string
  distance_km: number
  duration_minutes: number
  stops: RouteStop[]
}

export type Metrics = {
  total_distance_km: number
  total_duration_minutes: number
}

export type DashboardData = {
  summary: {
    total_orders: number
    assigned_orders: number
    unassigned_orders: number
    active_vehicles: number
  }
  orders: Order[]
  vehicles: Vehicle[]
  metrics: Metrics
  unassigned: UnassignedOrder[]
}

export type RoutePlan = {
  id: number
  routes: Route[]
  metrics: Metrics
  unassigned: UnassignedOrder[]
}

export type ImportError = {
  row?: number
  field?: string
  reason: string
}
