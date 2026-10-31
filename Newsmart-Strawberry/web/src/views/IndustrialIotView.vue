<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { RefreshCw, Droplets, Fan, RotateCw, FlaskConical, Lightbulb, Power, Thermometer, Sprout, Gauge } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import SensorHistory from '@/components/SensorHistory.vue'
import DiseaseCareSuggestions from '@/components/DiseaseCareSuggestions.vue'
import { fetchIotDashboard, setActuator } from '@/apis/iot_api'

const dashboard = ref(null)
const error = ref('')
const loading = ref(false)
const pending = ref({})
const commands = ref({})
const requested = ref({})
const stoppingAll = ref(false)
let stopGeneration = 0
const busy = computed(() => stoppingAll.value || Object.values(pending.value).some(Boolean))
const control = computed(() => dashboard.value?.device_control || {})
const healthItems = computed(() => [
  { key: 'air', name: '空气传感器' },
  { key: 'soil', name: '土壤传感器' },
  { key: 'relay', name: '执行器通信' },
].map(item => ({ ...item, value: control.value.online ? control.value.reported_health?.[item.key] : null })))
const devices = [
  { key: 'fertigation', name: '水肥设备', relay: 1, icon: FlaskConical },
  { key: 'rotation', name: '旋转机构', relay: 2, icon: RotateCw },
  { key: 'irrigation', name: '滴灌水泵', relay: 3, icon: Droplets },
  { key: 'ventilation', name: '通风风扇', relay: 4, icon: Fan },
  { key: 'light', name: '补光灯', relay: 5, icon: Lightbulb },
]
const groups = computed(() => [
  { name: '空气环境', icon: Thermometer, data: dashboard.value?.air, fields: [
    ['temp', '温度', '°C'], ['humidity', '湿度', '%'], ['co2', 'CO₂', 'ppm'], ['illumination', '光照', 'lx'],
  ] },
  { name: '土壤环境', icon: Sprout, data: dashboard.value?.soil, fields: [
    ['soil_temperature', '温度', '°C'], ['soil_moisture', '水分', '%'], ['ph_value', 'pH', ''],
    ['soil_conductivity', '电导率原始值', ''], ['nitrogen', '氮原始值', ''],
    ['phosphorus', '磷原始值', ''], ['potassium', '钾原始值', ''],
  ] },
])
const deviceGroups = [
  { name: '执行器控制', icon: Power, devices: devices.slice(0, 4), light: false },
  { name: '灯光控制', icon: Lightbulb, devices: devices.slice(4), light: true },
]
function fresh(data) {
  return data?.timestamp && Date.now() - new Date(data.timestamp).getTime() < 35000
}
function formatTime(seconds) {
  return seconds ? new Date(seconds * 1000).toLocaleString() : '暂无上报'
}
let timer
let disposed = false
async function load() {
  if (loading.value) return
  loading.value = true
  try {
    const data = await fetchIotDashboard()
    if (!disposed) { dashboard.value = data; error.value = '' }
  } catch (e) {
    error.value = e.message || '设备数据读取失败'
    dashboard.value = null
  } finally { loading.value = false }
}
async function send(item, enabled) {
  if (stoppingAll.value) return
  if (pending.value[item.key]) return
  if (!control.value.broker_connected || control.value.protocol !== 'strawberry' || (enabled && !control.value.online)) {
    message.warning('设备连接已变化，请刷新状态后重试')
    return
  }
  pending.value[item.key] = true
  try {
    const result = await setActuator(item.key, enabled)
    if (result.status !== 'sent_unconfirmed') throw new Error('控制接口响应不匹配')
    requested.value[item.key] = enabled
    commands.value[item.key] = `${enabled ? '开启' : '停止'}指令已发送 · ${new Date().toLocaleTimeString()}`
    message.success(`${item.name}${enabled ? '开启' : '停止'}指令已发送`)
  } catch (e) {
    commands.value[item.key] = `${enabled ? '开启' : '停止'}指令发送失败`
    message.error(e.message || '指令发送失败')
  } finally { pending.value[item.key] = false }
}
async function stopAll() {
  if (busy.value || !control.value.broker_connected || control.value.protocol !== 'strawberry') return
  stoppingAll.value = true
  stopGeneration += 1
  try {
    const results = await Promise.allSettled(devices.map(async item => {
      pending.value[item.key] = true
      try {
        const result = await setActuator(item.key, false)
        if (result.status !== 'sent_unconfirmed') throw new Error('控制接口响应不匹配')
        requested.value[item.key] = false
        commands.value[item.key] = `停止指令已发送 · ${new Date().toLocaleTimeString()}`
      } catch (e) {
        commands.value[item.key] = '停止指令发送失败'
        throw e
      } finally { pending.value[item.key] = false }
    }))
    const failed = devices.filter((_, index) => results[index].status === 'rejected')
    if (failed.length) message.error(`以下设备关闭指令发送失败：${failed.map(item => item.name).join('、')}`)
    else message.success('五路设备关闭指令已全部发送，请核对现场设备')
  } finally { stoppingAll.value = false }
}
function start(item) {
  const generation = stopGeneration
  Modal.confirm({
    title: `开启${item.name}？`,
    content: `将向现场设备发送开启指令，请确认${item.name}周边安全，操作后留意设备运行情况。`,
    okText: '确认开启', cancelText: '取消',
    onOk: () => generation === stopGeneration ? send(item, true) : message.warning('已执行全部关闭，请重新操作开启'),
  })
}
onMounted(async () => {
  await load()
  if (!disposed) timer = setInterval(load, 5000)
})
onBeforeUnmount(() => { disposed = true; clearInterval(timer) })
</script>

<template>
  <div class="layout-container industrial-iot-view">
    <PageHeader title="草莓设备控制" :show-border="true">
      <template #actions>
        <a-tooltip title="刷新设备状态"><a-button class="lucide-icon-btn" :loading="loading" aria-label="刷新设备状态" @click="load"><RefreshCw :size="16" /></a-button></a-tooltip>
      </template>
    </PageHeader>
    <main class="iot-content">
      <a-alert v-if="error" type="error" :message="error" show-icon />
      <a-alert v-if="control.protocol && control.protocol !== 'strawberry'" type="warning" message="当前 MQTT 协议不是草莓五路协议，控制已禁用" show-icon />
      <section class="overview-band">
        <div>
          <p class="eyebrow">设备总览</p>
          <h2>草莓温室运行监测</h2>
          <p class="overview-time">最后上报：{{ formatTime(control.last_seen) }}</p>
        </div>
        <div class="mode-panel">
          <div class="mode-item"><div><span class="mode-title">MQTT 服务</span><span class="mode-desc">消息通道</span></div><a-tag :color="control.broker_connected ? 'green' : 'red'">{{ control.broker_connected ? '已连接' : '未连接' }}</a-tag></div>
          <div class="mode-item"><div><span class="mode-title">设备通信</span><span class="mode-desc">控制器连接</span></div><a-tag :color="control.online ? 'green' : undefined">{{ control.online ? '设备在线' : '设备离线' }}</a-tag></div>
        </div>
        <div class="device-health">
          <span v-for="item in healthItems" :key="item.key">{{ item.name }} <a-tag :color="item.value === '001' ? 'green' : item.value === '000' ? 'red' : undefined">{{ item.value === '001' ? '正常' : item.value === '000' ? '异常' : '待上报' }}</a-tag></span>
        </div>
      </section>
      <div class="metrics-grid">
        <section v-for="group in groups" :key="group.name" class="monitor-section">
          <div class="section-heading"><component :is="group.icon" :size="18" /><h3>{{ group.name }}</h3><a-tag class="section-status">{{ fresh(group.data) ? '近期数据' : group.data ? '数据已过期' : '暂无数据' }}</a-tag></div>
          <div class="metric-list" :class="{ 'hydroponic-list': group.name === '土壤环境' }">
            <article v-for="[key, label, unit] in group.fields" :key="key" class="metric-card">
              <Gauge class="metric-icon" :size="20" />
              <div class="metric-body"><span class="metric-label">{{ label }}</span><strong>{{ fresh(group.data) ? group.data[key] ?? '--' : '--' }} <small>{{ unit }}</small></strong></div>
            </article>
          </div>
        </section>
      </div>
      <div class="all-stop-toolbar">
        <a-button danger :loading="stoppingAll" :disabled="busy || !control.broker_connected || control.protocol !== 'strawberry'" @click="stopAll"><Power :size="16" />一键关闭所有设备</a-button>
      </div>
      <section v-for="group in deviceGroups" :key="group.name" :class="group.light ? 'light-section' : 'actuator-section'">
        <div class="section-heading"><component :is="group.icon" :size="18" /><h3>{{ group.name }}</h3></div>
        <div :class="group.light ? 'light-top-row' : 'actuator-grid'">
          <article v-for="item in group.devices" :key="item.key" :data-device="item.key" :class="[group.light ? 'light-switch-card' : 'actuator-row', 'relay-control']">
            <div class="actuator-info"><component :is="item.icon" :size="22" /><div><span class="actuator-title">{{ item.name }}</span></div></div>
            <div class="relay-actions">
              <a-tooltip :title="!control.broker_connected ? 'MQTT 服务未连接' : !control.online ? '设备离线，等待重新连接' : '下发控制指令，开关显示本页最近一次发送状态'">
                <a-switch checked-children="开" un-checked-children="关" :aria-label="`${item.name}开关`" :checked="!!requested[item.key]" :loading="!!pending[item.key]" :disabled="stoppingAll || !control.broker_connected || (!requested[item.key] && !control.online) || control.protocol !== 'strawberry' || !!pending[item.key]" @change="enabled => enabled ? start(item) : send(item, false)" />
              </a-tooltip>
            </div>
            <p v-if="commands[item.key]" class="command-status" role="status">{{ commands[item.key] }}</p>
          </article>
        </div>
      </section>
      <DiseaseCareSuggestions :control="control" />
      <SensorHistory />
    </main>
  </div>
</template>

<style scoped lang="less" src="./IndustrialIotView.less"></style>
