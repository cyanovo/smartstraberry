/**
 * 大模型视觉识别 API
 *
 * 基于 Qwen3-VL-Plus 提供番茄成熟度评估、种植建议、病虫害识别
 */

import { apiPost } from './base'

/**
 * 上传图片进行大模型视觉分析
 * @param {File} file - 图片文件
 * @returns {Promise<{ok: boolean, result: object}>}
 */
export function analyzeImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiPost('/api/vlm/analyze', formData)
}

/**
 * 发送 base64 图片进行大模型视觉分析
 * @param {string} imageBase64 - base64 编码的图片
 * @returns {Promise<{ok: boolean, result: object}>}
 */
export function analyzeBase64(imageBase64) {
  return apiPost('/api/vlm/analyze-base64', { image_base64: imageBase64 })
}
