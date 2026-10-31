<script setup>
import { onMounted, ref } from 'vue'
import { Download, Search } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { downloadSensorHistory, fetchSensorDevices, fetchSensorHistory } from '@/apis/iot_api'

const devices = ref([])
const device = ref()
const kind = ref()
const range = ref([])
const items = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const columns = [
  { title: '采样时间', key: 'time', width: 190 },
  { title: '来源设备', dataIndex: 'device_id', width: 180 },
  { title: '类型', key: 'kind', width: 85 },
  { title: '采集指标', key: 'values' },
]
const fields = {
  temp: ['温度', '°C'], humidity: ['湿度', '%'], co2: ['CO₂', 'ppm'], illumination: ['光照', 'lx'],
  soil_temperature: ['土壤温度', '°C'], soil_moisture: ['土壤水分', '%'],
  soil_conductivity: ['电导率原始值', ''], ph_value: ['pH', ''], water_tank_level: ['水位', 'cm'],
  nitrogen: ['氮原始值', ''], phosphorus: ['磷原始值', ''], potassium: ['钾原始值', ''],
}
function params() {
  const result = {}
  if (device.value) result.device_id = device.value
  if (kind.value) result.kind = kind.value
  if (range.value?.length === 2) {
    result.start = range.value[0].toISOString()
    result.end = range.value[1].toISOString()
  }
  return result
}
async function load(nextPage = 1) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await fetchSensorHistory({ ...params(), limit: 20, offset: (nextPage - 1) * 20 })
    items.value = result.items
    total.value = result.total
    page.value = nextPage
  } catch (e) {
    items.value = []
    total.value = 0
    error.value = e.message || '历史记录读取失败'
  } finally { loading.value = false }
}
async function download() {
  exporting.value = true
  try {
    const blob = await downloadSensorHistory(params())
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'sensor-history.csv'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) { message.error(e.message || '导出失败') }
  finally { exporting.value = false }
}
onMounted(async () => {
  try { devices.value = (await fetchSensorDevices()).devices }
  catch (e) { error.value = e.message || '设备列表读取失败'; return }
  await load()
})
</script>

<template>
  <section class="sensor-history">
    <h3>传感器历史日志</h3>
    <div class="history-filters">
      <a-select v-model:value="device" allow-clear placeholder="全部来源设备" aria-label="来源设备" :options="devices.map(value => ({ value, label: value }))" />
      <a-select v-model:value="kind" allow-clear placeholder="全部类型" aria-label="传感器类型" :options="[{value:'air',label:'空气'},{value:'soil',label:'土壤'}]" />
      <a-range-picker v-model:value="range" show-time aria-label="采样时间范围" />
      <a-tooltip title="查询历史记录"><a-button :loading="loading" aria-label="查询历史记录" @click="load(1)"><Search :size="16" /></a-button></a-tooltip>
      <a-button :loading="exporting" @click="download"><Download :size="16" />导出 CSV</a-button>
    </div>
    <a-alert v-if="error" :message="error" type="error" show-icon />
    <a-table :columns="columns" :data-source="items" :loading="loading" row-key="id" :pagination="false" :scroll="{x: 760}">
      <template #bodyCell="{column, record}">
        <template v-if="column.key === 'time'">{{ new Date(record.sampled_at).toLocaleString() }}</template>
        <template v-else-if="column.key === 'kind'">{{ record.kind === 'air' ? '空气' : '土壤' }}</template>
        <div v-else-if="column.key === 'values'" class="sample-values">
          <span v-for="(value, key) in record.values" :key="key">{{ fields[key]?.[0] || key }}：{{ value }} {{ fields[key]?.[1] }}</span>
        </div>
      </template>
    </a-table>
    <a-pagination :current="page" :total="total" :page-size="20" :show-size-changer="false" :disabled="loading" @change="load" />
  </section>
</template>

<style scoped lang="less">
.sensor-history { margin-top: 24px; min-width: 0; }
.history-filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
.history-filters :deep(.ant-select) { min-width: 155px; max-width: 100%; }
.history-filters :deep(.ant-picker) { max-width: 100%; }
.history-filters :deep(.ant-btn) { display: inline-flex; align-items: center; gap: 6px; }
.sample-values { display: flex; flex-wrap: wrap; gap: 6px 16px; }
.sensor-history :deep(.ant-pagination) { margin-top: 16px; }
</style>
