export function formatTime(seconds: number): string {
  const neg = seconds < 0
  const abs = Math.abs(seconds)
  const h = Math.floor(abs / 3600)
  const m = Math.floor((abs % 3600) / 60)
  const s = abs % 60
  const pad = (n: number) => n.toString().padStart(2, '0')
  const time = h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`
  return neg ? `-${time}` : time
}

export function priorityLabel(p: string): string {
  switch (p) {
    case 'high': return 'High'
    case 'low': return 'Low'
    default: return ''
  }
}

export function priorityColor(p: string): string {
  switch (p) {
    case 'high': return 'text-red-400'
    case 'low': return 'text-zinc-500'
    default: return 'text-zinc-300'
  }
}
