<template>
  <div class="ai-log-view layout-container">
    <PageHeader title="AI 日志" :show-border="true">
      <template #info>
        <span class="status-pill">
          <FileClock :size="14" />
          {{ currentReport.label }} {{ currentReport.logs.length }} 条
        </span>
      </template>
    </PageHeader>

    <main class="log-content">
      <div class="report-layout">
        <div class="report-main">
          <section class="log-overview">
            <img src="/images/Tomato/tomato-ai-advisor.png" alt="AI 番茄专家" />
            <div>
              <p>智能决策留痕</p>
              <h2>记录识别、预警、调控与采摘建议全过程</h2>
              <span>用于复盘 AI 建议、追踪循迹小车扫描结果，并辅助后续教学和生产决策。</span>
            </div>
          </section>

          <section class="log-grid">
            <article v-for="item in currentReport.stats" :key="item.label" class="stat-card">
              <component :is="item.icon" :size="20" />
              <div>
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.note }}</p>
              </div>
            </article>
          </section>

          <section class="log-panel">
            <div class="section-title">
              <FileClock :size="18" />
              <h3>日志记录</h3>
            </div>
            <div class="log-list">
              <article v-for="log in currentReport.logs" :key="log.id" class="log-row">
                <div class="log-time">
                  <strong>{{ log.time }}</strong>
                  <span>{{ log.source }}</span>
                </div>
                <span class="log-type" :class="log.type">{{ log.typeText }}</span>
                <div class="log-body">
                  <strong>{{ log.title }}</strong>
                  <p>{{ log.detail }}</p>
                </div>
                <span class="log-result" :class="log.result">{{ log.resultText }}</span>
              </article>
            </div>
          </section>
        </div>

        <aside class="calendar-panel">
          <div class="calendar-head">
            <div>
              <span>历史日报</span>
              <strong>2026 年 6 月</strong>
            </div>
            <CalendarDays :size="20" />
          </div>
          <div class="weekday-row">
            <span v-for="day in weekdays" :key="day">{{ day }}</span>
          </div>
          <div class="calendar-grid">
            <button
              v-for="day in calendarDays"
              :key="day.key"
              type="button"
              class="calendar-day"
              :class="{
                muted: !day.date,
                active: day.date === selectedDate,
                available: Boolean(day.date && reports[day.date])
              }"
              :disabled="!day.date || !reports[day.date]"
              @click="selectedDate = day.date"
            >
              <span>{{ day.label }}</span>
              <em v-if="day.date && reports[day.date]">{{ reports[day.date].logs.length }}</em>
            </button>
          </div>
          <div class="calendar-summary">
            <span>{{ currentReport.label }}</span>
            <strong>{{ currentReport.title }}</strong>
            <p>{{ currentReport.summary }}</p>
          </div>
        </aside>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import {
  Bot,
  CalendarDays,
  ClipboardCheck,
  FileClock,
  ScanLine,
  TriangleAlert,
  Wrench,
  BarChart3,
  Globe,
  Database
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import { agentApi } from '@/apis/agent_api'

const selectedDate = ref('')
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const reports = ref({})
const loading = ref(false)
let _refreshTimer = null

const TOOL_LABELS = {
  get_iot_dashboard: '仪表盘数据', get_air_sensors: '空气传感器', get_soil_sensors: '土壤传感器',
  get_actuators: '执行器状态', task: '子智能体', tavily_search: '联网搜索',
  query_kb: '知识库检索', list_kbs: '知识库列表'
}
const TOOL_ICONS = { task: Bot, get_iot_dashboard: BarChart3, get_air_sensors: ScanLine, get_soil_sensors: Database, get_actuators: Wrench, tavily_search: Globe, query_kb: Database }

function toolLabel(n) { return TOOL_LABELS[n] || n }
function toolIcon(n) { return TOOL_ICONS[n] || Wrench }

// 格式化日期
function fmtDate(d) {
  const dt = new Date(d); const y = dt.getFullYear(); const m = String(dt.getMonth() + 1).padStart(2, '0'); const day = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function fmtTime(d) { const dt = new Date(d); return String(dt.getHours()).padStart(2, '0') + ':' + String(dt.getMinutes()).padStart(2, '0') }

// 从对话历史构建 AI 日志
async function loadAiLogs() {
  loading.value = true
  try {
    const { threadApi } = await import('@/apis/agent_api')
    // 获取所有智能体的对话线程
    const agents = ['greenhouse-master', 'default-chatbot', 'deep-research']
    const allThreads = []
    for (const aid of agents) {
      try {
        const r = await threadApi.getThreads(aid, 30, 0)
        const threads = Array.isArray(r) ? r : (r?.threads || r?.data || [])
        allThreads.push(...threads)
      } catch {}
    }

    // 按日期分组
    const grouped = {}
    for (const t of allThreads) {
      if (!t.id) continue
      try {
        const h = await agentApi.getAgentHistory(t.id)
        const msgs = h?.history || h?.messages || h?.data || []
        if (!msgs.length) continue

        const date = fmtDate(t.created_at || t.updated_at)
        if (!grouped[date]) grouped[date] = { logs: [], toolCount: 0, adviceCount: 0, warningCount: 0, executedCount: 0 }

        // 提取用户问题
        const userMsgs = msgs.filter(m => m.type === 'human' || m.role === 'user')
        const aiMsgs = msgs.filter(m => m.type === 'ai' || m.role === 'assistant')

        for (const um of userMsgs) {
          if (!um.content?.trim()) continue
          const log = {
            id: 'L-' + (um.id || Date.now()),
            time: fmtTime(um.created_at),
            source: t.agent_id === 'greenhouse-master' ? '温室总管' : (t.agent_id === 'default-chatbot' ? '智能助手' : '深度研究'),
            type: 'advice',
            typeText: '提问',
            title: um.content.slice(0, 60) + (um.content.length > 60 ? '...' : ''),
            detail: '',
            result: 'ready',
            resultText: '已回复'
          }

          // 找对应的 AI 回复
          const umIdx = msgs.indexOf(um)
          for (let j = umIdx + 1; j < msgs.length; j++) {
            if (msgs[j].type === 'ai' || msgs[j].role === 'assistant') {
              let content = msgs[j].content?.trim()
              if (!content && msgs[j].extra_metadata?.content) {
                const texts = msgs[j].extra_metadata.content.filter(c => c.type === 'text' && c.text).map(c => c.text)
                content = texts.join(' ')
              }
              if (content) {
                log.detail = content.slice(0, 120) + (content.length > 120 ? '...' : '')
                log.typeText = '建议'
                grouped[date].adviceCount++
                break
              }
            }
            // 收集工具调用
            const tcList = msgs[j].tool_calls || msgs[j].extra_metadata?.tool_calls || []
            for (const tc of tcList) {
              const name = tc.name || tc.function?.name || ''
              if (name) {
                grouped[date].toolCount++
                if (name.includes('warning') || name.includes('alert')) grouped[date].warningCount++
                if (name === 'task') grouped[date].executedCount++
              }
            }
          }

          grouped[date].logs.push(log)
        }
      } catch { /* skip individual thread errors */ }
    }

    // 按日期排序，每个日期内按时间倒序
    const sorted = {}
    for (const [date, data] of Object.entries(grouped)) {
      data.logs.sort((a, b) => b.time.localeCompare(a.time))
      sorted[date] = {
        label: date === fmtDate(new Date()) ? '今日' : (date === fmtDate(new Date(Date.now() - 86400000)) ? '昨天' : date),
        title: `${data.logs.length} 条 AI 交互记录`,
        summary: `AI 共回复 ${data.adviceCount} 次建议，调用 ${data.toolCount} 次工具，委派 ${data.executedCount} 次子智能体。`,
        stats: [
          { label: '对话轮次', value: String(data.logs.length), note: '用户提问与 AI 回复', icon: Bot },
          { label: 'AI 建议', value: String(data.adviceCount), note: '分析、建议与决策', icon: ClipboardCheck },
          { label: '工具调用', value: String(data.toolCount), note: '传感器、知识库、子智能体', icon: Wrench },
          { label: '子智能体', value: String(data.executedCount), note: '委派专业子智能体执行', icon: Bot }
        ],
        logs: data.logs.slice(0, 30)
      }
    }
    reports.value = sorted

    // 默认选中最新日期
    const dates = Object.keys(sorted).sort().reverse()
    if (dates.length) selectedDate.value = dates[0]
  } catch (e) {
    console.error('加载 AI 日志失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAiLogs()
  _refreshTimer = setInterval(loadAiLogs, 60000) // 每分钟刷新
})
onBeforeUnmount(() => { if (_refreshTimer) clearInterval(_refreshTimer) })

const currentReport = computed(() => {
  const dates = Object.keys(reports.value).sort().reverse()
  const key = selectedDate.value && reports.value[selectedDate.value] ? selectedDate.value : dates[0]
  return reports.value[key] || { label: '加载中...', title: '', summary: '', stats: [], logs: [] }
})

const calendarDays = computed(() => {
  const days = []
  const now = new Date()
  const year = now.getFullYear(); const month = now.getMonth()
  const firstDay = new Date(year, month, 1).getDay() || 7
  for (let i = 1; i < firstDay; i++) days.push({ key: `blank-${i}`, label: '', date: '' })
  const lastDay = new Date(year, month + 1, 0).getDate()
  for (let d = 1; d <= lastDay; d++) {
    const date = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({ key: date, label: String(d), date })
  }
  return days
})

</script>

<style scoped lang="less">
.ai-log-view {
  min-height: 100%;
  background: var(--gray-25);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  background: var(--color-info-50);
  color: var(--color-info-700);
  font-size: 12px;
  font-weight: 600;
}

.log-content {
  padding: var(--page-padding);
}

.report-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
}

.report-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.log-overview,
.stat-card,
.log-panel,
.calendar-panel {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.log-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 520px);
  overflow: hidden;
}

.log-overview img {
  width: 100%;
  height: 250px;
  object-fit: cover;
}

.log-overview div {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 26px;
}

.log-overview p {
  margin: 0 0 8px;
  color: var(--main-color);
  font-size: 12px;
  font-weight: 700;
}

.log-overview h2 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.35;
}

.log-overview span {
  margin-top: 10px;
  color: var(--gray-600);
  font-size: 14px;
  line-height: 22px;
}

.log-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.stat-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 106px;
  padding: 14px;
  color: var(--main-color);
}

.stat-card span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
}

.stat-card strong {
  display: block;
  margin-top: 6px;
  color: var(--gray-1000);
  font-size: 24px;
  font-weight: 700;
}

.stat-card p,
.log-body p,
.calendar-summary p {
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
}

.log-panel {
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
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.log-row {
  display: grid;
  grid-template-columns: 90px 58px minmax(0, 1fr) 72px;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.log-time strong,
.log-body strong {
  display: block;
  color: var(--gray-1000);
  font-size: 14px;
  font-weight: 650;
}

.log-time span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
}

.log-type,
.log-result {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 650;
}

.log-type.scan,
.log-result.watch {
  background: var(--color-info-50);
  color: var(--color-info-700);
}

.log-type.advice,
.log-result.ready {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.log-type.warning,
.log-result.pending {
  background: var(--color-warning-50);
  color: var(--color-warning-900);
}

.calendar-panel {
  align-self: start;
  padding: 16px;
  position: sticky;
  top: 74px;
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--main-color);
}

.calendar-head span,
.calendar-summary span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
}

.calendar-head strong,
.calendar-summary strong {
  display: block;
  margin-top: 3px;
  color: var(--gray-1000);
  font-size: 16px;
  font-weight: 700;
}

.weekday-row,
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
}

.weekday-row {
  margin-top: 16px;
}

.weekday-row span {
  color: var(--gray-500);
  font-size: 12px;
  text-align: center;
}

.calendar-grid {
  margin-top: 8px;
}

.calendar-day {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 1;
  border: 1px solid transparent;
  border-radius: 8px;
  background: var(--gray-10);
  color: var(--gray-600);
  cursor: pointer;
}

.calendar-day:disabled {
  cursor: default;
}

.calendar-day.available {
  border-color: var(--main-50);
  color: var(--main-color);
  font-weight: 650;
}

.calendar-day.active {
  background: var(--main-color);
  color: var(--gray-0);
}

.calendar-day.muted {
  background: transparent;
}

.calendar-day em {
  position: absolute;
  right: 4px;
  bottom: 2px;
  color: inherit;
  font-size: 10px;
  font-style: normal;
  line-height: 1;
}

.calendar-summary {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: var(--gray-10);
}

@media (max-width: 1180px) {
  .report-layout {
    grid-template-columns: 1fr;
  }

  .calendar-panel {
    position: static;
  }

  .log-overview,
  .log-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .log-overview,
  .log-grid,
  .log-row {
    grid-template-columns: 1fr;
  }
}
</style>
