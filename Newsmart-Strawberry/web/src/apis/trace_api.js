import { apiGet, apiPost, apiPut, apiDelete } from './base'

// ══════════════════════════════════════════════════════════════════════
//  公开溯源查询（无需登录，消费者使用）
// ══════════════════════════════════════════════════════════════════════

export function traceQueryPublic(code) {
  return apiGet(`/api/trace/query/${code}`, {}, false)
}

export function traceByBatchCodePublic(batchCode) {
  return apiGet(`/api/trace/query/batch/${batchCode}`, {}, false)
}

// ══════════════════════════════════════════════════════════════════════
//  统计
// ══════════════════════════════════════════════════════════════════════

/** 获取溯源系统统计数据 */
export function fetchTraceStats() {
  return apiGet('/api/trace/stats')
}

// ══════════════════════════════════════════════════════════════════════
//  地块
// ══════════════════════════════════════════════════════════════════════

export function listPlots() {
  return apiGet('/api/trace/plot/list')
}

export function getPlot(plotId) {
  return apiGet(`/api/trace/plot/${plotId}`)
}

export function createPlot(data) {
  return apiPost('/api/trace/plot/create', data)
}

export function updatePlot(plotId, data) {
  return apiPut(`/api/trace/plot/${plotId}`, data)
}

export function deletePlot(plotId) {
  return apiDelete(`/api/trace/plot/${plotId}`)
}

// ══════════════════════════════════════════════════════════════════════
//  种子
// ══════════════════════════════════════════════════════════════════════

export function listSeeds() {
  return apiGet('/api/trace/seed/list')
}

export function getSeed(seedId) {
  return apiGet(`/api/trace/seed/${seedId}`)
}

export function createSeed(data) {
  return apiPost('/api/trace/seed/create', data)
}

export function updateSeed(seedId, data) {
  return apiPut(`/api/trace/seed/${seedId}`, data)
}

export function deleteSeed(seedId) {
  return apiDelete(`/api/trace/seed/${seedId}`)
}

// ══════════════════════════════════════════════════════════════════════
//  种植批次
// ══════════════════════════════════════════════════════════════════════

export function listBatches(limit = 50) {
  return apiGet(`/api/trace/batch/list?limit=${limit}`)
}

export function getBatch(batchId) {
  return apiGet(`/api/trace/batch/${batchId}`)
}

export function createBatch(data) {
  return apiPost('/api/trace/batch/create', data)
}

export function updateBatch(batchId, data) {
  return apiPut(`/api/trace/batch/${batchId}`, data)
}

export function deleteBatch(batchId) {
  return apiDelete(`/api/trace/batch/${batchId}`)
}

// ══════════════════════════════════════════════════════════════════════
//  农事操作
// ══════════════════════════════════════════════════════════════════════

export function listActivities(batchId) {
  return apiGet(`/api/trace/activity/list/${batchId}`)
}

export function addActivity(data) {
  return apiPost('/api/trace/activity/add', data)
}

export function deleteActivity(activityId) {
  return apiDelete(`/api/trace/activity/${activityId}`)
}

// ══════════════════════════════════════════════════════════════════════
//  环境数据
// ══════════════════════════════════════════════════════════════════════

export function listEnvironments(batchId) {
  return apiGet(`/api/trace/environment/list/${batchId}`)
}

export function addEnvironment(data) {
  return apiPost('/api/trace/environment/add', data)
}

export function deleteEnvironment(envId) {
  return apiDelete(`/api/trace/environment/${envId}`)
}

// ══════════════════════════════════════════════════════════════════════
//  采摘记录
// ══════════════════════════════════════════════════════════════════════

export function listHarvests(batchId) {
  return apiGet(`/api/trace/harvest/list/${batchId}`)
}

export function addHarvest(data) {
  return apiPost('/api/trace/harvest/add', data)
}

// ══════════════════════════════════════════════════════════════════════
//  质检记录
// ══════════════════════════════════════════════════════════════════════

export function listInspections(batchId) {
  return apiGet(`/api/trace/inspection/list/${batchId}`)
}

export function addInspection(data) {
  return apiPost('/api/trace/inspection/add', data)
}

// ══════════════════════════════════════════════════════════════════════
//  包装记录
// ══════════════════════════════════════════════════════════════════════

export function listPackages(batchId) {
  return apiGet(`/api/trace/package/list/${batchId}`)
}

export function addPackage(data) {
  return apiPost('/api/trace/package/add', data)
}

// ══════════════════════════════════════════════════════════════════════
//  溯源查询
// ══════════════════════════════════════════════════════════════════════

export function traceQuery(code) {
  return apiGet(`/api/trace/query/${code}`)
}

export function traceByBatchCode(batchCode) {
  return apiGet(`/api/trace/query/batch/${batchCode}`)
}

// ══════════════════════════════════════════════════════════════════════
//  照片
// ══════════════════════════════════════════════════════════════════════

export function listPhotos(batchId, photoType) {
  const url = photoType ? `/api/trace/photos/${batchId}?photo_type=${photoType}` : `/api/trace/photos/${batchId}`
  return apiGet(url)
}

export function uploadPhoto(batchId, formData) {
  return apiPost(`/api/trace/upload/${batchId}`, formData)
}

export function deletePhoto(photoId) {
  return apiDelete(`/api/trace/photos/${photoId}`)
}

// ══════════════════════════════════════════════════════════════════════
//  区块链
// ══════════════════════════════════════════════════════════════════════

export function getBlockchainStatus() {
  return apiGet('/api/trace/blockchain/status')
}

// ══════════════════════════════════════════════════════════════════════
//  二维码
// ══════════════════════════════════════════════════════════════════════

export function generateQR(traceCode) {
  return apiGet(`/api/trace/qr/generate/${traceCode}`)
}

export function decodeQR(formData) {
  return apiPost('/api/trace/qr/decode', formData)
}

// ══════════════════════════════════════════════════════════════════════
//  溯源事件
// ══════════════════════════════════════════════════════════════════════

export function listEvents(batchId) {
  return apiGet(`/api/trace/events/${batchId}`)
}
