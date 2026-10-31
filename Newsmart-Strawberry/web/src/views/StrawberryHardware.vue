<template>
  <div class="industrial-iot-view layout-container">
    <PageHeader title="硬件控制" :show-border="true" :loading="loading">
      <template #actions><a-button title="刷新监测数据" :loading="loading" @click="load"><RefreshCw :size="16" /></a-button></template>
    </PageHeader>
    <main class="iot-content">
      <a-alert v-if="error" type="error" :message="error" show-icon />
      <section class="overview-band">
        <div><p class="eyebrow">草莓环境监测</p><h2>空气、土壤与执行器</h2></div>
        <div><span class="mode-title">{{ latest?.areaName || '未标记场地' }}</span><span class="mode-desc">最近记录：{{ latest?.createDate || '暂无记录' }}</span></div>
      </section>
      <div class="metrics-grid">
        <section v-for="group in groups" :key="group.title" class="monitor-section">
          <div class="section-heading"><component :is="group.icon" :size="18" /><h3>{{ group.title }}</h3></div>
          <div class="metric-list" :class="{ 'hydroponic-list': group.title === '土壤环境' }">
            <article v-for="metric in group.fields" :key="metric.key" class="metric-card">
              <component :is="metric.icon" :size="20" class="metric-icon" /><div class="metric-body"><span class="metric-label">{{ metric.label }}</span><strong>{{ latest?.[metric.key] ?? '--' }}</strong><span class="metric-range">{{ metric.unit }}</span></div>
            </article>
          </div>
        </section>
      </div>
      <section class="actuator-section">
        <div class="section-heading"><Cpu :size="18" /><h3>执行器控制台</h3><a-tag>cclr04</a-tag></div>
        <a-alert type="warning" message="设备运行状态未回传；指令发送成功不代表设备已执行。" show-icon />
        <div class="actuator-grid hardware-controls">
          <article v-for="item in actuators" :key="item.key" class="actuator-row">
            <div class="actuator-info"><component :is="item.icon" :size="20" /><div><span class="actuator-title">{{ item.name }}</span><span class="actuator-desc">{{ lastCommand[item.key] || '尚未发送指令' }}</span></div></div>
            <a-form layout="vertical" class="control-form">
              <a-form-item v-if="item.key === 'fan'" label="风速档位"><a-input-number v-model:value="speed" :min="1" :max="5" :precision="0" /></a-form-item>
              <template v-else><a-form-item label="滴灌时长（秒）"><a-input-number v-model:value="duration" :min="1" :max="3600" :precision="0" /></a-form-item><a-form-item label="滴灌强度（%）"><a-input-number v-model:value="intensity" :min="1" :max="100" :precision="0" /></a-form-item></template>
            </a-form>
            <a-space><a-button :disabled="!!pending" @click="confirmStart(item)"><Play :size="14" /> 启动</a-button><a-button danger :loading="pending === `${item.key}:stop`" :disabled="!!pending" @click="send(item, 'stop')"><Square :size="14" /> 停止</a-button></a-space>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { Cloud, Cpu, Droplets, RefreshCw, FlaskConical, Gauge, Sun, Thermometer, Fan, Play, Square, Sprout } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import { list } from '@/apis/strawberry_api'
import { controlHardware } from '@/apis/strawberry_hardware'

const latest = ref(null)
const loading = ref(false)
const error = ref('')
const pending = ref('')
const speed = ref(3)
const duration = ref(300)
const intensity = ref(80)
const lastCommand = ref({})
const actuators = [{ key: 'fan', name: '风扇', icon: Fan }, { key: 'irrigation', name: '滴灌', icon: Droplets }]
const groups = [
  { title: '空气环境', icon: Cloud, fields: [
    { key: 'airTemperature', label: '空气温度', unit: '°C', icon: Thermometer }, { key: 'airHumidity', label: '空气湿度', unit: '%', icon: Droplets },
    { key: 'lightLux', label: '光照强度', unit: 'lx', icon: Sun }, { key: 'airCo2', label: '二氧化碳', unit: 'ppm', icon: Gauge }
  ] },
  { title: '土壤环境', icon: Sprout, fields: [
    { key: 'soilTemperature', label: '土壤温度', unit: '°C', icon: Thermometer }, { key: 'soilHumidity', label: '土壤湿度', unit: '%', icon: Droplets },
    { key: 'soilPh', label: 'pH', unit: '', icon: FlaskConical }, { key: 'soilConductivity', label: '电导率', unit: 'μS/cm', icon: Gauge },
    { key: 'soilN', label: '氮', unit: 'mg/kg', icon: Sprout }, { key: 'soilP', label: '磷', unit: 'mg/kg', icon: Sprout }, { key: 'soilK', label: '钾', unit: 'mg/kg', icon: Sprout }
  ] }
]
async function load() {
  if (loading.value) return
  loading.value = true
  try {
    const result = await list('record', { pageNum: 1, pageSize: 1, orderByColumn: 'createDate', isAsc: 'desc' })
    latest.value = result.rows[0] || null
    error.value = ''
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
function confirmStart(item) {
  const valid = item.key === 'fan' ? Number.isInteger(speed.value) && speed.value >= 1 && speed.value <= 5
    : Number.isInteger(duration.value) && duration.value >= 1 && duration.value <= 3600 && Number.isInteger(intensity.value) && intensity.value >= 1 && intensity.value <= 100
  if (!valid) return message.error('请填写有效的控制参数')
  Modal.confirm({ title: `启动${item.name}？`, content: `目标设备：cclr04。${item.key === 'fan' ? `风速 ${speed.value} 档` : `时长 ${duration.value} 秒，强度 ${intensity.value}%`}。`, okText: '确认发送', cancelText: '取消', onOk: () => send(item, 'start') })
}
async function send(item, action) {
  if (pending.value) return
  pending.value = `${item.key}:${action}`
  try {
    const data = { action, ...(action === 'start' ? item.key === 'fan' ? { speed: speed.value } : { duration: duration.value, intensity: intensity.value } : {}) }
    await controlHardware(item.key, data)
    lastCommand.value[item.key] = `${new Date().toLocaleTimeString()} ${action === 'start' ? '启动' : '停止'}指令已发送，执行未确认`
    message.success('指令已发送，执行状态未确认')
  } catch (e) { message.error(e.message) } finally { pending.value = '' }
}
let timer
onMounted(() => { load(); timer = setInterval(load, 15000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style lang="less" scoped src="./IndustrialIotView.less"></style>
<style lang="less" scoped>
.hardware-controls { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 16px; }
.hardware-controls .actuator-row { flex-direction: column; align-items: stretch; }
.control-form { display: flex; flex-wrap: wrap; gap: 16px; }
.metric-body strong { overflow-wrap: anywhere; white-space: normal; }
@media (max-width: 700px) {
  .hardware-controls { grid-template-columns: 1fr; }
  .overview-band { grid-template-columns: 1fr; }
  :deep(.page-header) { flex-wrap: wrap; }
}
</style>
