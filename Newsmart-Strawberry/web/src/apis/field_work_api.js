import { apiGet, apiPost, apiDelete } from './base'

const root = '/api/field-work'
export const fieldRecords = (kind, parent, offset = 0) => apiGet(`${root}/records/${kind}?${new URLSearchParams({ ...(parent !== undefined ? { parent_id: parent } : {}), offset, limit: 100 })}`)
export const createCapture = (data) => apiPost(`${root}/captures`, data)
export const captureAction = (id, action) => apiPost(`${root}/captures/${id}/${action}`, {})
export const createBackup = (data) => apiPost(`${root}/backups`, data)
export const runDetection = (data) => apiPost(`${root}/detections`, data)
export const runAnalysis = (data) => apiPost(`${root}/analyses`, data)
export const fieldKnowledge = () => apiGet(`${root}/knowledge`)
export const activateModel = (id) => apiPost(`${root}/models/${id}/activate`, {})
export const removeShared = (id) => apiDelete(`${root}/shared/${id}`)
export const removeAlbumPhoto = (id) => apiDelete(`${root}/photos/${id}`)
export const confirmControl = (id, thread, accept) => apiPost(`${root}/control/${id}/confirm`, { thread_id: thread, accept })
export function uploadFieldFile(kind, file, fields = {}) {
  const data = new FormData()
  data.append('file', file)
  Object.entries(fields).forEach(([key, value]) => data.append(key, value))
  return apiPost(`${root}/${kind}`, data)
}
export function createSharedFolder(name) {
  const data = new FormData()
  data.append('name', name)
  return apiPost(`${root}/folders`, data)
}
export async function downloadFieldFile(row) {
  const response = await apiGet(`${root}/files/${row.id}`, {}, true, 'blob')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = row.name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
