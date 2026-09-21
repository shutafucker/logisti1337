import type { PlanSnapshot, ReplanResult } from '../api/types'
import { number } from './labels'

const metrics: { key: keyof PlanSnapshot; label: string; unit: string; digits: number }[] = [
  { key: 'assigned_orders', label: 'Назначено заказов', unit: '', digits: 0 },
  { key: 'unassigned_orders', label: 'Без машины', unit: '', digits: 0 },
  { key: 'distance_km', label: 'Расстояние', unit: ' км', digits: 1 },
  { key: 'duration_minutes', label: 'Сумма времени маршрутов', unit: ' мин', digits: 0 },
]

export function PlanComparison({ result }: { result: ReplanResult }) {
  return <section className="section comparison" aria-label="Сравнение планов">
    <p className="eyebrow">РЕЗУЛЬТАТ СЦЕНАРИЯ</p>
    <h2>Было → стало</h2>
    <p className="muted">Исходный план №{result.base_plan_id} → новый №{result.plan.id}. Исключены: {result.unavailable_vehicle_ids.join(', ') || 'нет'}.</p>
    {result.comparison.after.assigned_orders < result.comparison.before.assigned_orders && <p className="warning" role="status">Доставок стало меньше. Снижение расстояния или времени не означает улучшение обслуживания.</p>}
    <div className="table-wrap"><table><caption className="sr-only">Показатели до и после пересчёта</caption><thead><tr><th>Показатель</th><th>Было</th><th>Стало</th><th>Изменение</th></tr></thead>
      <tbody>{metrics.map(({ key, label, unit, digits }) => <tr key={key}><th scope="row">{label}</th><td>{number(result.comparison.before[key], digits)}{unit}</td><td>{number(result.comparison.after[key], digits)}{unit}</td><td>{result.comparison.delta[key] > 0 ? '+' : ''}{number(result.comparison.delta[key], digits)}{unit}</td></tr>)}</tbody></table></div>
    <p className="muted small">Изменение = стало − было. Время — сумма по всем маршрутам, а не момент завершения всей доставки.</p>
  </section>
}
