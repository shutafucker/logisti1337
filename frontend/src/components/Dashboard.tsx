import { ChangeEvent, useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { AgentResult, DashboardData, ImportError, ReplanResult, RoutePlan } from '../api/types'
import { MapPanel } from './MapPanel'
import { PlanComparison } from './PlanComparison'
import { number, reasonLabel, routeColor, statusLabel } from './labels'

const formatErrors = (errors: ImportError[]) => errors.map(error => `Строка ${error.row ?? '?'}${error.field ? ` · ${error.field}` : ''}: ${error.reason}`).join('; ')
function errorMessage(error: unknown, operation: string) {
  if (error instanceof ApiError) {
    if (error.status === 404 && error.message === 'Not Found') return `${operation}: функция пока недоступна на сервере.`
    if (error.status === 409) return 'Исходный план устарел. Обновите данные и повторите действие.'
    if (error.status === 503) return 'AI временно недоступен. Можно исключить машину вручную.'
    return `${operation}: ${error.details.length ? formatErrors(error.details) : error.message}`
  }
  return `${operation}: непредвиденная ошибка. Повторите запрос.`
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [plan, setPlan] = useState<RoutePlan | null>(null)
  const [comparison, setComparison] = useState<ReplanResult | null>(null)
  const [excluded, setExcluded] = useState<string[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState<string | null>('load')
  const lock = useRef(false)
  const revision = useRef(0)
  const mounted = useRef(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [agent, setAgent] = useState<{ result: AgentResult; revision: number; planId: number } | null>(null)
  const [agentBusy, setAgentBusy] = useState(false)
  const agentLock = useRef(false)
  const agentRequest = useRef(0)
  const [agentError, setAgentError] = useState<string | null>(null)

  function invalidateAgent() {
    revision.current += 1
    agentRequest.current += 1
    agentLock.current = false
    setAgentBusy(false)
    setAgent(null)
    setAgentError(null)
  }
  function acceptDashboard(next: DashboardData) {
    setData(next); setPlan(next.route_plan); setComparison(null); setExcluded([]); setSelected([])
  }
  async function run(operation: string, action: () => Promise<void>) {
    if (lock.current) return
    lock.current = true; setBusy(operation); setError(null); setNotice(null)
    invalidateAgent()
    try { await action() }
    catch (requestError) { if (mounted.current) setError(errorMessage(requestError, operation)) }
    finally { lock.current = false; if (mounted.current) setBusy(null) }
  }
  const refresh = () => run('Обновление данных', async () => acceptDashboard(await api.getDashboard()))

  useEffect(() => {
    mounted.current = true
    let active = true
    lock.current = true
    api.getDashboard().then(next => { if (active) acceptDashboard(next) })
      .catch(requestError => { if (active) setError(errorMessage(requestError, 'Загрузка данных')) })
      .finally(() => { if (active) { lock.current = false; setBusy(null) } })
    return () => { active = false; mounted.current = false; agentRequest.current += 1 }
  }, [])

  const calculate = () => run('Расчёт маршрутов', async () => {
    const created = await api.createRoutePlan()
    const next = await api.getRoutePlan(created.id)
    setPlan(next); setComparison(null); setExcluded([]); setSelected([])
    setNotice(`План №${next.id} рассчитан.`)
  })
  const replan = (ids: string[]) => {
    if (!plan || !ids.length) return
    const baseId = plan.id
    const allIds = [...new Set([...excluded, ...ids])]
    return run('Пересчёт плана', async () => {
      const result = await api.replan(baseId, allIds)
      if (result.base_plan_id !== baseId) throw new Error('Plan mismatch')
      setPlan(result.plan); setComparison(result); setExcluded(result.unavailable_vehicle_ids); setSelected([])
      setNotice(`Новый план №${result.plan.id} готов. Исходный план №${baseId} сохранён.`)
    })
  }
  async function importFile(resource: 'orders' | 'vehicles', event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    await run('Импорт данных', async () => {
      const result = await api.importFile(resource, file)
      if (result.accepted_count > 0) {
        // The input data changed even if the subsequent dashboard request fails.
        setPlan(null); setComparison(null); setExcluded([]); setSelected([]); setData(null)
        if (result.errors.length) setError(formatErrors(result.errors))
        acceptDashboard(await api.getDashboard())
        setNotice(`Принято строк: ${result.accepted_count}. Данные и план обновлены.`)
      }
      if (result.errors.length) setError(formatErrors(result.errors))
      else if (!result.accepted_count) setNotice('В файле нет строк для импорта.')
    })
  }
  async function interpret() {
    if (!plan || !message.trim() || lock.current || agentLock.current) return
    const token = ++agentRequest.current
    const currentRevision = revision.current
    const planId = plan.id
    agentLock.current = true; setAgentBusy(true); setAgent(null); setAgentError(null)
    try {
      const result = await api.interpret(message.trim(), planId)
      if (result.status === 'ready' && (result.action?.type !== 'exclude_vehicles' || !result.action.vehicle_ids?.length || result.action.vehicle_ids.some(id => !data?.vehicles.some(vehicle => vehicle.external_id === id)))) {
        throw new ApiError('AI вернул неизвестную машину или неподдерживаемое действие. Уточните команду.')
      }
      if (mounted.current && token === agentRequest.current && currentRevision === revision.current) setAgent({ result, revision: currentRevision, planId })
    } catch (requestError) {
      if (mounted.current && token === agentRequest.current) setAgentError(errorMessage(requestError, 'Обработка команды'))
    } finally {
      if (mounted.current && token === agentRequest.current) { agentLock.current = false; setAgentBusy(false) }
    }
  }
  function editMessage(value: string) {
    agentRequest.current += 1; agentLock.current = false; setAgentBusy(false)
    setMessage(value); setAgent(null); setAgentError(null)
  }

  const assigned = plan?.routes.reduce((total, route) => total + route.stops.length, 0) ?? 0
  const unassigned = plan?.unassigned ?? []
  const available = data?.vehicles.filter(vehicle => vehicle.status.trim().toLowerCase() === 'available' && !excluded.includes(vehicle.external_id)) ?? []
  const candidate = agent?.result.status === 'ready' && agent.revision === revision.current && agent.planId === plan?.id ? agent.result : null

  return <main className="dashboard-shell">
    <header className="header"><div><p className="eyebrow">LOGISTIAI · ДИСПЕТЧЕРСКАЯ</p><h1>План доставки<br />под контролем</h1><p className="subtitle">Распределяйте заказы и проверяйте, как изменения влияют на доставку.</p></div>
      <div className="header-actions"><button className="secondary-button" disabled={!!busy} onClick={() => void refresh()}>Обновить данные</button><button className="primary-button" disabled={!!busy || !data} onClick={() => void calculate()}>{busy === 'Расчёт маршрутов' ? 'Считаем…' : 'Рассчитать маршруты'}</button></div></header>
    <section className="controls" aria-label="Импорт сценария"><div><strong>1. Загрузите исходные данные</strong><span>Заказы и машины в CSV или JSON</span></div><div className="control-actions">{(['orders', 'vehicles'] as const).map(resource => <label key={resource} className={`file-control ${busy ? 'disabled' : ''}`}>{resource === 'orders' ? 'Загрузить заказы' : 'Загрузить машины'}<input className="sr-only" aria-label={resource === 'orders' ? 'Файл заказов' : 'Файл машин'} type="file" disabled={!!busy} accept=".csv,.json,application/json,text/csv" onChange={event => void importFile(resource, event)} /></label>)}</div></section>
    {error && <section className="message message--error" role="alert"><span>{error}</span><button disabled={!!busy} onClick={() => void refresh()}>Обновить и повторить</button></section>}
    {notice && <section className="message message--success" role="status">{notice}</section>}
    {busy && <p className="progress" role="status">{busy === 'load' ? 'Загрузка данных диспетчера…' : `${busy}…`}</p>}
    {!data && !busy && <section className="section empty"><h2>Данные пока недоступны</h2><p>Проверьте соединение и обновите данные.</p></section>}
    {data && plan && <>
      <section className="stats" aria-label="Сводка плана"><Stat label="Всего заказов" value={data.summary.total_orders} /><Stat label="Назначено" value={assigned} /><Stat label="Без машины" value={unassigned.length} tone={unassigned.length ? 'risk' : ''} /><Stat label="Доступно машин" value={available.length} /><Stat label="Оценка расстояния" value={`${number(plan.metrics.total_distance_km, 1)} км`} /><Stat label="Сумма времени" value={`${number(plan.metrics.total_duration_minutes)} мин`} /></section>
      <p className="muted small">План №{plan.id}. Расстояние и время — оценки без дорог и пробок. ETA включает обслуживание точки; время суммируется по маршрутам.</p>
      <div className="scenario-grid">
        <section className="section"><p className="eyebrow">2. ПРОВЕРЬТЕ ИЗМЕНЕНИЕ</p><h2>Исключить машины из плана</h2><p className="muted">Выберите недоступные машины. Статусы автопарка не изменятся.</p>
          <fieldset disabled={!!busy}><legend className="sr-only">Машины для исключения</legend><div className="vehicle-options">{available.map(vehicle => <label key={vehicle.external_id}><input type="checkbox" checked={selected.includes(vehicle.external_id)} onChange={event => setSelected(current => event.target.checked ? [...current, vehicle.external_id] : current.filter(id => id !== vehicle.external_id))} /><span><strong>{vehicle.external_id}</strong><small>Вместимость: {number(vehicle.capacity, 1)}</small></span></label>)}</div></fieldset>
          {!available.length && <p className="empty">Доступных машин нет. Загрузите автопарк или рассчитайте исходный план заново.</p>}
          {!!excluded.length && <p className="muted small">Уже исключены: {excluded.join(', ')}.</p>}
          <button className="primary-button" disabled={!!busy || !selected.length} onClick={() => void replan(selected)}>Исключить и пересчитать</button>
        </section>
        <section className="section"><p className="eyebrow">ИЛИ ОПИШИТЕ СИТУАЦИЮ</p><h2>AI-помощник диспетчера</h2><form onSubmit={event => { event.preventDefault(); void interpret() }}><label className="field-label" htmlFor="agent-message">Что изменилось?</label><textarea id="agent-message" maxLength={2000} value={message} disabled={!!busy} onChange={event => editMessage(event.target.value)} placeholder="Укажите машину и что с ней произошло" rows={3} />
          <div className="examples">{available.slice(0, 2).map(vehicle => <button key={vehicle.external_id} type="button" disabled={!!busy} onClick={() => editMessage(`Машина ${vehicle.external_id} сломалась`)}>{vehicle.external_id} сломалась</button>)}</div>
          <button className="secondary-button" disabled={!!busy || agentBusy || !message.trim()}>{agentBusy ? 'Разбираем команду…' : 'Разобрать команду'}</button></form>
          <p className="muted small">AI предложит действие. Пересчёт начнётся после вашего подтверждения.</p>
          {agentError && <p className="warning" role="alert">{agentError}</p>}
          {agent && <div className="agent-result" role="status"><p>{agent.result.explanation}</p>{agent.result.status === 'needs_clarification' && <p><strong>{agent.result.question}</strong></p>}{agent.result.status === 'unsupported' && <p>Попробуйте команду об исключении машины.</p>}{candidate && <><p>Исключить: <strong>{candidate.action.vehicle_ids.join(', ')}</strong></p><button className="primary-button" disabled={!!busy} onClick={() => void replan(candidate.action.vehicle_ids)}>Применить и пересчитать</button></>}</div>}
        </section>
      </div>
      {comparison && <PlanComparison result={comparison} />}
      <section className="content-grid"><MapPanel vehicles={data.vehicles} routes={plan.routes} orders={data.orders} unassigned={unassigned} excludedVehicleIds={excluded} /><aside className="risk-panel"><p className="eyebrow">ТРЕБУЕТ ВНИМАНИЯ</p><h2>Заказы без машины</h2>{unassigned.length ? <ul>{unassigned.map(item => <li key={item.order_external_id}><strong>{item.order_external_id}</strong><span>{reasonLabel(item.reason)}</span></li>)}</ul> : <p className="empty">Неназначенных заказов нет.</p>}</aside></section>
      <section className="section"><div className="section-heading"><div><p className="eyebrow">3. ПРОВЕРЬТЕ ПЛАН</p><h2>Маршруты машин</h2></div><span>{number(plan.metrics.total_duration_minutes)} мин суммарно</span></div>
        {!plan.routes.length ? <p className="empty">Маршрутов нет. Проверьте доступность машин и список неназначенных заказов.</p> : <div className="route-grid">{plan.routes.map(route => <article className="route-card" style={{ borderTop: `3px solid ${routeColor(route.vehicle_external_id)}` }} key={route.vehicle_external_id}><h3>Маршрут · {route.vehicle_external_id}</h3><p>{number(route.distance_km, 1)} км · {number(route.duration_minutes)} мин · остановок: {route.stops.length}</p><ol>{route.stops.map(stop => <li key={stop.order_external_id}><strong>{stop.order_external_id}</strong><span>ETA {number(stop.eta_minutes)} мин от старта, с обслуживанием</span></li>)}</ol></article>)}</div>}
      </section>
      <section className="tables"><DataTable title="Заказы" headers={['Заказ', 'Приоритет', 'Груз', 'Статус']} rows={data.orders.map(order => [order.external_id, String(order.priority), number(order.demand, 1), statusLabel(order.status)])} empty="Заказов нет. Загрузите файл заказов." /><DataTable title="Автопарк" headers={['Машина', 'Вместимость', 'Статус']} rows={data.vehicles.map(vehicle => [vehicle.external_id, number(vehicle.capacity, 1), excluded.includes(vehicle.external_id) ? 'Исключена из плана' : statusLabel(vehicle.status)])} empty="Машин нет. Загрузите файл автопарка." /></section>
    </>}
  </main>
}

function Stat({ label, value, tone = '' }: { label: string; value: string | number; tone?: string }) {
  return <div className={`stat ${tone}`} aria-label={label}><span>{label}</span><strong>{value}</strong></div>
}
function DataTable({ title, headers, rows, empty }: { title: string; headers: string[]; rows: string[][]; empty: string }) {
  return <section className="table-card"><h2>{title}</h2>{rows.length ? <div className="table-wrap"><table><thead><tr>{headers.map(header => <th key={header} scope="col">{header}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row[0]}>{row.map((value, index) => <td key={index}>{value}</td>)}</tr>)}</tbody></table></div> : <p className="empty">{empty}</p>}</section>
}
