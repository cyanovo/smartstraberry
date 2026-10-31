/**
 * 番茄成熟度检测 API
 *
 * 成熟度检测统一使用本机 FastAPI：/api/detect/*
 */

/**
 * 安全解析 JSON 响应
 */
async function safeParseResponse(response) {
  const text = await response.text()
  try {
    return JSON.parse(text)
  } catch {
    return { detail: text || `HTTP ${response.status}: ${response.statusText}` }
  }
}

/**
 * 获取认证头
 */
function getAuthHeaders() {
  const token = localStorage.getItem('user_token') || ''
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`
  }
}

/**
 * 拍照并执行成熟度检测
 * @param {Object} params
 * @param {string} params.zone - 棚区 (A/B/C)
 * @param {number} [params.camera_id] - 摄像头 ID
 * @param {number} [params.conf_threshold] - 置信度阈值
 */
export async function captureAndDetect(params = {}) {
  const res = await fetch('/api/detect/camera', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const error = await safeParseResponse(res)
    throw new Error(error.detail || `检测失败: ${res.status}`)
  }
  return safeParseResponse(res)
}

/**
 * 上传图片进行检测
 * @param {File} file - 图片文件
 * @param {string} zone - 棚区
 * @param {number} [conf_threshold] - 置信度阈值
 */
export async function detectFromImage(file, zone = 'A', conf_threshold) {
  const formData = new FormData()
  formData.append('file', file)

  let url = `/api/detect/image?zone=${zone}`
  if (conf_threshold !== undefined) {
    url += `&conf_threshold=${conf_threshold}`
  }

  const token = localStorage.getItem('user_token') || ''
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) {
    const error = await safeParseResponse(res)
    throw new Error(error.detail || `检测失败: ${res.status}`)
  }
  return safeParseResponse(res)
}

/**
 * 查询检测历史
 * @param {Object} params
 * @param {string} [params.zone] - 棚区筛选
 * @param {number} [params.limit] - 返回数量
 */
export async function getDetectHistory(params = {}) {
  const query = new URLSearchParams()
  if (params.zone) query.set('zone', params.zone)
  if (params.limit) query.set('limit', String(params.limit))

  const res = await fetch(`/api/detect/history?${query.toString()}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    const error = await safeParseResponse(res)
    throw new Error(error.detail || `查询失败: ${res.status}`)
  }
  return safeParseResponse(res)
}

/**
 * 获取各区域成熟度统计（调用 Docker 后端）
 */
export async function getDetectStats() {
  const res = await fetch('/api/detect/stats', {
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    const error = await safeParseResponse(res)
    throw new Error(error.detail || `查询失败: ${res.status}`)
  }
  return safeParseResponse(res)
}

/**
 * 获取摄像头状态
 */
export async function getCameraStatus() {
  const res = await fetch('/api/detect/camera/status', {
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    const error = await safeParseResponse(res)
    throw new Error(error.detail || `查询失败: ${res.status}`)
  }
  return safeParseResponse(res)
}

/**
 * 列出所有可用摄像头
 */
export async function listCameras() {
  const res = await fetch('/api/detect/camera/list', {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`查询失败: ${res.status}`)
  return res.json()
}
