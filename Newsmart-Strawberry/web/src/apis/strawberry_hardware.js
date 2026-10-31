import { request, getToken, clearToken } from './strawberry_api'

export const deviceDetail = id => request(`/system/device/${id}`)
export const saveDevice = data => request('/system/device', { method: data.deviceId ? 'PUT' : 'POST', body: JSON.stringify(data) })
export const deleteDevice = id => request(`/system/device/${id}`, { method: 'DELETE' })
export const deviceOptions = async resource => {
  const rows = []
  for (let page = 1; ; page++) {
    const result = await request(`/system/device/${resource}?pageNum=${page}&pageSize=100`)
    rows.push(...result.rows)
    if (rows.length >= result.total || !result.rows.length) return rows
  }
}
export const controlHardware = (kind, data) => {
  if (!['fan', 'irrigation'].includes(kind) || !['start', 'stop'].includes(data.action)) throw new Error('不支持的控制指令')
  return request(`/system/record/${kind}`, { method: 'POST', body: JSON.stringify(data) })
}
export async function exportDevices(params) {
  const response = await fetch('/legacy/system/device/export', {
    method: 'POST', headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params)
  })
  if (!response.ok) throw new Error(`导出失败 (${response.status})`)
  if (response.headers.get('content-type')?.includes('json')) {
    const result = await response.json()
    if (result.code === 401) clearToken()
    throw new Error(result.msg || '导出失败')
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `devices-${Date.now()}.xlsx`
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
