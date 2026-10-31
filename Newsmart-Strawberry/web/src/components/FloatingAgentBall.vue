<template>
  <Teleport to="body">
    <div class="floating-ball" :class="{ 'is-open': isOpen, 'is-dragging': isDragging }" :style="ballStyle"
      @mousedown.prevent="onPointerStart($event)" @touchstart.prevent="onPointerStart($event)" @click.stop="handleBallClick">
      <div class="ball-inner"><img class="ball-icon" src="/favicon.svg" alt="温室总管" /><span class="ball-pulse"></span></div>
    </div>

    <div class="drawer-overlay" :class="{ show: isOpen }" @click="close"></div>

    <div class="agent-drawer" :class="{ show: isOpen }">
      <!-- 头部 -->
      <div class="drawer-header">
        <div class="drawer-title" @click="agentMenuOpen = !agentMenuOpen">
          <img class="drawer-avatar" src="/favicon.svg" alt="温室总管" />
          <div><strong>{{ currentAgentLabel }}</strong><small>{{ threadId ? '对话中' : '新对话' }}</small></div>
          <ChevronDown :size="14" class="agent-chevron" :class="{ open: agentMenuOpen }" />
        </div>
        <div class="drawer-actions">
          <button class="dbtn" title="新建对话" @click="newChat"><Plus :size="16" /></button>
          <button class="dbtn" title="历史对话" @click="showConvs = !showConvs; if (showConvs) loadConvs()"><MessageSquare :size="16" /></button>
          <button class="dbtn" title="全屏打开" @click="openFullChat"><ExternalLink :size="16" /></button>
          <button class="dbtn" title="关闭" @click="close"><X :size="18" /></button>
        </div>
      </div>

      <!-- 对话列表 -->
      <div v-if="showConvs" class="conv-panel">
        <div v-if="convs.length === 0" class="conv-empty">暂无历史对话</div>
        <div v-for="c in convs" :key="c.id" class="conv-item" :class="{ active: c.id === threadId }" @click="selectConv(c)">
          <span class="conv-title">{{ c.title || '新对话' }}</span>
          <span class="conv-time">{{ (c.updated_at || '').slice(5, 16) }}</span>
          <button class="conv-del" @click.stop="delConv(c.id)"><X :size="11" /></button>
        </div>
      </div>

      <!-- 消息区 -->
      <div class="drawer-body" ref="bodyEl" @click="handleMsgClick">
        <div v-if="msgs.length === 0 && !threadId" class="welcome">
          <img class="welcome-icon" src="/favicon.svg" alt="温室总管" /><h3>温室总管</h3><p>番茄温室 AI 决策助手</p>
        </div>

        <template v-for="(m, i) in msgs" :key="i">
          <div v-if="m.tools?.length" class="tool-row">
            <span v-for="t in m.tools" :key="t.id" class="tool-tag" :class="t.status">{{ t.icon }} {{ t.label }} {{ t.status === 'running' ? '⏳' : '✓' }}</span>
          </div>
          <div v-if="m.content" class="msg-row" :class="m.role">
            <div class="msg-bubble">
              <div class="msg-text" v-html="renderMd(m.content)"></div>
              <!-- 来源标签（可点击展开查看片段） -->
              <div v-if="m.sources?.length" class="msg-sources-row">
                <span v-for="(s, si) in m.sources" :key="si" class="src-tag-click"
                  :class="{ active: expandedSource === `${i}-${si}` }"
                  @click.stop="toggleSource(i, si, s)">
                  {{ s }}
                </span>
              </div>
              <div class="msg-foot"><span class="msg-time">{{ m.time }}</span></div>
              <!-- 展开的引用片段 -->
              <div v-if="expandedSource && expandedSource.startsWith(`${i}-`) && expandedMsgIdx === i"
                class="source-snippet">
                <div class="snippet-header">
                  <span>{{ expandedSourceLabel }}</span>
                  <X :size="12" @click.stop="expandedSource = ''" />
                </div>
                <div class="snippet-body" v-html="renderMd(expandedSourceText)"></div>
              </div>
            </div>
          </div>
        </template>

        <div v-if="loading" class="status-line">{{ statusText }}</div>
      </div>

      <!-- 输入区 -->
      <div class="drawer-foot">
        <textarea ref="inputEl" v-model="input" class="chat-input" rows="1" placeholder="输入问题..."
          :disabled="loading" @keydown.enter.exact.prevent="send" @input="autoResize"></textarea>
        <button class="send-btn" :disabled="!input.trim() || loading" @click="send">
          <Send v-if="!loading" :size="16" /><Loader2 v-else :size="16" class="spin" />
        </button>
      </div>
    </div>

    <!-- cite 引用弹窗 -->
    <Teleport to="body">
      <div v-if="citePop.visible" class="cite-popover"
        :style="{ position: 'fixed', top: citePop.top + 'px', left: citePop.left + 'px' }" @click.stop>
        <div class="cite-pop-header">
          <span>{{ citePop.source }}</span>
          <button @click="citePop.visible = false">&times;</button>
        </div>
        <div class="cite-pop-body">
          <template v-if="citePop.quote">{{ citePop.quote }}</template>
          <template v-else>
            <p class="cite-pop-empty">未找到引用原文片段</p>
            <p class="cite-pop-hint">可能原因：知识库检索结果未返回或 AI 未按要求填入 quote 属性</p>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- 智能体下拉 -->
    <Teleport to="body">
      <div v-if="agentMenuOpen" class="agent-menu-overlay" @click="agentMenuOpen = false"></div>
      <Transition name="sf">
        <div v-if="agentMenuOpen" class="agent-menu-dropdown">
          <div v-for="a in agentOptions" :key="a.value" class="agent-menu-item" :class="{ sel: a.value === selectedAgentId }" @click="switchAgent(a.value)">
            <span class="agent-menu-label">{{ a.label }}</span><span v-if="a.value === selectedAgentId" class="agent-menu-check">✓</span>
          </div>
          <div class="agent-menu-divider"></div>
          <div class="agent-menu-item act" @click="openAgentManage"><span>管理智能体</span></div>
        </div>
      </Transition>
    </Teleport>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { ChevronDown, ExternalLink, MessageSquare, Plus, Send, Loader2, X } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import { useAgentStore } from '@/stores/agent'
import { usePageAgent } from '@/stores/pageAgent'
import { agentApi } from '@/apis/agent_api'
import { citeSourceStore, setCiteSources, getCiteSource } from '@/stores/citeSources'

const md = new MarkdownIt({ breaks: true, linkify: true, html: true })
const { getPageAgentContext } = usePageAgent()
const router = useRouter()
const agentStore = useAgentStore()
const { agents: allAgents, selectedAgentId } = storeToRefs(agentStore)

const agentOptions = computed(() => (allAgents.value || []).filter(a => !a.is_subagent).map(a => ({ label: a.name || a.slug, value: a.id || a.slug })))
const currentAgentLabel = computed(() => agentOptions.value.find(a => a.value === selectedAgentId.value)?.label || '智能助手')
const agentMenuOpen = ref(false)

function renderMd(t) { return t ? md.render(t) : '' }

// 面板
const isOpen = ref(false); const loading = ref(false); const statusText = ref('')
const msgs = ref([]); const input = ref(''); const threadId = ref(null)
const bodyEl = ref(null); const inputEl = ref(null)

// 对话列表
const showConvs = ref(false); const convs = ref([])
function _arr(r) { return Array.isArray(r) ? r : (r?.threads || r?.data || []) }
async function loadConvs() {
  try { const { threadApi } = await import('@/apis/agent_api'); const r = await threadApi.getThreads(agentStore.selectedAgentId, 20, 0); convs.value = _arr(r).slice(0, 20) } catch {}
}
async function selectConv(c) {
  showConvs.value = false; threadId.value = c.id; msgs.value = []; loading.value = false
  try {
    const h = await agentApi.getAgentHistory(c.id)
    const all = h?.history || h?.messages || h?.data || []
    msgs.value = []
    for (const m of all) {
      const role = (m.type === 'human' || m.role === 'user') ? 'user' : 'assistant'
      let content = m.content || ''
      // AI 消息可能把工具调用放在 extra_metadata.content 数组里
      if (!content && m.extra_metadata?.content) {
        const texts = m.extra_metadata.content.filter(c => c.type === 'text' && c.text).map(c => c.text)
        if (texts.length) content = texts.join('\n')
      }
      // 收集工具调用
      const tools = []
      const tcList = m.tool_calls || m.extra_metadata?.tool_calls || []
      for (const tc of tcList) {
        const name = tc.name || tc.function?.name || ''
        if (name) tools.push({ id: ++_seq, label: tlabel(name), icon: name === 'task' ? '🤖' : '🔧', status: 'done' })
      }
      if (content || tools.length) {
        msgs.value.push({ role, content, time: (m.created_at || '').slice(11, 16) || '', tools })
      }
    }
  } catch { msgs.value = [] }
}
async function delConv(id) { try { const { threadApi } = await import('@/apis/agent_api'); await threadApi.deleteThread(id); convs.value = convs.value.filter(c => c.id !== id) } catch {}; if (threadId.value === id) newChat() }
function newChat() { threadId.value = null; msgs.value = []; showConvs.value = false }
async function switchAgent(id) {
  if (id === selectedAgentId.value) { agentMenuOpen.value = false; return }
  await agentStore.selectAgent(id)
  agentMenuOpen.value = false
  // 切换到该智能体的最近一次对话
  threadId.value = null; msgs.value = []; showConvs.value = false
  await loadLastConv()
}

// 拖拽
const isDragging = ref(false); const hasMoved = ref(false); const pointerMoved = ref(false)
const dragStart = reactive({ x: 0, y: 0, origRight: 24, origBottom: 80 })
const ballStyle = reactive({ right: '24px', bottom: '80px' })
function onPointerStart(e) {
  if (isOpen.value) return; hasMoved.value = false; pointerMoved.value = false; isDragging.value = false
  const cx = e.touches ? e.touches[0].clientX : e.clientX; const cy = e.touches ? e.touches[0].clientY : e.clientY
  dragStart.x = cx; dragStart.y = cy; dragStart.origRight = parseInt(ballStyle.right); dragStart.origBottom = parseInt(ballStyle.bottom)
  const mv = (ev) => { const mx = ev.touches ? ev.touches[0].clientX : ev.clientX; const my = ev.touches ? ev.touches[0].clientY : ev.clientY; if (Math.abs(dragStart.x - mx) > 3 || Math.abs(dragStart.y - my) > 3) pointerMoved.value = true; if (pointerMoved.value) isDragging.value = true; ballStyle.right = Math.min(window.innerWidth - 60, Math.max(8, dragStart.origRight + dragStart.x - mx)) + 'px'; ballStyle.bottom = Math.min(window.innerHeight - 60, Math.max(8, dragStart.origBottom + dragStart.y - my)) + 'px' }
  const up = () => { isDragging.value = false; if (pointerMoved.value) hasMoved.value = true; rm() }
  const rm = () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); window.removeEventListener('touchmove', mv); window.removeEventListener('touchend', up) }
  window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up); window.addEventListener('touchmove', mv, { passive: false }); window.addEventListener('touchend', up)
}
function handleBallClick() { if (hasMoved.value || pointerMoved.value) { hasMoved.value = false; pointerMoved.value = false; return } isOpen.value = !isOpen.value; if (isOpen.value) nextTick(() => inputEl.value?.focus()) }
function close() { isOpen.value = false; agentMenuOpen.value = false; showConvs.value = false }
function scrollBottom() { nextTick(() => { if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight }) }
function autoResize() { nextTick(() => { const el = inputEl.value; if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 100) + 'px' } }) }

// cite 引用弹窗
const citePop = reactive({ visible: false, top: 0, left: 0, source: '', quote: '', index: '' })
function handleMsgClick(e) {
  const cite = e.target.closest('cite')
  if (!cite) { citePop.visible = false; return }

  citePop.index = cite.textContent?.trim() || ''
  citePop.source = cite.getAttribute('source') || cite.getAttribute('data-source') || ''
  citePop.quote = cite.getAttribute('quote') || ''

  // 1. citeSourceStore
  if (!citePop.quote || citePop.source === '未知来源') {
    const src = getCiteSource(citePop.index)
    if (src) {
      if (src.content && !citePop.quote) citePop.quote = src.content.slice(0, 400)
      if (src.source && citePop.source === '未知来源') citePop.source = src.source
    }
  }

  // 2. AI 写了 source="未知来源"，到消息文本里找真正的文件名
  if (citePop.source === '未知来源' || !citePop.quote) {
    const idx = parseInt(citePop.index)
    if (idx > 0) {
      // 先查当前 AI 回复中【来源 N】格式
      for (const msg of msgs.value) {
        if (!msg.content || msg.role !== 'assistant') continue
        const re = new RegExp(`【来源\\s*${idx}】\\s*(.{10,400})`, 's')
        const m = msg.content.match(re)
        if (m) {
          const full = m[1].trim()
          const nl = full.indexOf('\n')
          if (nl > 0 && nl < 60) {
            if (citePop.source === '未知来源') citePop.source = full.slice(0, nl).trim()
            if (!citePop.quote) citePop.quote = full.slice(nl).trim()
          } else {
            if (!citePop.quote) citePop.quote = full
          }
          break
        }
      }
    }
  }

  // 3. 兜底：citeSourceStore 里的文件名匹配
  if (citePop.source === '未知来源') {
    const allSrcs = citeSourceStore.sources || []
    const match = allSrcs.find(s => String(s.index) === String(citePop.index))
    if (match?.source) citePop.source = match.source
  }

  if (!citePop.source || citePop.source === '未知来源') citePop.source = '知识库文档'
  showCitePop(cite)
}

function showCitePop(cite) {
  const rect = cite.getBoundingClientRect()
  citePop.top = rect.bottom + 6
  citePop.left = Math.min(rect.left, window.innerWidth - 300)
  citePop.visible = true
}

// 来源标签点击展开
const expandedSource = ref('')
const expandedMsgIdx = ref(-1)
const expandedSourceLabel = ref('')
const expandedSourceText = ref('')

function toggleSource(msgIdx, srcIdx, label) {
  const key = `${msgIdx}-${srcIdx}`
  if (expandedSource.value === key) { expandedSource.value = ''; return }
  expandedSource.value = key
  expandedMsgIdx.value = msgIdx
  expandedSourceLabel.value = label
  // 从消息内容中提取相关片段
  const msg = msgs.value[msgIdx]
  if (msg?.content) {
    // 尝试提取关键词相关段落（100-300字）
    const text = msg.content
    const keywords = [label, label.replace('仪表盘', '传感器'), label.replace('传感器', '数据')]
    let snippet = ''
    for (const kw of keywords) {
      const idx = text.indexOf(kw)
      if (idx >= 0) {
        const start = Math.max(0, idx - 40)
        const end = Math.min(text.length, idx + 300)
        snippet = (start > 0 ? '...' : '') + text.slice(start, end) + (end < text.length ? '...' : '')
        break
      }
    }
    expandedSourceText.value = snippet || text.slice(0, 300) + (text.length > 300 ? '...' : '')
  }
}

// 确保智能体就绪
async function ensureReady() {
  if (!agentStore.isInitialized) await agentStore.initialize()
  const master = agentStore.agents.find(a => a.slug === 'greenhouse-master' || a.id === 'greenhouse-master')
  if (master && agentStore.selectedAgentId !== master.id) await agentStore.selectAgent(master.id)
  else if (!agentStore.selectedAgentId) { const f = agentStore.agents.find(a => !a.is_subagent); if (f) await agentStore.selectAgent(f.id) }
}

// 打开时加载最近一次对话，不自动创建新对话
async function loadLastConv() {
  await ensureReady()
  try {
    const { threadApi } = await import('@/apis/agent_api')
    const r = await threadApi.getThreads(agentStore.selectedAgentId, 1, 0)
    const threads = _arr(r)
    if (threads.length > 0) {
      threadId.value = threads[0].id
      const h = await agentApi.getAgentHistory(threadId.value)
      const all = h?.history || h?.messages || h?.data || []
      msgs.value = []
      for (const m of all) {
        const role = (m.type === 'human' || m.role === 'user') ? 'user' : 'assistant'
        let content = m.content || ''
        if (!content && m.extra_metadata?.content) {
          const texts = m.extra_metadata.content.filter(c => c.type === 'text' && c.text).map(c => c.text)
          if (texts.length) content = texts.join('\n')
        }
        const tools = []
        for (const tc of (m.tool_calls || m.extra_metadata?.tool_calls || [])) {
          const name = tc.name || tc.function?.name || ''
          if (name) tools.push({ id: ++_seq, label: tlabel(name), icon: name === 'task' ? '🤖' : '🔧', status: 'done' })
        }
        if (content || tools.length) {
          msgs.value.push({ role, content, time: (m.created_at || '').slice(11, 16) || '', tools })
        }
      }
    }
  } catch {}
}

watch(isOpen, async (val) => { if (val && !threadId.value) await loadLastConv() })

let _seq = 0
const TOOL_MAP = { get_iot_dashboard: '仪表盘', get_air_sensors: '空气传感器', get_soil_sensors: '土壤传感器', get_actuators: '执行器', task: '子智能体', tavily_search: '联网搜索', query_kb: '知识库', list_kbs: '知识库列表' }
function tlabel(n) { return TOOL_MAP[n] || n }

async function send() {
  const text = input.value.trim(); if (!text || loading.value) return
  input.value = ''; autoResize()
  const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  msgs.value.push({ role: 'user', content: text, time: now })
  loading.value = true; statusText.value = '💭 思考中...'; scrollBottom()

  // 占位 assistant 消息
  const am = { role: 'assistant', content: '', time: '', tools: [], sources: [] }
  msgs.value.push(am)

  try {
    await ensureReady()
    const agentId = agentStore.selectedAgentId

    // 创建线程
    if (!threadId.value) {
      const { threadApi } = await import('@/apis/agent_api')
      const tr = await threadApi.createThread(agentId, text.slice(0, 30))
      threadId.value = tr?.id || tr?.thread_id
    }

    statusText.value = '⚙️ 提交任务...'
    scrollBottom()

    const pageCtx = getPageAgentContext()
    const fullQuery = pageCtx ? text + pageCtx : text
    const runRes = await agentApi.createAgentRun({ query: fullQuery, agent_id: agentId, thread_id: threadId.value, meta: {} })
    const runId = runRes?.run_id
    if (!runId) throw new Error('创建运行失败')

    // SSE 流
    const startTime = Date.now()
    const timer = setInterval(() => {
      const s = Math.floor((Date.now() - startTime) / 1000)
      statusText.value = `🔍 处理中... (${s}s)` + (am.tools?.length ? ' — ' + am.tools.map(t => t.label).join('、') : '')
      scrollBottom()
    }, 1000)

    const resp = await agentApi.streamAgentRunEvents(runId, '0-0')
    const reader = resp.body.getReader(); const dec = new TextDecoder()
    let buf = ''; let content = ''

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
            // 工具调用
            const name = item.name || item.tool_call?.name || ''
            if (name) {
              const label = tlabel(name)
              if (!am.tools.find(t => t.label === label)) {
                am.tools.push({ id: ++_seq, label, icon: name === 'task' ? '🤖' : '🔧', status: 'running' })
                statusText.value = '🔧 ' + am.tools.map(t => t.label).join('、')
                scrollBottom()
              }
            }
            // 工具结果
            if (item.tool_call_id || item.type === 'tool' || item.role === 'tool') {
              const running = am.tools.filter(t => t.status === 'running')
              if (running.length) { running[running.length - 1].status = 'done'; statusText.value = '🔧 ' + am.tools.map(t => t.label + (t.status === 'running' ? '⏳' : '✓')).join('、') }
            }
            // 文本
            const t = _pick(item)
            if (t) { content += t; am.content = content; scrollBottom() }
          }
        } catch {}
      }
    }

    clearInterval(timer)
    statusText.value = ''

    // 从历史拉取完整回复 + 引用来源
    if (threadId.value) {
      await new Promise(r => setTimeout(r, 2000))
      // 先捕获 query_kb 的引用来源
      try {
        const h2 = await agentApi.getAgentHistory(threadId.value)
        const all2 = h2?.history || h2?.messages || h2?.data || []
        for (const m of all2) {
          const checkTc = (tc) => {
            if (tc.name !== 'query_kb') return
            let raw = tc.tool_call_result?.content
            if (!raw && tc.tool_call_result) raw = tc.tool_call_result
            if (!raw) return
            try {
              // 尝试多种解析方式
              let parsed = raw
              if (typeof raw === 'string') {
                try { parsed = JSON.parse(raw) } catch {
                  // 可能不是 JSON，直接当文本
                  parsed = { results: [{ content: raw, metadata: {} }] }
                }
              }
              const results = parsed?.results || []
              if (results.length) {
                const sources = results.map((r, i) => ({
                  index: i + 1,
                  source: (r.metadata?.source || r.file_id || ''),
                  content: (r.content || '').replace(/^【来源\s*\d+】[^\n]*\n?/, '').trim()
                }))
                if (sources.some(s => s.content)) setCiteSources(sources)
              }
            } catch {}
          }
          if (m.tool_calls) m.tool_calls.forEach(checkTc)
          // 也检查独立 tool 消息
          if (m.type === 'tool' && m.name === 'query_kb') {
            checkTc({ name: 'query_kb', tool_call_result: { content: m.content || m.tool_output } })
          }
        }
      } catch {}
      try {
        const hist = await agentApi.getAgentHistory(threadId.value)
        const all = hist?.history || hist?.messages || hist?.data || []
        const seen = new Set(); const htools = []
        for (const m of all) {
          for (const tc of (m.tool_calls || m.extra_metadata?.tool_calls || [])) { const n = tc.name || tc.function?.name || ''; if (n && !seen.has(n)) { seen.add(n); htools.push({ id: ++_seq, label: tlabel(n), icon: n === 'task' ? '🤖' : '🔧', status: 'done' }) } }
        }
        if (htools.length) am.tools = htools
        for (let i = all.length - 1; i >= 0; i--) {
          const m = all[i]
          if (m.type === 'ai' || m.role === 'assistant') {
            // 优先用 content
            if (m.content?.trim()) { am.content = m.content.trim(); break }
            // 尝试从 extra_metadata.content 提取 text
            if (m.extra_metadata?.content) {
              const texts = m.extra_metadata.content.filter(c => c.type === 'text' && c.text).map(c => c.text)
              if (texts.length) { am.content = texts.join('\n'); break }
            }
          }
        }
      } catch {}
    }

    if (!am.content) am.content = '抱歉，未能获取回答。'
  } catch (e) {
    am.content = '发生错误：' + (e.message || '未知')
  } finally {
    loading.value = false; statusText.value = ''
    am.time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    scrollBottom()
    loadConvs()
  }
}

function _pick(item) {
  if (!item) return ''; if (typeof item === 'string') return item
  if (typeof item.content === 'string') return item.content
  if (typeof item.text === 'string') return item.text
  if (Array.isArray(item.content)) return item.content.map(c => typeof c === 'string' ? c : c?.text || c?.type === 'text' ? c.text : '').join('')
  return ''
}

function openFullChat() { close(); if (threadId.value) router.push({ name: 'AgentCompWithThreadId', params: { thread_id: threadId.value } }); else router.push('/agent') }
function openAgentManage() { agentMenuOpen.value = false; close(); router.push({ name: 'ModelManageComp', query: { tab: 'agents' } }) }
</script>

<style scoped lang="less">
.floating-ball { position: fixed; z-index: 9998; width: 52px; height: 52px; border-radius: 50%; background: var(--gray-0); border: 2px solid var(--main-color); box-shadow: 0 4px 16px rgba(0,0,0,.12), 0 0 0 4px color-mix(in srgb, var(--main-color) 15%, transparent); cursor: pointer; user-select: none; transition: transform .2s, box-shadow .2s; &:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(0,0,0,.16), 0 0 0 8px color-mix(in srgb, var(--main-color) 20%, transparent); } &:active { transform: scale(.95); } &.is-open { opacity: 0; pointer-events: none; } &.is-dragging { transition: none; transform: scale(1.1); box-shadow: 0 8px 32px rgba(0,0,0,.2), 0 0 0 10px color-mix(in srgb, var(--main-color) 25%, transparent); } }
.ball-inner { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; position: relative; }
.ball-icon { width: 30px; height: 30px; }
.ball-pulse { position: absolute; inset: -6px; border-radius: 50%; border: 2px solid color-mix(in srgb, var(--main-color) 30%, transparent); animation: pulse-ring 2.5s ease-out infinite; }
@keyframes pulse-ring { 0% { transform: scale(1); opacity: .7; } 100% { transform: scale(1.5); opacity: 0; } }

.drawer-overlay { position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,.2); opacity: 0; pointer-events: none; transition: opacity .25s; &.show { opacity: 1; pointer-events: auto; } }
.agent-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: 440px; max-width: 100vw; z-index: 10000; background: var(--gray-0); border-left: 1px solid var(--gray-150); box-shadow: -4px 0 32px rgba(0,0,0,.1); display: flex; flex-direction: column; transform: translateX(100%); transition: transform .3s cubic-bezier(.4,0,.2,1); &.show { transform: translateX(0); } }

.drawer-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--gray-100); flex-shrink: 0; }
.drawer-title { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 6px; border-radius: 8px; &:hover { background: var(--gray-50); } strong { font-size: 13px; font-weight: 650; color: var(--gray-1000); max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } small { font-size: 10px; color: var(--gray-500); display: block; } }
.drawer-avatar { width: 24px; height: 24px; padding: 4px; display: flex; align-items: center; justify-content: center; background: var(--main-50); border-radius: 8px; flex-shrink: 0; }
.agent-chevron { color: var(--gray-400); flex-shrink: 0; transition: transform .2s; &.open { transform: rotate(180deg); } }
.drawer-actions { display: flex; gap: 1px; }
.dbtn { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: 1px solid transparent; border-radius: 6px; background: transparent; color: var(--gray-500); cursor: pointer; &:hover { background: var(--gray-50); color: var(--gray-800); } }

.conv-panel { max-height: 150px; overflow-y: auto; border-bottom: 1px solid var(--gray-100); padding: 4px 8px; flex-shrink: 0; }
.conv-empty { padding: 12px; text-align: center; color: var(--gray-400); font-size: 11px; }
.conv-item { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 6px; cursor: pointer; font-size: 11px; &:hover { background: var(--gray-25); } &.active { background: var(--main-10); } }
.conv-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--gray-800); font-weight: 500; }
.conv-time { font-size: 10px; color: var(--gray-400); flex-shrink: 0; }
.conv-del { opacity: 0; border: none; background: transparent; color: var(--gray-400); cursor: pointer; padding: 1px; border-radius: 3px; &:hover { color: var(--color-error-500); } .conv-item:hover & { opacity: 1; } }

.drawer-body { flex: 1; overflow-y: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; }
.welcome { text-align: center; padding: 30px 10px; .welcome-icon { width: 64px; height: 64px; margin-bottom: 8px; } h3 { font-size: 16px; font-weight: 700; color: var(--gray-1000); margin: 0 0 4px; } p { font-size: 12px; color: var(--gray-500); } }

.tool-row { display: flex; flex-wrap: wrap; gap: 4px; }
.tool-tag { display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px; border-radius: 10px; background: var(--main-10); color: var(--main-color); font-size: 10px; font-weight: 500; &.done { background: var(--color-success-50); color: var(--color-success-700); } }

.status-line { padding: 8px 12px; font-size: 12px; color: var(--gray-500); background: var(--gray-25); border-radius: 8px; }

.msg-row { max-width: 90%; &.user { align-self: flex-end; .msg-bubble { background: var(--main-color); color: var(--gray-0); border-radius: 14px 14px 4px 14px; } } &.assistant { align-self: flex-start; .msg-bubble { background: var(--gray-50); color: var(--gray-900); border-radius: 14px 14px 14px 4px; } } }
.msg-bubble { padding: 8px 12px; font-size: 13px; line-height: 1.5; :deep(p) { margin: 0 0 4px; &:last-child { margin: 0; } } :deep(code) { background: var(--gray-100); padding: 1px 3px; border-radius: 3px; font-size: 11px; } :deep(pre) { background: var(--gray-100); padding: 6px 8px; border-radius: 6px; overflow-x: auto; font-size: 11px; } :deep(ul), :deep(ol) { padding-left: 14px; margin: 2px 0; } }
.msg-foot { margin-top: 2px; }
.msg-time { font-size: 10px; color: var(--gray-400); }
.msg-sources-row { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px; }
.src-tag-click { font-size: 10px; padding: 2px 7px; border-radius: 8px; background: var(--main-10); color: var(--main-600); cursor: pointer; transition: background .15s; &:hover { background: var(--main-30); } &.active { background: var(--main-color); color: var(--gray-0); } }
.source-snippet { margin-top: 6px; border: 1px solid var(--gray-150); border-radius: 6px; overflow: hidden; }
.snippet-header { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: var(--gray-25); font-size: 11px; color: var(--gray-600); border-bottom: 1px solid var(--gray-100); }
.snippet-body { padding: 6px 8px; font-size: 11px; color: var(--gray-700); line-height: 1.5; max-height: 200px; overflow-y: auto; background: var(--gray-0); :deep(p) { margin: 0 0 4px; } :deep(code) { font-size: 10px; } }

.drawer-foot { padding: 8px 12px; border-top: 1px solid var(--gray-100); display: flex; gap: 6px; align-items: flex-end; flex-shrink: 0; }
.chat-input { flex: 1; border: 1px solid var(--gray-200); border-radius: 10px; padding: 8px 10px; font-size: 13px; line-height: 1.5; resize: none; outline: none; font-family: inherit; background: var(--gray-25); color: var(--gray-900); max-height: 100px; &:focus { border-color: var(--main-color); background: var(--gray-0); } &:disabled { opacity: .6; } &::placeholder { color: var(--gray-400); } }
.send-btn { width: 34px; height: 34px; border-radius: 10px; border: none; background: var(--main-color); color: var(--gray-0); display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; &:disabled { opacity: .4; cursor: not-allowed; } &:not(:disabled):hover { opacity: .85; } }
.spin { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }

.agent-menu-overlay { position: fixed; inset: 0; z-index: 10001; }
.agent-menu-dropdown { position: fixed; top: 48px; right: 210px; z-index: 10002; min-width: 160px; padding: 4px; background: var(--gray-0); border: 1px solid var(--gray-100); border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
.agent-menu-item { display: flex; justify-content: space-between; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 12px; &:hover { background: var(--gray-50); } &.sel { background: var(--main-10); color: var(--main-color); } &.act { color: var(--gray-500); font-size: 11px; } }
.agent-menu-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--gray-800); .sel & { color: var(--main-color); font-weight: 600; } }
.agent-menu-check { color: var(--main-color); font-weight: 700; margin-left: 6px; }
.agent-menu-divider { height: 1px; margin: 3px 5px; background: var(--gray-100); }
.sf-enter-active, .sf-leave-active { transition: all .15s; }
.sf-enter-from, .sf-leave-to { opacity: 0; transform: scale(.95) translateY(-4px); }

.cite-popover { position: fixed; z-index: 10010; width: 280px; background: var(--gray-0); border: 1px solid var(--gray-200); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.12); overflow: hidden; }
.cite-pop-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--gray-25); font-size: 11px; font-weight: 600; color: var(--gray-700); border-bottom: 1px solid var(--gray-100); button { border: none; background: transparent; font-size: 16px; color: var(--gray-400); cursor: pointer; } }
.cite-pop-body { padding: 8px 10px; font-size: 12px; color: var(--gray-700); line-height: 1.5; max-height: 200px; overflow-y: auto; }

@media (max-width: 480px) { .agent-drawer { width: 100vw; } }
</style>
