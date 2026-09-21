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
  route_plan: RoutePlan
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

export type ImportResult = {
  accepted_count: number
  errors: ImportError[]
}

export type PlanSnapshot = {
  assigned_orders: number
  unassigned_orders: number
  distance_km: number
  duration_minutes: number
}

export type ReplanResult = {
  base_plan_id: number
  plan: RoutePlan
  comparison: { before: PlanSnapshot; after: PlanSnapshot; delta: PlanSnapshot }
  unavailable_vehicle_ids: string[]
}

export type AgentResult = {
  status: 'ready'
  action: { type: 'exclude_vehicles'; vehicle_ids: string[] }
  explanation: string
  question: null
} | {
  status: 'needs_clarification' | 'unsupported'
  action: null
  explanation: string
  question: string | null
}
