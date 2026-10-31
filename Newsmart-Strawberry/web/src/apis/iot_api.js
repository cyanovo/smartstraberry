import { apiGet, apiPost } from './base'

export function fetchSensorHistory(params) {
  return apiGet(`/api/iot/history?${new URLSearchParams(params)}`)
}

export function fetchSensorDevices() {
  return apiGet('/api/iot/history/devices')
}

export async function downloadSensorHistory(params) {
  const response = await apiGet(`/api/iot/history/export?${new URLSearchParams(params)}`, {}, true, 'blob')
  return response.blob()
}

/** 获取 IoT 仪表盘全量数据（空气 + 土壤 + 执行器） */
export function fetchIotDashboard() {
  return apiGet('/api/iot/dashboard')
}

/** 获取最新空气传感器数据 */
export function fetchAirSensor() {
  return apiGet('/api/iot/sensors/air')
}

/** 获取最新土壤传感器数据 */
export function fetchSoilSensor() {
  return apiGet('/api/iot/sensors/soil')
}

/** 控制执行器：key = irrigation | pump */
export function setActuator(key, value) {
  return apiPost(`/api/iot/actuators/${key}?value=${value}`)
}

/** 控制 LED 补光灯（支持单路控制） */
export function controlLed(ledCommand) {
  return apiPost('/api/iot/actuators/led', ledCommand)
}

/** 设置工作模式 mode=manual(手动) / mode=ai(AI)，后端兼容旧 auto */
export function setMode(mode) {
  return apiPost(`/api/iot/mode?mode=${mode}`)
}

export function setRedBrightness(value) {
  return apiPost(`/api/iot/light/red?value=${value}`)
}

export function setBlueBrightness(value) {
  return apiPost(`/api/iot/light/blue?value=${value}`)
}

export function setFillLightMode(value) {
  return apiPost(`/api/iot/light/mode?value=${value}`)
}

export function setPumpInterval(value) {
  return apiPost(`/api/iot/pump/interval?value=${value}`)
}

export function setPumpDuration(value) {
  return apiPost(`/api/iot/pump/duration?value=${value}`)
}

export function setRestSchedule(schedule) {
  return apiPost('/api/iot/rest-schedule', schedule)
}
