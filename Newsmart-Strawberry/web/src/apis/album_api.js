import { apiGet, apiPost } from './base'

export const listAlbums = (page = 1) => apiGet(`/api/albums?limit=50&offset=${(page - 1) * 50}`)
export const createAlbum = (data) => apiPost('/api/albums', data)
export const listAlbumPhotos = (id, page = 1) => apiGet(`/api/albums/${id}/photos?limit=24&offset=${(page - 1) * 24}`)
export function uploadAlbumPhoto(id, file, capturedAt) {
  const data = new FormData()
  data.append('file', file)
  if (capturedAt) data.append('captured_at', capturedAt)
  return apiPost(`/api/albums/${id}/photos`, data)
}
export async function getAlbumPhotoFile(id, thumbnail = false) {
  const response = await apiGet(`/api/albums/photos/${id}/file?thumbnail=${thumbnail}`, {}, true, 'blob')
  return response.blob()
}
export async function downloadAlbumArchive(id) {
  const response = await apiGet(`/api/albums/${id}/archive`, {}, true, 'blob')
  return response.blob()
}
