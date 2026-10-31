<template>
  <div class="harvest-dashboard">
    <div class="topbar">
      <div class="topbar-left">
        <button class="back-btn" type="button" @click="router.push('/tomato-maturity')">
          <ArrowLeft :size="16" />
          返回
        </button>
        <img class="logo-icon" src="/favicon.svg" alt="logo" />
        <span class="topbar-title">番茄成熟度检测与自动采摘</span>
        <span class="topbar-sub">实时识别成熟度，联动采摘设备执行作业</span>
      </div>
      <div class="topbar-right">
        <span class="meta-item">
          <Clock :size="14" />
          {{ currentTime }}
        </span>
        <div class="location-selector">
          <MapPin :size="13" />
          <a-select
            v-model:value="selectedZone"
            class="zone-select"
            size="small"
            :options="zoneOptions"
            :bordered="false"
          />
        </div>
        <span class="meta-item">
          <span class="status-dot"></span>
          设备在线 {{ onlineCount }}/{{ deviceTotal }}
        </span>
        <span class="tag tag-running">
          <Play :size="13" />
          系统运行中
        </span>
        <span class="tag tag-connected">
          <Monitor :size="13" />
          采摘机械臂已连接
        </span>
      </div>
    </div>

    <main class="main-grid">
      <!-- LEFT COLUMN -->
      <div class="left-col">
        <!-- 实时采摘画面 -->
        <div class="card video-card">
          <div class="card-header">
            <span class="card-title"><Monitor :size="16" /> 实时采摘画面</span>
            <button class="btn-text">全屏</button>
          </div>
          <div class="video-wrap">
            <img
              src="/image.png"
              alt="番茄成熟度检测与自动采摘"
              class="video-img"
            />
          </div>
          <!-- 统计条 -->
          <div class="stats-row">
            <div class="stat-item">
              <img class="stat-emoji" src="/favicon.svg" alt="统计" />
              <div><div class="stat-label">当前检测总数</div><div class="stat-value total">{{ scanStats.total }}</div></div>
            </div>
            <div class="stat-sep"></div>
            <div class="stat-item"><span class="stat-dot-sm ripe-dot"></span><div><div class="stat-label">成熟</div><div class="stat-value ripe">{{ scanStats.ripe }}</div></div></div>
            <div class="stat-sep"></div>
            <div class="stat-item"><span class="stat-dot-sm half-dot"></span><div><div class="stat-label">半熟</div><div class="stat-value half">{{ scanStats.half }}</div></div></div>
            <div class="stat-sep"></div>
            <div class="stat-item"><span class="stat-dot-sm unripe-dot"></span><div><div class="stat-label">未熟</div><div class="stat-value unripe">{{ scanStats.unripe }}</div></div></div>
            <div class="stat-rate">
              <div class="rate-label">成熟率</div>
              <div class="rate-value">{{ maturityRate }}%</div>
            </div>
          </div>
          <div class="threshold-bar" :class="{ met: scanStats.maturity >= harvestThreshold }">
            <CircleCheck v-if="scanStats.maturity >= harvestThreshold" :size="16" />
            <AlertTriangle v-else :size="16" />
            <template v-if="scanStats.maturity >= harvestThreshold">
              已满足采摘阈值（{{ harvestThreshold }}%），建议执行自动采摘
            </template>
            <template v-else>
              成熟度 {{ scanStats.maturity }}% 未达阈值（{{ harvestThreshold }}%），建议等待下次扫描
            </template>
          </div>
        </div>

        <!-- 任务记录 + 作业日志 并排 -->
        <div class="bottom-row">
          <div class="card bottom-card">
            <div class="card-header">
              <span class="card-title"><ClipboardList :size="14" /> 任务记录</span>
              <span class="more-link">更多 ›</span>
            </div>
            <table class="task-table">
              <thead>
                <tr><th>任务编号</th><th>区域</th><th>数量</th><th>方式</th><th>状态</th></tr>
              </thead>
              <tbody>
                <tr v-for="t in tasks" :key="t.id">
                  <td>{{ t.id }}</td><td>{{ t.zone }}</td><td>{{ t.count }}</td><td>{{ t.method }}</td>
                  <td><span class="badge" :class="t.status">{{ t.statusText }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="card bottom-card">
            <div class="card-header">
              <span class="card-title"><ScrollText :size="14" /> 作业日志</span>
              <span class="log-clear" @click="clearLogs">清空</span>
            </div>
            <div class="log-list">
              <div v-for="log in logs" :key="log.id" class="log-item">
                <span class="log-time">{{ log.time }}</span>
                <div class="log-dot" :style="{ background: log.color }"></div>
                <span class="log-text">{{ log.text }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT COLUMN -->
      <div class="right-col">
        <!-- 成熟度分析 -->
        <div class="card">
          <div class="card-header">
            <span class="card-title"><BarChart3 :size="15" /> 成熟度分析</span>
          </div>
          <div class="donut-section">
            <div class="donut-wrap">
              <svg viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="46" fill="none" stroke="#f0f0f0" stroke-width="14"/>
                <circle cx="60" cy="60" r="46" fill="none" stroke="#66bb6a" stroke-width="14"
                  :stroke-dasharray="unripeDashArray" stroke-dashoffset="0"/>
                <circle cx="60" cy="60" r="46" fill="none" stroke="#ff9800" stroke-width="14"
                  :stroke-dasharray="halfDashArray" :stroke-dashoffset="halfOffset"/>
                <circle cx="60" cy="60" r="46" fill="none" stroke="#e53935" stroke-width="14"
                  :stroke-dasharray="ripeDashArray" :stroke-dashoffset="ripeOffset"/>
              </svg>
              <div class="donut-center">
                <div class="donut-total-label">总计</div>
                <div class="donut-total-val">{{ scanStats.total }}</div>
              </div>
            </div>
            <div class="donut-legend">
              <div class="legend-item"><div class="legend-dot" style="background:#e53935"></div><span>成熟</span><span class="legend-count">{{ scanStats.ripe }}</span><span class="legend-pct">({{ ripePct }}%)</span></div>
              <div class="legend-item"><div class="legend-dot" style="background:#ff9800"></div><span>半熟</span><span class="legend-count">{{ scanStats.half }}</span><span class="legend-pct">({{ halfPct }}%)</span></div>
              <div class="legend-item"><div class="legend-dot" style="background:#66bb6a"></div><span>未熟</span><span class="legend-count">{{ scanStats.unripe }}</span><span class="legend-pct">({{ unripePct }}%)</span></div>
            </div>
          </div>
          <div class="kpi-grid">
            <div class="kpi-item"><div class="kpi-icon">📈</div><div><div class="kpi-label">平均成熟指数</div><div class="kpi-val">{{ (scanStats.maturity / 100).toFixed(2) }}</div></div></div>
            <div class="kpi-item"><div class="kpi-icon">⚖️</div><div><div class="kpi-label">预计可采摘重量</div><div class="kpi-val">{{ harvestYield.weight }}</div></div></div>
            <div class="kpi-item"><div class="kpi-icon">🏷️</div><div><div class="kpi-label">最佳采摘批次</div><div class="kpi-val">{{ harvestYield.batch }}</div></div></div>
            <div class="kpi-item"><div class="kpi-icon">🤖</div><div><div class="kpi-label">识别模型</div><div class="kpi-val kpi-sm">YOLO 成熟度</div></div></div>
          </div>
          <div class="threshold-bar threshold-sm threshold-config">
            <span>采摘阈值：</span>
            <input
              type="number"
              class="threshold-input"
              v-model.number="harvestThreshold"
              min="0" max="100"
              @change="persistThreshold"
            />
            <span>%</span>
            <span class="threshold-hint">（成熟度 ≥ {{ harvestThreshold }}% 才可采摘）</span>
          </div>
        </div>

        <!-- 采摘任务控制 -->
        <div class="card">
          <div class="card-header">
            <span class="card-title"><Activity :size="15" /> 采摘任务控制</span>
          </div>
          <div class="ctrl-btns">
            <button class="ctrl-btn ctrl-detect" @click="startDetect">
              <Play :size="14" /> 开始检测
            </button>
            <button class="ctrl-btn ctrl-auto" @click="dispatchHarvest">
              🤖 一键自动采摘
            </button>
            <button class="ctrl-btn ctrl-pause" @click="pauseTask">⏸ 暂停任务</button>
            <button class="ctrl-btn ctrl-manual" @click="switchManual">✋ 切换手动控制</button>
          </div>
          <div class="steps">
            <div v-for="(s, i) in steps" :key="s.label" class="step" :class="{ done: taskStep > i || taskPhase === 'completed', active: taskStep === i }">
              <div class="step-circle">{{ taskStep > i ? '✓' : i + 1 }}</div>
              <div class="step-name">{{ s.label }}</div>
            </div>
          </div>
        </div>

        <!-- 采摘设备状态 -->
        <div class="card">
          <div class="card-header">
            <span class="card-title"><Wrench :size="15" /> 采摘设备状态</span>
          </div>
          <div class="device-grid">
            <div v-for="d in devices" :key="d.name" class="device-item">
              <div class="device-icon-wrap">{{ d.icon }}</div>
              <div class="device-name">{{ d.name }}</div>
              <div class="device-status">{{ d.status }}</div>
              <div class="device-online">✦ 在线</div>
            </div>
          </div>
          <div class="position-bar">
            <span>机械臂当前位值：</span>
            <span class="position-coords">X 12.4 / Y 08.7 / Z 03.5</span>
            <span class="eta">
              <Clock :size="13" />
              预计完成时间：<span class="eta-val">{{ etaTime }}</span>
            </span>
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity, AlertTriangle, ArrowLeft, BarChart3, CircleCheck, ClipboardList, Clock, MapPin,
  Monitor, Play, ScrollText, Wrench
} from 'lucide-vue-next'
import { zoneConfig, scanRecords, harvestRecords as sharedRecords, getHarvestThreshold, setHarvestThreshold } from '@/data/tomatoData.js'

const route = useRoute()
const router = useRouter()

// 从路由参数读取初始区域，与成熟度管理中心联动
const initialZone = (route.query.zone && zoneConfig[route.query.zone]) ? route.query.zone : 'A'
const selectedZone = ref(initialZone)

const zoneOptions = Object.entries(zoneConfig).map(([k, v]) => ({ value: k, label: '1号温室-' + v.name }))

// 当前时间
const currentTime = ref('')
let timeTimer = null
const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

// 根据共享数据生成区域扫描统计
function buildZoneStats(zoneId) {
  const cfg = zoneConfig[zoneId]
  const scan = scanRecords.find(s => s.zone === zoneId && s.time.includes('今天'))
  if (!scan) return { total: 0, ripe: 0, half: 0, unripe: 0, maturity: 0 }
  const total = scan.count
  const ripe = Math.round(total * scan.maturity / 100)
  const rest = total - ripe
  const half = Math.round(rest * 0.55)
  const unripe = rest - half
  return { total, ripe, half, unripe: Math.max(0, unripe), maturity: scan.maturity }
}

const scanStats = reactive(buildZoneStats(selectedZone.value))
const maturityRate = computed(() => scanStats.total ? Math.round(scanStats.ripe / scanStats.total * 100) : 0)

// 可配置采摘阈值
const harvestThreshold = ref(getHarvestThreshold())
function persistThreshold() {
  const n = harvestThreshold.value
  if (n >= 0 && n <= 100) {
    setHarvestThreshold(n)
    addLog('采摘阈值已更新为 ' + n + '%', 'var(--color-info-500)')
  }
}

// 切换区域时更新数据
watch(selectedZone, (zoneId) => {
  const stats = buildZoneStats(zoneId)
  Object.assign(scanStats, stats)
  resetTask()
  addLog('切换到 ' + zoneConfig[zoneId].name + '，扫描数据已更新')
  // 同步路由参数
  router.replace({ query: { zone: zoneId } })
})

// 环形图数据
const CIRC = 2 * Math.PI * 46
const ripeDash = computed(() => scanStats.total ? Math.round(scanStats.ripe / scanStats.total * CIRC) : 0)
const halfDash = computed(() => scanStats.total ? Math.round(scanStats.half / scanStats.total * CIRC) : 0)
const unripeDash = computed(() => CIRC - ripeDash.value - halfDash.value)
const unripeDashArray = computed(() => unripeDash.value + ' 289')
const halfDashArray = computed(() => halfDash.value + ' 289')
const ripeDashArray = computed(() => ripeDash.value + ' 289')
const halfOffset = computed(() => -unripeDash.value)
const ripeOffset = computed(() => -(unripeDash.value + halfDash.value))
const ripePct = computed(() => scanStats.total ? Math.round(scanStats.ripe / scanStats.total * 100) : 0)
const halfPct = computed(() => scanStats.total ? Math.round(scanStats.half / scanStats.total * 100) : 0)
const unripePct = computed(() => scanStats.total ? Math.max(0, 100 - ripePct.value - halfPct.value) : 0)

// 设备 - 根据成熟度动态显示状态
const devices = computed(() => {
  const m = scanStats.maturity
  return [
    { name: '机械臂', icon: '🦾', status: m >= 80 ? '就绪' : '待命' },
    { name: '夹爪', icon: '🔧', status: m >= 80 ? '就绪' : '待命' },
    { name: '传送装置', icon: '📦', status: '正常' },
    { name: '视觉相机', icon: '📷', status: '正常' },
    { name: '环境传感器', icon: '🌡️', status: '正常' },
    { name: '控制系统', icon: '🖥️', status: '正常' }
  ]
})
const deviceTotal = computed(() => devices.value.length)
const onlineCount = ref(6)

// 采摘任务统计 - 按区域汇总
const harvestYield = computed(() => {
  const zoneName = zoneConfig[selectedZone.value]?.name
  const records = sharedRecords.filter(r => r.zone === zoneName)
  if (!records.length) return { weight: '--', batch: '--' }
  const totalKg = records.reduce((s, r) => s + parseFloat(r.yield), 0)
  return { weight: totalKg.toFixed(1) + ' kg', batch: records[0].rows.split('/')[0] }
})

// 任务记录
const tasks = ref([
  { id: 'TASK-2026-061', zoneId: 'A', zone: '1号温室-A区', count: 12, method: '自动采摘', status: 'running', statusText: '● 执行中', time: '--' },
  { id: 'TASK-2026-060', zoneId: 'B', zone: '1号温室-B区', count: 9, method: '自动采摘', status: 'done', statusText: '● 已完成', time: '2026-06-24 08:57' },
  { id: 'TASK-2026-059', zoneId: 'A', zone: '1号温室-A区', count: 11, method: '自动采摘', status: 'done', statusText: '● 已完成', time: '2026-06-24 08:15' },
  { id: 'TASK-2026-058', zoneId: 'C', zone: '1号温室-C区', count: 8, method: '手动采摘', status: 'done', statusText: '● 已完成', time: '2026-06-24 07:42' },
  { id: 'TASK-2026-057', zoneId: 'B', zone: '1号温室-B区', count: 10, method: '自动采摘', status: 'done', statusText: '● 已完成', time: '2026-06-24 07:05' }
])

// 任务步骤
const steps = [
  { label: '图像采集' }, { label: '成熟判断' }, { label: '任务生成' },
  { label: '机械臂定位' }, { label: '执行采摘' }, { label: '结果回传' }
]
const taskPhase = ref('idle')
const taskStep = ref(-1)
const etaTime = ref('--:--')
let progressTimer = null

// 作业日志
const logs = ref([])
function initLogs() {
  const zn = zoneConfig[selectedZone.value]?.name || ''
  logs.value = [
    { id: 5, time: '09:20', color: 'var(--color-success-500)', text: zn + ' 开始图像采集，系统运行正常' },
    { id: 4, time: '09:21', color: 'var(--color-success-500)', text: '检测到成熟果 ' + scanStats.ripe + ' 个，成熟率 ' + maturityRate.value + '%' },
    { id: 3, time: '09:22', color: 'var(--color-success-500)', text: '已生成采摘路径，预计采摘 ' + scanStats.ripe + ' 个成熟果' },
    { id: 2, time: '09:23', color: 'var(--color-success-500)', text: '机械臂待命，等待采摘指令' },
    { id: 1, time: '09:24', color: 'var(--color-warning-500)', text: '系统就绪，成熟度 ' + scanStats.maturity + '%，' + (scanStats.maturity >= 80 ? '满足采摘阈值' : '未达采摘阈值') }
  ]
}
initLogs()

function addLog(text, color = 'var(--color-success-500)') {
  const now = new Date()
  const time = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0')
  logs.value.unshift({ id: Date.now(), time, color, text })
}

function startDetect() {
  addLog('手动触发图像采集检测')
  // 模拟检测结果微调
  scanStats.ripe = Math.max(0, scanStats.ripe + Math.round((Math.random() - 0.5) * 4))
  scanStats.half = Math.max(0, scanStats.half + Math.round((Math.random() - 0.5) * 3))
}

function dispatchHarvest() {
  if (taskPhase.value !== 'idle') return
  taskPhase.value = 'running'
  addLog('一键自动采摘已触发，任务开始执行', 'var(--color-success-500)')
  taskStep.value = 0
  const durations = [2000, 1500, 1500, 2000, 5000, 2000]
  let acc = 0
  durations.forEach((d, i) => {
    acc += d
    setTimeout(() => {
      if (taskPhase.value !== 'running') return
      taskStep.value = i + 1
      const doneColor = i === 5 ? 'var(--color-warning-500)' : 'var(--color-success-500)'
      addLog(steps[i].label + (i < steps.length - 1 ? ' 完成' : ' 完成，采摘任务结束'), doneColor)
      if (i === 5) {
        taskPhase.value = 'completed'
        const dn = new Date()
        const t = String(dn.getHours()).padStart(2, '0') + ':' + String(dn.getMinutes()).padStart(2, '0')
        const zn = zoneConfig[selectedZone.value]?.name || ''
        tasks.value.unshift({
          id: 'TASK-2026-' + String(tasks.value.length + 1).padStart(3, '0'),
          zoneId: selectedZone.value,
          zone: '1号温室-' + zn,
          count: scanStats.ripe,
          method: '自动采摘',
          status: 'done',
          statusText: '● 已完成',
          time: dn.toISOString().slice(0, 10) + ' ' + t
        })
        etaTime.value = '--:--'
        // 采摘完成后更新统计
        scanStats.ripe = 0
        scanStats.total = scanStats.half + scanStats.unripe
      }
    }, acc)
  })
  let sec = Math.ceil(acc / 1000)
  const updateEta = () => {
    if (taskPhase.value !== 'running') return
    const m = Math.floor(sec / 60), s = sec % 60
    etaTime.value = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0')
    if (sec > 0) { sec--; setTimeout(updateEta, 1000) }
  }
  updateEta()
}

function resetTask() {
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null }
  taskPhase.value = 'idle'
  taskStep.value = -1
  etaTime.value = '--:--'
}

function pauseTask() {
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null }
  addLog('任务已暂停', 'var(--color-warning-500)')
}

function switchManual() {
  addLog('切换为手动控制模式')
}

function clearLogs() {
  logs.value = []
}

onMounted(() => {
  updateTime()
  timeTimer = setInterval(updateTime, 30000)
})

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<style scoped lang="less">
.harvest-dashboard {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--gray-25);
  color: var(--gray-1000);
  overflow: hidden;
}

// ── TOPBAR ──
.topbar {
  background: var(--gray-0);
  border-bottom: 1px solid var(--gray-150);
  height: 52px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-600);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.2s, color 0.2s;

  &:hover { border-color: var(--main-color); color: var(--main-color); }
}

.logo-icon { width: 24px; height: 24px; flex-shrink: 0; }

.topbar-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--main-color);
  white-space: nowrap;
}

.topbar-sub {
  font-size: 11px;
  color: var(--gray-500);
  white-space: nowrap;
  margin-left: 4px;
}

.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--gray-600);
  white-space: nowrap;
}

.location-selector {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  padding: 2px 6px;
  color: var(--gray-600);
}

.zone-select {
  min-width: 120px;
  :deep(.ant-select-selector) { border: none !important; padding: 0 !important; font-size: 12px; }
}

.status-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--color-success-500);
  display: inline-block; flex-shrink: 0;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
}

.tag-running {
  background: var(--color-success-50);
  color: var(--color-success-700);
  border: 1px solid var(--color-success-100);
}

.tag-connected {
  background: var(--main-color);
  color: var(--gray-0);
  border: none;
}

// ── MAIN LAYOUT ──
.main-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 12px;
  padding: 12px;
  min-height: 0;
  overflow: hidden;
}

.left-col, .right-col {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  min-height: 0;
}

.left-col { overflow: hidden; }
.right-col { overflow-y: auto; }

// ── CARDS ──
.card {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 12px;
  flex-shrink: 0;
}

.card.video-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-1000);
  display: flex;
  align-items: center;
  gap: 5px;

  :deep(svg) { color: var(--main-color); }
}

.btn-text {
  background: var(--gray-25);
  border: 1px solid var(--gray-150);
  border-radius: 5px;
  padding: 3px 10px;
  font-size: 12px;
  color: var(--gray-600);
  cursor: pointer;
}

.more-link {
  font-size: 12px;
  color: var(--main-color);
  cursor: pointer;
}

// ── VIDEO ──
.video-wrap {
  border-radius: 8px;
  overflow: hidden;
  flex: 1;
  min-height: 260px;
  margin-bottom: 10px;
}

.video-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

// ── BOTTOM ROW (任务 + 日志) ──
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.bottom-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

// ── STATS ──
.stats-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 7px;
}

.stat-emoji { width: 20px; height: 20px; }

.stat-dot-sm {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
  &.ripe-dot { background: var(--color-error-500); }
  &.half-dot { background: var(--color-warning-500); }
  &.unripe-dot { background: var(--color-success-500); }
}

.stat-label { font-size: 11px; color: var(--gray-500); }
.stat-value { font-size: 18px; font-weight: 700; }
.stat-value.total { color: var(--gray-1000); }
.stat-value.ripe { color: var(--color-error-500); }
.stat-value.half { color: var(--color-warning-500); }
.stat-value.unripe { color: var(--color-success-500); }

.stat-sep {
  width: 1px; height: 36px; background: var(--gray-150);
}

.stat-rate {
  margin-left: auto; text-align: right;
  .rate-label { font-size: 11px; color: var(--gray-500); }
  .rate-value { font-size: 24px; font-weight: 800; color: var(--main-color); }
}

.threshold-bar {
  background: var(--color-success-50);
  border: 1px solid var(--color-success-100);
  border-radius: 7px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--color-success-700);

  :deep(svg) { flex-shrink: 0; }
}

.threshold-sm { font-size: 11px; margin-top: 10px; }

.threshold-bar {
  &.met { /* 无额外样式，默认绿色 */ }
  &:not(.met) {
    background: var(--color-warning-50);
    border-color: var(--color-warning-100);
    color: var(--color-warning-700);
  }
}

.threshold-config {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-600);
}

.threshold-input {
  width: 44px;
  height: 22px;
  padding: 0 4px;
  border: 1px solid var(--gray-200);
  border-radius: 4px;
  background: var(--gray-0);
  color: var(--gray-1000);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  outline: none;

  &:focus { border-color: var(--main-color); }
}

.threshold-hint {
  font-size: 10px;
  color: var(--gray-500);
}

// ── TASK TABLE ──
.task-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;

  th {
    text-align: left;
    color: var(--gray-500);
    font-weight: 500;
    font-size: 10px;
    padding: 4px 5px;
    border-bottom: 1px solid var(--gray-150);
  }

  td {
    padding: 5px 5px;
    border-bottom: 1px solid var(--gray-100);
  }
}

.badge {
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;

  &.running { background: var(--color-warning-50); color: var(--color-warning-700); }
  &.done { background: var(--color-success-50); color: var(--color-success-700); }
}

// ── DONUT ──
.donut-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.donut-wrap {
  position: relative;
  width: 130px; height: 130px;
  flex-shrink: 0;

  svg {
    width: 130px; height: 130px;
    transform: rotate(-90deg);
  }
}

.donut-center {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.donut-total-label { font-size: 10px; color: var(--gray-500); }
.donut-total-val { font-size: 20px; font-weight: 800; color: var(--gray-1000); }

.donut-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
}

.legend-dot {
  width: 9px; height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-count { font-weight: 700; margin-left: auto; }
.legend-pct { color: var(--gray-500); }

// ── KPI ──
.kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
}

.kpi-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kpi-icon {
  width: 36px; height: 36px;
  border-radius: 8px;
  background: var(--main-50);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.kpi-label { font-size: 11px; color: var(--gray-500); }
.kpi-val { font-size: 18px; font-weight: 700; color: var(--gray-1000); }
.kpi-sm { font-size: 13px !important; }

// ── CTRL BUTTONS ──
.ctrl-btns {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.ctrl-btn {
  padding: 10px 12px;
  border-radius: 7px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: 1px solid var(--gray-150);
  background: var(--gray-0);
  color: var(--gray-600);
  transition: border-color 0.2s, color 0.2s;

  &:hover { border-color: var(--main-color); color: var(--main-color); }
}

.ctrl-detect { flex: 1; }
.ctrl-auto {
  flex: 2;
  background: var(--main-color);
  border: none;
  color: var(--gray-0);
  font-weight: 600;
  font-size: 13px;

  &:hover { opacity: 0.9; color: var(--gray-0); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.ctrl-pause, .ctrl-manual { flex: 1; }

// ── STEPS ──
.steps {
  display: flex;
  align-items: flex-start;
  gap: 0;
}

.step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  position: relative;

  &:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 12px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: var(--gray-150);
    z-index: 0;
  }

  &.done::after, &.active::after {
    background: var(--main-color);
  }
}

.step-circle {
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--gray-150);
  color: var(--gray-500);
  font-size: 10px; font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  position: relative;
}

.step.done .step-circle { background: var(--main-color); color: var(--gray-0); }
.step.active .step-circle { background: var(--main-color); color: var(--gray-0); border: 2px solid var(--main-200); }

.step-name {
  font-size: 9px; color: var(--gray-500); text-align: center; line-height: 1.2;
}

.step.done .step-name, .step.active .step-name { color: var(--main-color); }

// ── DEVICES ──
.device-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 8px;
}

.device-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 11px;
}

.device-icon-wrap {
  width: 42px; height: 42px;
  background: var(--main-50);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.device-name { color: var(--gray-600); font-size: 12px; }
.device-status { color: var(--color-success-700); font-weight: 600; font-size: 11px; }
.device-online { color: var(--gray-500); font-size: 10px; }

.position-bar {
  background: var(--main-50);
  border-radius: 7px;
  padding: 7px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gray-600);
}

.position-coords { color: var(--gray-1000); font-weight: 600; }

.eta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--gray-600);
}

.eta-val { color: var(--main-color); font-weight: 700; font-size: 14px; }

// ── LOG ──
.log-clear {
  font-size: 11px; color: var(--gray-500); cursor: pointer;
}

.log-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  overflow-y: auto;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 11px;
}

.log-time { color: var(--gray-500); flex-shrink: 0; width: 30px; }

.log-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 3px;
}

.log-text { color: var(--gray-600); line-height: 1.4; }

@media (max-width: 1080px) {
  .main-grid { grid-template-columns: 1fr; max-width: 760px; }
  .topbar-sub { display: none; }
}

@media (max-width: 700px) {
  .topbar { flex-wrap: wrap; height: auto; padding: 10px 12px; }
  .topbar-right { flex-wrap: wrap; }
  .stats-row { flex-wrap: wrap; }
  .donut-section { flex-direction: column; }
}
</style>
