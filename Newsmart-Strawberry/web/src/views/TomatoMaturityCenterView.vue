<template>
  <div class="maturity-center layout-container">
    <PageHeader title="成熟度管理中心" :show-border="true">
      <template #info>
        <a-button @click="$router.push('/disease-detection')">病虫害识别</a-button>
        <PageAgentDropdown default-agent="maturity-analyzer" />
        <span class="threshold-config">
          <span>采摘阈值</span>
          <input
            type="number"
            class="threshold-input"
            v-model.number="harvestThreshold"
            min="0" max="100"
            @change="persistThreshold"
          />
          <span>%</span>
        </span>
        <span class="status-pill" :class="cameraReady ? 'online' : 'offline'">
          <Camera :size="14" />
          {{ cameraReady ? '摄像头就绪' : '摄像头未连接' }}
        </span>
      </template>
    </PageHeader>

    <main class="maturity-content">
      <!-- 检测操作区 -->
      <section class="detect-action-bar">
        <div class="action-left">
          <a-select v-model:value="albumId" placeholder="选择草莓照片集" :disabled="detecting" :options="albums.map(a => ({ label: a.name, value: a.id }))" style="width: 220px; max-width: 100%" @change="latestResult = null; loadHistory()" />
          <div class="zone-selector">
            <span>棚区</span>
            <button
              v-for="z in zones"
              :key="z.id"
              :class="{ active: selectedZone === z.id }"
              @click="selectedZone = z.id"
            >{{ z.name }}</button>
          </div>
          <div class="camera-selector">
            <span>摄像头</span>
            <select v-model="selectedCameraId" :disabled="detecting || cameraActive">
              <option v-if="!availableCameras.length" :value="-1">未检测到摄像头</option>
              <option
                v-for="cam in availableCameras"
                :key="cam.id"
                :value="cam.id"
              >{{ cam.name }}</option>
            </select>
          </div>
        </div>
        <div class="action-right">
          <button
            v-if="!showCaptured"
            class="preview-btn"
            :class="{ active: cameraActive }"
            @click="toggleCamera"
          >
            <Video :size="16" />
            {{ cameraActive ? '关闭摄像头' : '开启摄像头' }}
          </button>
          <button
            v-if="!showCaptured"
            class="capture-btn"
            :disabled="detecting || vlmAnalyzing || !cameraActive || !albumId"
            @click="doCapture"
          >
            <Camera :size="18" />
            {{ detecting ? '检测中...' : '拍照检测' }}
          </button>
          <button
            v-if="showCaptured"
            class="retake-action-btn"
            :disabled="detecting || vlmAnalyzing"
            @click="retakePhoto"
          >
            <RotateCcw :size="18" />
            重新拍照
          </button>
        </div>
      </section>

      <!-- 摄像头预览 + 检测结果 -->
      <section class="preview-result-section">
        <!-- 左侧：摄像头预览 / 拍摄照片 -->
        <div class="camera-panel">
          <div class="panel-header">
            <div class="section-title">
              <Camera :size="18" />
              <h3>{{ showCaptured ? '拍摄照片' : '摄像头画面' }}</h3>
            </div>
          </div>
          <div class="video-container">
            <!-- 摄像头预览模式 -->
            <video
              ref="videoRef"
              autoplay
              playsinline
              muted
              class="camera-video"
              v-show="cameraActive && !showCaptured"
            ></video>
            <canvas ref="canvasRef" style="display: none;"></canvas>
            <!-- 拍摄照片模式 -->
            <img
              v-if="showCaptured && capturedImageSrc"
              :src="capturedImageSrc"
              alt="拍摄照片"
              class="captured-image"
            />
            <!-- 占位符 -->
            <div class="camera-placeholder" v-if="!cameraActive && !showCaptured">
              <Camera :size="48" />
              <p>点击"开启摄像头"开始</p>
            </div>
          </div>
        </div>

        <!-- 右侧：检测结果 -->
        <div class="result-panel">
          <div class="panel-header">
            <div class="section-title">
              <ScanLine :size="18" />
              <h3>检测结果</h3>
            </div>
            <span class="result-time" v-if="latestResult">{{ formatTime(latestResult.created_at) }}</span>
          </div>

          <!-- 检测中 / AI 分析中状态 -->
          <div class="detecting-state" v-if="detecting || vlmAnalyzing">
            <div class="loading-spinner"></div>
            <p>{{ vlmAnalyzing ? '大模型正在分析...' : '正在识别中...' }}</p>
          </div>

          <!-- YOLO 检测结果（有标框图） -->
          <div class="result-content" v-else-if="latestResult">
            <DetectionEvidence v-if="latestResult.evidence" :record="latestResult.evidence" />
            <div class="annotated-image-wrapper">
              <img
                v-if="latestResult.annotated_image_base64"
                :src="'data:image/jpeg;base64,' + latestResult.annotated_image_base64"
                alt="检测标注图"
                class="annotated-image"
              />
            </div>
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-label">总数</span>
                <strong>{{ latestResult.total_count }}</strong>
              </div>
              <div class="stat-item ripe">
                <span class="stat-label">成熟</span>
                <strong>{{ latestResult.ripe_count }}</strong>
              </div>
              <div class="stat-item half">
                <span class="stat-label">半成熟</span>
                <strong>{{ latestResult.half_ripe_count }}</strong>
              </div>
              <div class="stat-item unripe">
                <span class="stat-label">未成熟</span>
                <strong>{{ latestResult.unripe_count }}</strong>
              </div>
            </div>
            <div class="maturity-bar">
              <div class="bar-header">
                <span>成熟度</span>
                <strong :class="{ ready: latestResult.maturity_ratio >= harvestThreshold }">{{ latestResult.maturity_ratio }}%</strong>
              </div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: latestResult.maturity_ratio + '%' }" :class="{ ready: latestResult.maturity_ratio >= harvestThreshold }"></div>
                <div class="bar-threshold" :style="{ left: harvestThreshold + '%' }"></div>
              </div>
            </div>
            <div class="recommendation">
              <ClipboardCheck :size="16" />
              <span>{{ latestResult.recommendation }}</span>
            </div>
            <!-- YOLO 成功 → AI 增强分析 -->
            <button
              class="vlm-enhance-btn"
              :disabled="vlmAnalyzing"
              @click="doVlmAnalyze"
              v-if="latestResult.total_count > 0"
            >
              <Sparkles :size="16" />
              {{ vlmAnalyzing ? 'AI 分析中...' : 'AI 增强分析' }}
            </button>
            <!-- YOLO 失败 → 使用大模型重新检测 -->
            <div class="vlm-fallback" v-if="latestResult.total_count === 0">
              <p class="fallback-hint">当前模型未检出草莓，大模型分析仅作独立参考</p>
              <button
                class="vlm-fallback-btn"
                :disabled="vlmAnalyzing"
                @click="doVlmAnalyze"
              >
                <Sparkles :size="16" />
                {{ vlmAnalyzing ? 'AI 分析中...' : '使用大模型检测' }}
              </button>
            </div>
          </div>

          <!-- 仅有 VLM 结果（YOLO 失败后，无标框图） -->
          <div class="result-content vlm-only-result" v-else-if="vlmResult && showCaptured">
            <div class="annotated-image-wrapper">
              <img
                :src="vlmResult.annotated_image_base64 ? 'data:image/jpeg;base64,' + vlmResult.annotated_image_base64 : capturedImageSrc"
                alt="检测结果"
                class="annotated-image"
              />
            </div>
            <div class="vlm-result-badge">
              <Sparkles :size="14" />
              <span>大模型识别结果</span>
            </div>
          </div>

          <!-- 空状态 -->
          <div class="empty-state" v-else>
            <ScanLine :size="48" />
            <p>开启摄像头后点击"拍照检测"</p>
          </div>
        </div>
      </section>

      <!-- 大模型分析结果 -->
      <section class="vlm-section" v-if="vlmResult || vlmAnalyzing">
        <div class="vlm-header">
          <div class="section-title">
            <Sparkles :size="18" />
            <h3>大模型智能分析</h3>
          </div>
          <span class="vlm-badge">Qwen3-VL-Plus</span>
        </div>

        <div class="vlm-loading" v-if="vlmAnalyzing">
          <div class="loading-spinner"></div>
          <p>大模型正在分析图片，请稍候...</p>
        </div>

        <div class="vlm-content" v-else-if="vlmResult">
          <div class="vlm-grid">
            <div class="vlm-card maturity-card">
              <div class="vlm-card-header">
                <Gauge :size="16" />
                <span>成熟度评估</span>
              </div>
              <div class="vlm-card-body">
                <span class="vlm-level" :class="vlmLevelClass">{{ vlmResult.maturity_level }}</span>
                <p>{{ vlmResult.maturity_detail }}</p>
              </div>
            </div>

            <div class="vlm-card advice-card">
              <div class="vlm-card-header">
                <Sprout :size="16" />
                <span>种植建议</span>
              </div>
              <div class="vlm-card-body">
                <p>{{ vlmResult.planting_advice }}</p>
              </div>
            </div>

            <div class="vlm-card pest-card">
              <div class="vlm-card-header">
                <Bug :size="16" />
                <span>病虫害识别</span>
              </div>
              <div class="vlm-card-body">
                <p>{{ vlmResult.pest_disease }}</p>
              </div>
            </div>
          </div>

          <div class="vlm-summary" v-if="vlmResult.overall_summary">
            <ClipboardCheck :size="16" />
            <span>{{ vlmResult.overall_summary }}</span>
          </div>
        </div>
      </section>

      <!-- 汇总卡片 -->
      <section class="summary-grid">
        <article v-for="item in summary" :key="item.label" class="summary-card">
          <component :is="item.icon" :size="20" />
          <div>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.note }}</p>
          </div>
        </article>
      </section>

      <!-- 历史记录 + 采摘建议 -->
      <section class="records-layout">
        <article class="scan-panel">
          <div class="section-title">
            <Route :size="18" />
            <h3>检测记录</h3>
          </div>
          <div class="scan-list" v-if="historyRecords.length">
            <div v-for="record in historyRecords" :key="record.id" class="scan-row">
              <div class="scan-main">
                <strong>{{ getZoneName(record.zone) }} · 检测 #{{ record.id.slice(-6) }}</strong>
                <span>{{ formatTime(record.created_at) }}</span>
              </div>
              <div class="scan-numbers">
                <span>{{ record.total_count }} 颗</span>
                <strong :class="{ ready: record.maturity_ratio >= harvestThreshold }">{{ record.maturity_ratio }}%</strong>
              </div>
              <span class="scan-advice" :class="{ ready: record.maturity_ratio >= harvestThreshold }">
                {{ record.maturity_ratio >= harvestThreshold ? '可采摘' : '继续观察' }}
              </span>
            </div>
          </div>
          <div v-else class="empty-hint">
            <Camera :size="32" />
            <p>暂无检测记录，点击"拍照检测"开始</p>
          </div>
        </article>

        <article class="advice-panel">
          <div class="section-title">
            <ClipboardCheck :size="18" />
            <h3>采摘建议</h3>
          </div>
          <div class="advice-list">
            <div v-for="advice in displayAdvice" :key="advice.title" class="advice-item">
              <span class="advice-level" :class="advice.level">{{ advice.levelText }}</span>
              <div>
                <strong>{{ advice.title }}</strong>
                <p>{{ advice.desc }}</p>
              </div>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import {
  Bug,
  Camera,
  ClipboardCheck,
  Gauge,
  RotateCcw,
  Route,
  ScanLine,
  Sparkles,
  Sprout,
  Timer,
  Video
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageAgentDropdown from '@/components/PageAgentDropdown.vue'
import { getHarvestThreshold, setHarvestThreshold } from '@/data/tomatoData.js'
import { listCameras } from '@/apis/detect_api.js'
import { listAlbums, uploadAlbumPhoto } from '@/apis/album_api'
import { fieldRecords, runDetection } from '@/apis/field_work_api'
import DetectionEvidence from '@/components/DetectionEvidence.vue'
import { analyzeBase64 } from '@/apis/vlm_api.js'

const albums = ref([]), albumId = ref()

// 棚区配置
const zones = [
  { id: 'A', name: 'A 区' },
  { id: 'B', name: 'B 区' },
  { id: 'C', name: 'C 区' }
]

// 状态
const selectedZone = ref('A')
const harvestThreshold = ref(getHarvestThreshold())
const cameraReady = ref(false)
const cameraActive = ref(false)
const detecting = ref(false)
const latestResult = ref(null)
const historyRecords = ref([])
const availableCameras = ref([])
const selectedCameraId = ref(0)

// 大模型分析状态
const vlmAnalyzing = ref(false)
const vlmResult = ref(null)
let lastCapturedBase64 = null  // 缓存最近一次拍照的 base64，供 VLM 复用

// 拍照状态：拍照后左侧显示拍摄的照片，右侧显示标框结果
const showCaptured = ref(false)
const capturedImageSrc = ref('')

// DOM refs
const videoRef = ref(null)
const canvasRef = ref(null)

// 当前媒体流
let currentStream = null

function persistThreshold() {
  const n = harvestThreshold.value
  if (n >= 0 && n <= 100) setHarvestThreshold(n)
}

function getZoneName(zoneId) {
  return zones.find(z => z.id === zoneId)?.name || zoneId
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const time = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return isToday ? `今天 ${time}` : `${d.getMonth() + 1}/${d.getDate()} ${time}`
}

// 开启/关闭摄像头
async function toggleCamera() {
  if (cameraActive.value) {
    stopCamera()
  } else {
    await startCamera()
  }
}

async function startCamera() {
  try {
    // 停止之前的流
    stopCamera()

    // 获取摄像头
    const constraints = {
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment'  // 优先使用后置摄像头
      }
    }

    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    currentStream = stream

    if (videoRef.value) {
      videoRef.value.srcObject = stream
      cameraActive.value = true
      cameraReady.value = true
    }
  } catch (err) {
    console.error('无法访问摄像头:', err)
    alert('无法访问摄像头，请确保已授权摄像头权限')
  }
}

function stopCamera() {
  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop())
    currentStream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  cameraActive.value = false
}

// 拍照检测
async function doCapture() {
  if (!cameraActive.value || !videoRef.value || !canvasRef.value) {
    alert('请先开启摄像头')
    return
  }

  detecting.value = true
  latestResult.value = null
  vlmResult.value = null  // 清除之前的 AI 分析结果

  try {
    // 从视频捕获帧
    const video = videoRef.value
    const canvas = canvasRef.value
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // 缓存 base64 供 VLM 复用
    lastCapturedBase64 = canvas.toDataURL('image/jpeg', 0.85)
    capturedImageSrc.value = lastCapturedBase64

    // 停止摄像头，切换到显示拍摄照片模式
    stopCamera()
    showCaptured.value = true

    // 转为 Blob
    const blob = await new Promise(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', 0.9)
    })

    // 上传检测
    const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' })
    const result = await detectFromImage(file, selectedZone.value, 0.5)
    latestResult.value = result

    // 刷新历史
    await loadHistory()
  } catch (e) {
    alert('模型识别失败：' + e.message)
  } finally {
    detecting.value = false
  }
}

// 重新拍照：清除拍摄状态，重新开启摄像头
async function retakePhoto() {
  showCaptured.value = false
  capturedImageSrc.value = ''
  latestResult.value = null
  vlmResult.value = null
  lastCapturedBase64 = null
  await startCamera()
}

// 大模型 AI 分析（复用 YOLO 拍照时缓存的图片）
async function doVlmAnalyze() {
  if (!lastCapturedBase64) {
    alert('请先点击"拍照检测"获取图片')
    return
  }

  vlmAnalyzing.value = true
  vlmResult.value = null

  try {
    const resp = await analyzeBase64(lastCapturedBase64)
    if (resp.ok && resp.result) {
      vlmResult.value = resp.result

    } else {
      alert('分析失败：未获取到结果')
    }
  } catch (e) {
    console.error('大模型分析失败:', e)
    alert('AI 分析失败: ' + e.message)
  } finally {
    vlmAnalyzing.value = false
  }
}

// VLM 成熟度等级样式
const vlmLevelClass = computed(() => {
  const level = vlmResult.value?.maturity_level || ''
  if (level.includes('成熟') && !level.includes('未') && !level.includes('半')) return 'ripe'
  if (level.includes('半成熟')) return 'half'
  return 'unripe'
})

// 上传图片检测
async function detectFromImage(file, zone = 'A', conf_threshold = 0.5) {
  if (!albumId.value) throw new Error('请先选择照片集')
  const photo = await uploadAlbumPhoto(albumId.value, file, new Date().toISOString())
  const record = await runDetection({ photo_id: photo.id, task: 'maturity', threshold: conf_threshold })
  return asMaturityResult(record, zone)
}

function asMaturityResult(record, zone = '') {
  const counts = Object.fromEntries(Object.entries(record.data.counts || {}).map(([key, value]) => [key.toLowerCase().replaceAll('_', '-').replaceAll(' ', '-'), value]))
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0)
  return { id: record.id, zone, evidence: record, created_at: record.created_at,
    total_count: total, ripe_count: counts.ripe || 0, half_ripe_count: counts['half-ripe'] || 0,
    unripe_count: counts.unripe || 0, maturity_ratio: total ? Math.round((counts.ripe || 0) / total * 100) : 0,
    confidence_threshold: record.data.threshold, recommendation: '仅代表本张照片可见果实，采摘前需现场复核。' }
}

// 加载历史
async function loadHistory() {
  try {
    historyRecords.value = albumId.value ? (await fieldRecords('detection', albumId.value))
      .filter(r => r.status === 'ready' && r.data.task === 'maturity').map(r => asMaturityResult(r)) : []
  } catch (e) {
    console.error('加载历史失败:', e)
  }
}

// 汇总卡片
const summary = computed(() => {
  const r = latestResult.value
  const v = vlmResult.value

  // 如果有 VLM 结果，使用 VLM 的真实数据
  if (v && v.total_count > 0) {
    return [
      { label: '本次识别总数', value: `${v.total_count} 颗`, note: '大模型识别', icon: Sprout },
      { label: '平均成熟度', value: `${v.maturity_ratio}%`, note: `AI: ${v.maturity_level}`, icon: Gauge },
      { label: '可见成熟果', value: `${v.ripe_count} 颗`, note: '大模型参考，非自训模型结果', icon: Timer },
      { label: '检测状态', value: 'AI 完成', note: 'Qwen3-VL-Plus', icon: Sparkles }
    ]
  }

  // YOLO 检测结果
  if (r && r.total_count > 0) {
    return [
      { label: '本次识别总数', value: `${r.total_count} 颗`, note: `${getZoneName(r.zone)} 检测`, icon: Sprout },
      { label: '平均成熟度', value: `${r.maturity_ratio}%`, note: r.maturity_ratio >= harvestThreshold.value ? '达到采摘阈值' : '未达阈值', icon: Gauge },
      { label: '可见成熟果', value: `${r.ripe_count} 颗`, note: '未称重，不推算重量', icon: Timer },
      { label: '检测状态', value: '完成', note: `阈值 ${r.confidence_threshold}`, icon: ScanLine }
    ]
  }

  // 默认状态
  return [
    { label: '本次识别总数', value: '—', note: '等待检测', icon: Sprout },
    { label: '平均成熟度', value: '—', note: '等待检测', icon: Gauge },
    { label: '建议采摘量', value: '—', note: '等待检测', icon: Timer },
    { label: '检测状态', value: '就绪', note: cameraReady.value ? '摄像头已连接' : '摄像头未连接', icon: ScanLine }
  ]
})

// 采摘建议
const displayAdvice = computed(() => {
  const r = latestResult.value
  const items = []

  if (r) {
    const zn = getZoneName(r.zone)
    if (r.maturity_ratio >= harvestThreshold.value) {
      items.push({ level: 'ready', levelText: '执行', title: `${zn} 成熟度 ${r.maturity_ratio}%`, desc: '已达采摘阈值，建议立即采摘。' })
    } else if (r.maturity_ratio >= harvestThreshold.value - 10) {
      items.push({ level: 'watch', levelText: '观察', title: `${zn} 接近采摘窗口`, desc: `成熟度 ${r.maturity_ratio}%，建议明天再次检测。` })
    } else {
      items.push({ level: 'normal', levelText: '正常', title: `${zn} 未达采摘阈值`, desc: '继续观察，维持当前策略。' })
    }
  }

  const latestZone = latestResult.value?.zone
  for (const z of zones) {
    if (z.id === latestZone) continue
    const zoneRecords = historyRecords.value.filter(r => r.zone === z.id)
    if (zoneRecords.length) {
      const latest = zoneRecords[0]
      if (latest.maturity_ratio >= harvestThreshold.value) {
        items.push({ level: 'ready', levelText: '执行', title: `${z.name} 成熟度 ${latest.maturity_ratio}%`, desc: '已达采摘阈值。' })
      } else {
        items.push({ level: 'normal', levelText: '正常', title: `${z.name} 成熟度 ${latest.maturity_ratio}%`, desc: '继续观察。' })
      }
    } else {
      items.push({ level: 'normal', levelText: '待检测', title: `${z.name} 暂无数据`, desc: '请使用摄像头检测该区域。' })
    }
  }

  return items
})

// 初始化
onMounted(async () => {
  try {
    let page = 1, result
    do { result = await listAlbums(page++); albums.value.push(...result.items) } while (albums.value.length < result.total)
  } catch (e) { alert('照片集加载失败：' + e.message) }
  // 加载摄像头列表（用于显示）
  try {
    const cameras = await listCameras()
    availableCameras.value = cameras || []
    if (cameras.length > 0) {
      selectedCameraId.value = cameras[0].id
      cameraReady.value = true
    }
  } catch {
    // 即使获取列表失败，也可以使用浏览器摄像头
    availableCameras.value = [{ id: 0, name: '默认摄像头' }]
    selectedCameraId.value = 0
  }
  // 加载历史
  await loadHistory()
})

// 清理
onUnmounted(() => {
  stopCamera()
})
</script>

<style scoped lang="less">
.maturity-center {
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
  font-size: 12px;
  font-weight: 600;

  &.online {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
  &.offline {
    background: var(--color-error-50);
    color: var(--color-error-700);
  }
}

.maturity-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

/* 检测操作栏 */
.detect-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.action-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px;
}

.action-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.zone-selector, .camera-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--gray-600);

  button {
    min-width: 48px;
    height: 28px;
    padding: 0 10px;
    border: 1px solid var(--gray-200);
    border-radius: 6px;
    background: var(--gray-0);
    color: var(--gray-700);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover { border-color: var(--main-color); color: var(--main-color); }
    &.active {
      border-color: var(--main-color);
      background: var(--main-50);
      color: var(--main-color);
      font-weight: 600;
    }
  }
}

.camera-selector select {
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  cursor: pointer;
  outline: none;

  &:focus { border-color: var(--main-color); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.preview-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--main-color);
    color: var(--main-color);
  }

  &.active {
    border-color: var(--color-success-500);
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
}

.capture-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) { opacity: 0.9; }
  &:disabled {
    background: var(--gray-200);
    color: var(--gray-500);
    cursor: not-allowed;
  }
}

.retake-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  height: 36px;
  padding: 0 16px;
  border: 2px solid var(--main-color);
  border-radius: 8px;
  background: var(--gray-0);
  color: var(--main-color);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: var(--main-50);
  }
  &:disabled {
    border-color: var(--gray-200);
    color: var(--gray-400);
    cursor: not-allowed;
  }
}

/* 预览+结果区域 */
.preview-result-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-height: 400px;
}

.camera-panel, .result-panel {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--gray-150);
}

.result-time {
  color: var(--gray-500);
  font-size: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--main-color);

  h3 {
    margin: 0;
    color: var(--gray-1000);
    font-size: 15px;
    font-weight: 650;
  }
}

/* 视频容器 */
.video-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  min-height: 300px;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.captured-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.retake-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--main-color);
    color: var(--main-color);
  }
}

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--gray-400);

  p {
    margin: 0;
    font-size: 14px;
  }
}

/* 检测结果 */
.detecting-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--main-color);

  p {
    margin: 0;
    font-size: 14px;
  }
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--main-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.result-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 14px;
}

.vlm-only-result {
  align-items: center;
}

.vlm-result-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  background: var(--color-accent-50);
  color: var(--color-accent-700);
  font-size: 12px;
  font-weight: 600;
}

.annotated-image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-10);
  border-radius: 6px;
  overflow: hidden;
  min-height: 200px;
}

.annotated-image {
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
  border-radius: 6px;
  background: var(--gray-10);

  &.ripe { background: var(--color-success-50); }
  &.half { background: var(--color-warning-50); }
  &.unripe { background: var(--color-info-50); }
}

.stat-label {
  color: var(--gray-600);
  font-size: 11px;
}

.stat-item strong {
  color: var(--gray-1000);
  font-size: 20px;
  font-weight: 700;
}

.ripe strong { color: var(--color-success-700); }
.half strong { color: var(--color-warning-900); }
.unripe strong { color: var(--color-info-700); }

/* 成熟度进度条 */
.maturity-bar {
  margin-top: 4px;
}

.bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--gray-600);

  strong {
    font-size: 15px;
    color: var(--gray-1000);
    &.ready { color: var(--color-success-700); }
  }
}

.bar-track {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: var(--gray-150);
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--color-info-500);
  transition: width 0.5s ease;
  &.ready { background: var(--color-success-500); }
}

.bar-threshold {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 14px;
  background: var(--color-error-500);
  border-radius: 1px;
}

.recommendation {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--main-50);
  color: var(--gray-800);
  font-size: 13px;
  line-height: 20px;
}

/* AI 增强分析按钮（YOLO 成功后） */
.vlm-enhance-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  justify-content: center;
  height: 36px;
  padding: 0 16px;
  border: 2px solid var(--color-accent-500);
  border-radius: 8px;
  background: var(--color-accent-50);
  color: var(--color-accent-700);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: var(--color-accent-100);
  }
  &:disabled {
    border-color: var(--gray-200);
    background: var(--gray-10);
    color: var(--gray-400);
    cursor: not-allowed;
  }
}

/* YOLO 失败时的大模型回退区域 */
.vlm-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  background: var(--color-warning-50);
}

.fallback-hint {
  margin: 0;
  color: var(--color-warning-900);
  font-size: 13px;
}

.vlm-fallback-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 160px;
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--color-accent-500);
  color: var(--gray-0);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
  &:disabled {
    background: var(--gray-200);
    color: var(--gray-500);
    cursor: not-allowed;
  }
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--gray-400);

  p {
    margin: 0;
    font-size: 14px;
  }
}

/* 汇总卡片 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 90px;
  padding: 14px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
  color: var(--main-color);

  span {
    display: block;
    color: var(--gray-600);
    font-size: 12px;
  }

  strong {
    display: block;
    margin-top: 4px;
    color: var(--gray-1000);
    font-size: 22px;
    font-weight: 700;
  }

  p {
    margin: 4px 0 0;
    color: var(--gray-600);
    font-size: 12px;
  }
}

/* 历史记录 */
.records-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(300px, 0.75fr);
  gap: 16px;
}

.scan-panel, .advice-panel {
  padding: 18px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.scan-list, .advice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.scan-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 100px 72px;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-10);
}

.scan-main strong {
  display: block;
  color: var(--gray-1000);
  font-size: 13px;
  font-weight: 650;
}

.scan-main span {
  display: block;
  color: var(--gray-500);
  font-size: 12px;
}

.scan-numbers {
  text-align: right;

  span {
    display: block;
    color: var(--gray-500);
    font-size: 11px;
  }

  strong {
    color: var(--gray-1000);
    font-size: 18px;
    font-weight: 700;
    &.ready { color: var(--color-success-700); }
  }
}

.scan-advice {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  background: var(--color-info-50);
  color: var(--color-info-700);
  font-size: 12px;
  font-weight: 600;
  &.ready {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-10);
}

.advice-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;

  &.ready {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
  &.watch {
    background: var(--color-warning-50);
    color: var(--color-warning-900);
  }
  &.normal {
    background: var(--color-info-50);
    color: var(--color-info-700);
  }
}

.advice-item strong {
  display: block;
  color: var(--gray-1000);
  font-size: 13px;
  font-weight: 650;
}

.advice-item p {
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: 12px;
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  color: var(--gray-400);

  p {
    margin: 0;
    font-size: 14px;
  }
}

/* 大模型分析区域 */
.vlm-section {
  padding: 18px;
  border: 1px solid var(--color-accent-100);
  border-radius: 8px;
  background: var(--gray-0);
}

.vlm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.vlm-badge {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 12px;
  background: var(--color-accent-50);
  color: var(--color-accent-700);
  font-size: 12px;
  font-weight: 600;
}

.vlm-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 20px;
  color: var(--color-accent-700);

  p {
    margin: 0;
    font-size: 14px;
  }
}

.vlm-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.vlm-card {
  padding: 16px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.vlm-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--gray-700);
  font-size: 13px;
  font-weight: 600;

  svg {
    color: var(--color-accent-500);
  }
}

.vlm-card-body {
  p {
    margin: 0;
    color: var(--gray-800);
    font-size: 13px;
    line-height: 1.6;
  }
}

.vlm-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 650;
  margin-bottom: 8px;

  &.ripe {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
  &.half {
    background: var(--color-warning-50);
    color: var(--color-warning-900);
  }
  &.unripe {
    background: var(--color-info-50);
    color: var(--color-info-700);
  }
}

.vlm-summary {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--color-accent-50);
  color: var(--gray-800);
  font-size: 13px;
  line-height: 1.6;

  svg {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--color-accent-500);
  }
}

@media (max-width: 1180px) {
  .preview-result-section {
    grid-template-columns: 1fr;
  }
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .records-layout {
    grid-template-columns: 1fr;
  }
  .vlm-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .detect-action-bar {
    flex-direction: column;
    gap: 12px;
  }
  .action-left, .action-right {
    width: 100%;
    justify-content: center;
  }
  .summary-grid, .scan-row {
    grid-template-columns: 1fr;
  }
  .scan-numbers {
    text-align: left;
  }
}
</style>
