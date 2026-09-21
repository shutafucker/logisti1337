export const number = (value: number, digits = 0) => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits }).format(value)
export const reasonLabel = (reason: string) => ({
  capacity_exceeded: 'Недостаточно вместимости',
  no_available_vehicle: 'Нет доступных машин',
}[reason] ?? reason)
export const statusLabel = (status: string) => ({
  pending: 'Ожидает', assigned: 'Назначен', available: 'Доступна',
  unavailable: 'Недоступна', completed: 'Завершён', cancelled: 'Отменён',
}[status] ?? status)
const colors = ['#2563eb', '#a21caf', '#047857', '#b45309', '#be123c', '#0e7490']
export const routeColor = (id: string) => colors[[...id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % colors.length]
