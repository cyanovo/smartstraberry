/**
 * 番茄大棚共享数据 —— 成熟度管理中心、采摘小车派发 共用
 * 后续可替换为后端 API 调用
 */

export const zoneConfig = {
  A: { id: 'A', name: 'A 区', rows: 'A2 / A3 行', cart: 'R-02', duration: '约 45 分钟' },
  B: { id: 'B', name: 'B 区', rows: 'B1 / B2 行', cart: 'R-01', duration: '约 38 分钟' },
  C: { id: 'C', name: 'C 区', rows: 'C3 / C4 行', cart: 'R-02', duration: '约 35 分钟' }
}

/** 循迹扫描记录（成熟度管理中心展示用） */
export const scanRecords = [
  { id: 'S-1042', zone: 'A', path: 'A2-A3 行', time: '今天 13:42', robot: 'R-02', count: 1286, maturity: 86 },
  { id: 'S-1041', zone: 'B', path: 'B1-B2 行', time: '今天 11:20', robot: 'R-01', count: 936, maturity: 74 },
  { id: 'S-1040', zone: 'C', path: 'C3-C4 行', time: '今天 09:10', robot: 'R-02', count: 812, maturity: 68 },
  { id: 'S-1039', zone: 'A', path: 'A1 行', time: '昨天 16:35', robot: 'R-01', count: 1184, maturity: 81 }
]

/** 根据扫描记录计算区域汇总（供派发页面使用） */
export function getZoneDispatchData(zoneId) {
  const cfg = zoneConfig[zoneId]
  const scan = scanRecords.find(s => s.zone === zoneId && s.time.startsWith('今天'))
  if (!scan) return null
  const matureRatio = scan.maturity / 100
  const matureCount = Math.round(scan.count * matureRatio)
  const yieldKg = Math.round(matureCount * 0.1)
  return {
    ...cfg,
    matureCount: matureCount.toLocaleString(),
    totalCount: scan.count.toLocaleString(),
    yield: `${yieldKg} kg`,
    maturity: scan.maturity
  }
}

/** 采摘记录 */
export const harvestRecords = [
  { id: 'H-005', date: '2026-06-24', time: '14:27', zone: 'A 区', rows: 'A2/A3 行', yield: '112 kg', fruitCount: '1,105', status: 'completed', statusText: '已完成' },
  { id: 'H-004', date: '2026-06-22', time: '10:15', zone: 'A 区', rows: 'A1 行', yield: '98 kg', fruitCount: '967', status: 'completed', statusText: '已完成' },
  { id: 'H-003', date: '2026-06-19', time: '15:40', zone: 'B 区', rows: 'B2 行', yield: '73 kg', fruitCount: '712', status: 'completed', statusText: '已完成' },
  { id: 'H-002', date: '2026-06-17', time: '11:20', zone: 'A 区', rows: 'A3 行', yield: '91 kg', fruitCount: '902', status: 'completed', statusText: '已完成' },
  { id: 'H-001', date: '2026-06-14', time: '16:05', zone: 'C 区', rows: 'C4 行', yield: '68 kg', fruitCount: '674', status: 'completed', statusText: '已完成' }
]

/** 采摘阈值（可配置，持久化到 localStorage） */
const THRESHOLD_KEY = 'tomato-harvest-threshold'
const DEFAULT_THRESHOLD = 80

export function getHarvestThreshold() {
  try {
    const v = localStorage.getItem(THRESHOLD_KEY)
    const n = parseInt(v, 10)
    return (n >= 0 && n <= 100) ? n : DEFAULT_THRESHOLD
  } catch { return DEFAULT_THRESHOLD }
}

export function setHarvestThreshold(value) {
  try {
    localStorage.setItem(THRESHOLD_KEY, String(value))
  } catch { /* ignore */ }
}

/** 采摘建议 */
export const harvestAdvice = [
  { level: 'ready', levelText: '执行', title: 'A2/A3 行成熟度超过 80%', desc: '建议立即派发采摘小车，优先采摘颜色均匀、畸形率低的果实。' },
  { level: 'watch', levelText: '观察', title: 'B 区预计 2 天后进入采摘窗口', desc: '成熟度暂未达到阈值，建议明天上午再次循迹扫描。' },
  { level: 'normal', levelText: '正常', title: 'C 区保持当前补光与营养液策略', desc: '成熟度增长稳定，暂不建议提前采摘。' }
]
