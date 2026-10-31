<template>
  <div class="tomato-dashboard layout-container">
    <PageHeader title="番茄驾驶舱" :show-border="true">
      <template #info>
        <PageAgentDropdown default-agent="dashboard-analyzer" />
        <span class="live-pill">
          <Activity :size="14" />
          基地在线
        </span>
      </template>
    </PageHeader>

    <main class="dashboard-content">
      <section class="hero-panel">
        <img
          class="hero-image"
          src="/images/Tomato/tomato-greenhouse-hero.png"
          alt="番茄智能温室"
        />
        <div class="hero-overlay"></div>
        <div class="hero-copy">
          <p class="eyebrow">今日生产态势</p>
          <h2>番茄 A 区处于膨果期，环境状态稳定</h2>
          <p class="hero-desc">AI 已根据温室环境、水培营养液与农事任务生成今日调控建议。</p>
        </div>
        <div class="hero-metrics">
          <div v-for="item in heroMetrics" :key="item.label" class="hero-metric">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>

      <section class="operations-grid">
        <article class="zone-panel">
          <div class="section-title">
            <Map :size="18" />
            <h3>棚区态势</h3>
          </div>
          <div class="zone-visual">
            <img
              src="/images/Tomato/tomato-zone-overview.png"
              alt="番茄温室棚区总览"
            />
            <div class="zone-status">
              <span>A 区 稳定</span>
              <span>B 区 待巡检</span>
              <span>C 区 光照偏低</span>
            </div>
          </div>
        </article>

        <article class="ai-panel">
          <div class="section-title">
            <Bot :size="18" />
            <h3>AI 今日建议</h3>
          </div>
          <div class="ai-list">
            <div v-for="item in displaySuggestions" :key="item.title" class="ai-item">
              <span class="ai-level" :class="item.level">{{ item.levelText }}</span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section class="metric-strip">
        <article v-for="item in environmentMetrics" :key="item.label" class="metric-card">
          <component :is="item.icon" :size="20" />
          <div>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.range }}</p>
          </div>
        </article>
      </section>

      <section class="lower-grid">
        <article class="task-panel">
          <div class="section-title">
            <ClipboardList :size="18" />
            <h3>今日农事</h3>
          </div>
          <div class="task-list">
            <div v-for="task in tasks" :key="task.name" class="task-row">
              <span class="task-state" :class="task.state">{{ task.stateText }}</span>
              <div>
                <strong>{{ task.name }}</strong>
                <p>{{ task.zone }} · {{ task.time }}</p>
              </div>
            </div>
          </div>
        </article>

        <article class="growth-panel">
          <div class="section-title">
            <Leaf :size="18" />
            <h3>生长与采收</h3>
          </div>
          <img
            class="growth-image"
            src="/images/Tomato/tomato-growth-stages.png"
            alt="番茄生长阶段"
          />
          <div class="growth-stats">
            <div>
              <span>当前阶段</span>
              <strong>膨果期</strong>
            </div>
            <div>
              <span>预计采收</span>
              <strong>6 天后</strong>
            </div>
            <div>
              <span>预计产量</span>
              <strong>128 kg</strong>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Activity,
  Bot,
  ClipboardList,
  CloudSun,
  Droplets,
  Gauge,
  Leaf,
  Map,
  Sun,
  Thermometer
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageAgentDropdown from '@/components/PageAgentDropdown.vue'
import { fetchIotDashboard } from '@/apis/iot_api'

// ---- 来自 API 的传感器数据 ----
const airData = ref(null)
const soilData = ref(null)

const heroMetrics = computed(() => {
  const a = airData.value; const s = soilData.value
  let warnings = 0
  if (a) { if (a.temp > 28 || a.temp < 15) warnings++; if (a.humidity < 50 || a.humidity > 85) warnings++ }
  if (s) { if (s.ph_value < 5.5 || s.ph_value > 7) warnings++; if (s.soil_conductivity < 500 || s.soil_conductivity > 3000) warnings++ }
  return [
    { label: "在线棚区", value: "3" },
    { label: "今日预警", value: String(warnings) },
    { label: "AI 分析", value: String(aiSuggestions.value.length) + " 条" },
    { label: "传感器", value: a && s ? "在线" : "部分离线" }
  ]
})

// AI 建议 — 读取当前传感器数据，调用 AI 实时分析生成
const aiSuggestions = ref([])
const aiLoading = ref(false)

// AI 加载前显示占位
const displaySuggestions = computed(() => {
  if (aiSuggestions.value.length) return aiSuggestions.value
  if (aiLoading.value) return [{ title: 'AI 分析中...', desc: '正在根据当前传感器数据生成建议，请稍候。', level: 'normal', levelText: '加载中' }]
  return [{ title: '暂无 AI 建议', desc: '传感器数据加载完成后将自动生成分析建议。', level: 'normal', levelText: '等待' }]
})
async function loadAiSuggestions() {
  const a = airData.value; const s = soilData.value
  if (!a && !s) { aiSuggestions.value = []; return }
  aiLoading.value = true

  // 流式显示占位
  aiSuggestions.value = [{ title: '分析中...', desc: '正在读取传感器数据并生成建议', level: 'normal', levelText: '...' }]

  try {
    const { agentApi, threadApi } = await import('@/apis/agent_api')
    const { useAgentStore } = await import('@/stores/agent')
    const agentStore = useAgentStore()
    if (!agentStore.isInitialized) await agentStore.initialize()

    let env = '当前温室环境数据：\n'
    if (a) env += `空气：温度 ${a.temp}°C，湿度 ${a.humidity}%，光照 ${a.illumination}lx\n`
    if (s) env += `水培：pH ${s.ph_value}，EC ${s.soil_conductivity}μS/cm，水温 ${s.soil_temperature}°C，水箱水位 ${s.water_tank_level}cm\n`
    env += `\n番茄适宜：温度22-28°C，湿度60-75%，光照15000-25000lx，pH 5.8-6.5。`
    env += `\n卡片空间有限！给出3条建议，每条格式：【标题】描述。标题≤8字，描述≤50字。有异常标预警。`

    // 确保使用温室总管
    const master = agentStore.agents.find(a => a.slug === 'greenhouse-master' || a.id === 'greenhouse-master')
    const agentId = master?.id || agentStore.selectedAgentId
    if (!agentId) throw new Error('无可用智能体')

    // 创建临时线程和 run
    const tr = await threadApi.createThread(agentId, '仪表盘建议')
    const threadId = tr?.id || tr?.thread_id
    if (!threadId) throw new Error('创建线程失败')

    const runRes = await agentApi.createAgentRun({ query: env, agent_id: agentId, thread_id: threadId, meta: {} })
    const runId = runRes?.run_id
    if (!runId) throw new Error('创建运行失败')

    // SSE 流式读取
    const resp = await agentApi.streamAgentRunEvents(runId, '0-0')
    const reader = resp.body.getReader(); const dec = new TextDecoder()
    let buf = ''; let fullText = ''

    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buf += dec.decode(value, { stream: true }); const lines = buf.split('\n'); buf = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        try {
          const env = JSON.parse(line.slice(5).trim())
          if (!env?.payload) continue
          const items = env.payload.items || (env.payload.chunk ? [env.payload.chunk] : [])
          for (const item of items) {
            const t = (typeof item.content === 'string') ? item.content : (Array.isArray(item.content) ? item.content.map(c => typeof c === 'string' ? c : c?.text || '').join('') : '')
            if (t) { fullText += t; _parseStreamingSuggestions(fullText) }
          }
        } catch {}
      }
    }

    // 从历史拉取完整回复
    await new Promise(r => setTimeout(r, 1000))
    try {
      const hist = await agentApi.getAgentHistory(threadId)
      const all = hist?.history || hist?.messages || hist?.data || []
      for (let i = all.length - 1; i >= 0; i--) {
        if ((all[i].type === 'ai' || all[i].role === 'assistant') && all[i].content?.trim()) {
          fullText = all[i].content.trim(); break
        }
      }
    } catch {}

    _parseStreamingSuggestions(fullText)
  } catch (e) {
    console.error('生成 AI 建议失败:', e)
    aiSuggestions.value = [{ title: '分析失败', desc: e.message || '请稍后重试', level: 'normal', levelText: '错误' }]
  } finally {
    aiLoading.value = false
    // 如果解析后没有有效建议，保持最后状态
    if (!aiSuggestions.value.length || (aiSuggestions.value.length === 1 && aiSuggestions.value[0].title === '分析中...')) {
      if (!aiSuggestions.value.filter(s => s.title !== '分析中...').length) {
        aiSuggestions.value = [{ title: '暂无建议', desc: 'AI 分析未返回有效结果', level: 'normal', levelText: '等待' }]
      }
    }
  }
}

function _parseStreamingSuggestions(text) {
  if (!text?.trim()) return
  const items = []
  const lines = text.split('\n').filter(l => l.trim())
  for (const line of lines) {
    const cleaned = line.replace(/^[\d\.\-\*\s]+/, '').trim()
    if (!cleaned || cleaned.length < 5) continue
    let title = cleaned; let desc = ''
    const sep = cleaned.indexOf('：') >= 0 ? '：' : (cleaned.indexOf(':') >= 0 ? ':' : null)
    if (sep) { title = cleaned.slice(0, cleaned.indexOf(sep)).trim(); desc = cleaned.slice(cleaned.indexOf(sep) + 1).trim() }
    if (!desc) desc = title
    let level = 'normal'; let levelText = '正常'
    if (cleaned.includes('预警') || cleaned.includes('异常') || cleaned.includes('警告') || cleaned.includes('超标') || cleaned.includes('过低') || cleaned.includes('过高')) { level = 'warning'; levelText = '预警' }
    else if (cleaned.includes('关注') || cleaned.includes('注意') || cleaned.includes('风险') || cleaned.includes('偏低') || cleaned.includes('偏高')) { level = 'risk'; levelText = '关注' }
    items.push({ title: title.slice(0, 20), desc: desc.slice(0, 100), level, levelText })
    if (items.length >= 3) break
  }
  if (items.length) aiSuggestions.value = items
  else aiSuggestions.value = [{ title: '生成中...', desc: text.slice(0, 80), level: 'normal', levelText: '...' }]
}

// 环境指标 — 从真实传感器数据计算
const environmentMetrics = computed(() => {
  const a = airData.value
  const s = soilData.value
  return [
    { label: '温度', value: a ? `${a.temp} °C` : '--', range: '目标 22-28 °C', icon: Thermometer },
    { label: '湿度', value: a ? `${a.humidity}%` : '--', range: '目标 60-75%', icon: Droplets },
    { label: '光照', value: a ? `${a.illumination.toLocaleString()} lx` : '--', range: '目标 15,000-25,000 lx', icon: Sun },
    { label: 'pH', value: s ? `${s.ph_value}` : '--', range: '目标 5.8-6.5', icon: CloudSun },
    { label: 'EC', value: s ? `${s.soil_conductivity} μS/cm` : '--', range: '设备回传', icon: Gauge },
    { label: '水位', value: s ? `${s.water_tank_level} cm` : '--', range: '水箱液位', icon: Droplets }
  ]
})

// 农事任务 — 暂保留静态（未来可从任务系统接入）
const tasks = [
  { name: 'A 区营养液巡检', zone: 'A 区', time: '09:30', state: 'done', stateText: '已完成' },
  { name: 'B 区病害巡检', zone: 'B 区', time: '14:00', state: 'pending', stateText: '待处理' },
  { name: 'C 区补光策略确认', zone: 'C 区', time: '15:30', state: 'warning', stateText: '需确认' },
  { name: '采收前品质抽检', zone: 'A 区', time: '17:00', state: 'pending', stateText: '待处理' }
]

onMounted(async () => {
  try {
    const data = await fetchIotDashboard()
    if (data.air) airData.value = data.air
    if (data.soil) soilData.value = data.soil
  } catch {
    // 静默失败，保留 "--" 占位
  }
  loadAiSuggestions()
})
</script>

<style scoped lang="less">
.tomato-dashboard {
  min-height: 100%;
  background: var(--gray-25);
}

.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  background: var(--color-success-50);
  color: var(--color-success-700);
  font-size: 12px;
  font-weight: 600;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

.hero-panel {
  min-height: 300px;
  overflow: hidden;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-900);
}

.hero-image,
.hero-overlay {
  position: absolute;
  inset: 0;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-overlay {
  background:
    linear-gradient(90deg, rgba(1, 21, 31, 0.82) 0%, rgba(1, 21, 31, 0.5) 40%, rgba(1, 21, 31, 0.12) 100%),
    linear-gradient(0deg, rgba(1, 21, 31, 0.58) 0%, rgba(1, 21, 31, 0) 54%);
}

.hero-copy {
  position: relative;
  z-index: 1;
  max-width: 620px;
  padding: 34px;
  color: var(--gray-0);
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--color-success-100);
  font-size: 12px;
  font-weight: 700;
}

.hero-copy h2 {
  margin: 0;
  color: var(--gray-0);
  font-size: 30px;
  font-weight: 700;
  line-height: 1.28;
}

.hero-desc {
  max-width: 460px;
  margin: 12px 0 0;
  color: var(--light-85);
  font-size: 14px;
  line-height: 22px;
}

.hero-metrics {
  position: absolute;
  right: 24px;
  bottom: 24px;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(4, minmax(92px, 1fr));
  gap: 8px;
  max-width: 560px;
}

.hero-metric {
  min-height: 74px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  color: var(--gray-0);
}

.hero-metric span,
.metric-card span,
.growth-stats span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
}

.hero-metric span {
  color: var(--light-80);
}

.hero-metric strong {
  display: block;
  margin-top: 6px;
  color: var(--gray-0);
  font-size: 22px;
  font-weight: 700;
  line-height: 28px;
}

.operations-grid,
.lower-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.65fr);
  gap: 16px;
}

.zone-panel,
.ai-panel,
.task-panel,
.growth-panel,
.metric-card {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.zone-panel,
.ai-panel,
.task-panel,
.growth-panel {
  padding: 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: var(--main-color);
}

.section-title h3 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 16px;
  font-weight: 650;
  line-height: 22px;
}

.zone-visual {
  overflow: hidden;
  border-radius: 8px;
  background: var(--gray-10);
}

.zone-visual img,
.growth-image {
  display: block;
  width: 100%;
  object-fit: cover;
}

.zone-visual img {
  height: 300px;
}

.zone-status {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  border-top: 1px solid var(--gray-150);
  background: var(--gray-150);
}

.zone-status span {
  padding: 10px 12px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  font-weight: 600;
}

.ai-list,
.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-item,
.task-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.ai-item strong,
.task-row strong {
  display: block;
  color: var(--gray-1000);
  font-size: 14px;
  font-weight: 650;
  line-height: 20px;
}

.ai-item p,
.task-row p,
.metric-card p {
  margin: 3px 0 0;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
}

.ai-level,
.task-state {
  flex: 0 0 auto;
  min-width: 44px;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 650;
  line-height: 16px;
  text-align: center;
}

.ai-level.normal,
.task-state.done {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.ai-level.warning,
.task-state.warning {
  background: var(--color-warning-50);
  color: var(--color-warning-900);
}

.ai-level.risk,
.task-state.pending {
  background: var(--color-info-50);
  color: var(--color-info-700);
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-height: 106px;
  padding: 14px;
  color: var(--main-color);
}

.metric-card strong {
  display: block;
  margin-top: 7px;
  color: var(--gray-1000);
  font-size: 22px;
  font-weight: 700;
  line-height: 28px;
  white-space: nowrap;
}

.growth-image {
  height: 170px;
  border-radius: 8px;
}

.growth-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.growth-stats div {
  padding: 10px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.growth-stats strong {
  display: block;
  margin-top: 4px;
  color: var(--gray-1000);
  font-size: 16px;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .operations-grid,
  .lower-grid,
  .metric-strip {
    grid-template-columns: 1fr 1fr;
  }

  .hero-metrics {
    position: relative;
    right: auto;
    bottom: auto;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-width: none;
    padding: 0 24px 24px;
  }
}

@media (max-width: 760px) {
  .dashboard-content {
    padding: 12px;
  }

  .hero-copy {
    padding: 24px;
  }

  .hero-copy h2 {
    font-size: 24px;
  }

  .operations-grid,
  .lower-grid,
  .metric-strip,
  .zone-status,
  .growth-stats {
    grid-template-columns: 1fr;
  }
}
</style>
