<template>
  <div class="trace-query-page">
    <header class="site-header">
      <div class="header-inner">
        <div>
          <p class="site-kicker">番茄产品质量安全追溯查询</p>
          <h1>番茄消费者查询</h1>
        </div>
        <div class="header-stamp">公开查询</div>
      </div>
    </header>

    <main class="page-body">
      <section class="notice-box">
        <strong>查询说明：</strong>
        请扫描包装上的二维码，或输入标签下方的追溯码、生产批次号。查询结果仅展示该批次已登记的生产、采摘、检测和包装信息。
      </section>

      <section class="query-panel">
        <div class="panel-title">
          <span>追溯信息查询</span>
          <small>Traceability Query</small>
        </div>

        <div class="query-table">
          <label for="trace-code">追溯码/批次号</label>
          <div class="query-control">
            <input
              id="trace-code"
              v-model="queryCode"
              placeholder="例：TM202608240001 或 BATCH-2026-001"
              @keyup.enter="handleQuery"
            />
            <button type="button" class="secondary-btn" @click="toggleScanner">
              <ScanLine :size="15" />
              {{ showScanner ? '关闭扫码' : '扫码' }}
            </button>
            <button type="button" class="primary-btn" @click="handleQuery" :disabled="!queryCode.trim() || loading">
              <Search :size="15" />
              查询
            </button>
          </div>
        </div>

        <Transition name="fold">
          <div v-if="showScanner" class="scanner-section">
            <div id="qr-reader" class="scanner-box"></div>
            <p>请允许浏览器访问摄像头，并将二维码置于取景框内。</p>
          </div>
        </Transition>
      </section>

      <div v-if="loading" class="status-line">
        <span class="loading-dot"></span>
        正在查询，请稍候...
      </div>

      <div v-if="error" class="error-line">
        <AlertCircle :size="16" />
        {{ error }}
      </div>

      <section v-if="report" class="result-panel">
        <div class="result-title">
          <div>
            <h2>查询结果</h2>
            <p>追溯码：{{ report.trace_code || queryCode }}</p>
          </div>
          <span class="verify-badge" :class="{ pass: isVerified, fail: !isVerified }">
            {{ isVerified ? '校验通过' : '校验异常' }}
          </span>
        </div>

        <table class="info-table">
          <tbody>
            <tr>
              <th>产品名称</th>
              <td>温室番茄</td>
              <th>批次编号</th>
              <td class="mono">{{ report.batch_code || '-' }}</td>
            </tr>
            <tr>
              <th>品种</th>
              <td>{{ report.seed_variety || '-' }}</td>
              <th>生产地块</th>
              <td>{{ joinText(report.plot_name, report.plot_location) }}</td>
            </tr>
            <tr>
              <th>种子供应商</th>
              <td>{{ report.seed_supplier || '-' }}</td>
              <th>种植日期</th>
              <td>{{ report.plant_date || '-' }}</td>
            </tr>
            <tr>
              <th>采摘日期</th>
              <td>{{ report.harvest_date || '-' }}</td>
              <th>采摘等级</th>
              <td>{{ report.harvest_grade || '-' }}</td>
            </tr>
            <tr>
              <th>采摘产量</th>
              <td>{{ formatKg(report.harvest_yield_kg) }}</td>
              <th>包装批号</th>
              <td class="mono">{{ report.package_info?.lot_number || '-' }}</td>
            </tr>
            <tr>
              <th>包装日期</th>
              <td>{{ report.package_info?.package_date || '-' }}</td>
              <th>包装规格/重量</th>
              <td>{{ packageText }}</td>
            </tr>
          </tbody>
        </table>

        <div class="section-block">
          <h3>质量检测信息</h3>
          <table class="list-table">
            <thead>
              <tr>
                <th>检测项目</th>
                <th>检测结果</th>
                <th>检测机构</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(insp, index) in report.inspections" :key="index">
                <td>{{ insp.type || insp.inspection_type || '-' }}</td>
                <td>
                  <span class="plain-tag" :class="{ pass: insp.result === '合格' }">{{ insp.result || '-' }}</span>
                </td>
                <td>{{ insp.lab || insp.lab_name || '-' }}</td>
              </tr>
              <tr v-if="!hasInspection">
                <td colspan="3" class="empty-cell">暂无检测记录</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section-block">
          <h3>生产过程记录</h3>
          <table class="list-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>操作类型</th>
                <th>记录内容</th>
                <th>使用物料</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(act, index) in report.activities_detail" :key="index">
                <td>{{ act.datetime || '-' }}</td>
                <td>{{ act.type || '-' }}</td>
                <td>{{ act.detail || '-' }}</td>
                <td>{{ act.materials || '-' }}</td>
              </tr>
              <tr v-if="!hasActivities">
                <td colspan="4" class="empty-cell">暂无生产过程记录</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasPhotos" class="section-block">
          <h3>现场照片</h3>
          <div class="photo-list">
            <figure v-for="(photo, index) in photoItems" :key="index">
              <img :src="photo.file_path" :alt="photo.label" />
              <figcaption>{{ photo.label }}</figcaption>
            </figure>
          </div>
        </div>

        <div class="verify-panel">
          <div>
            <span>区块链验证</span>
            <strong>{{ report.blockchain_verified ? '已上链' : '未上链' }}</strong>
          </div>
          <div>
            <span>数据完整性</span>
            <strong>{{ report.hash_verified ? '完整' : '异常' }}</strong>
          </div>
          <div>
            <span>篡改检测</span>
            <strong>{{ report.tamper_detected ? '发现异常' : '未发现异常' }}</strong>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, nextTick } from 'vue'
import { Search, ScanLine, AlertCircle } from 'lucide-vue-next'
import { traceQueryPublic, traceByBatchCodePublic } from '@/apis/trace_api'

const queryCode = ref('')
const report = ref(null)
const loading = ref(false)
const error = ref('')
const showScanner = ref(false)
let html5QrScanner = null

const isVerified = computed(() =>
  report.value && report.value.hash_verified && !report.value.tamper_detected
)
const hasInspection = computed(() => report.value?.inspections?.length > 0)
const hasActivities = computed(() => report.value?.activities_detail?.length > 0)
const photoItems = computed(() => [
  ...(report.value?.growth_photos || []).map((photo) => ({ ...photo, label: '生长记录' })),
  ...(report.value?.harvest_photos || []).map((photo) => ({ ...photo, label: '采摘记录' }))
])
const hasPhotos = computed(() => photoItems.value.length > 0)
const packageText = computed(() => {
  const spec = report.value?.package_info?.package_spec
  const weight = formatKg(report.value?.package_info?.weight_kg)
  return [spec, weight !== '-' ? weight : ''].filter(Boolean).join(' / ') || '-'
})

function joinText(...parts) {
  return parts.filter(Boolean).join(' / ') || '-'
}

function formatKg(value) {
  return value ? `${value} kg` : '-'
}

async function handleQuery() {
  const code = queryCode.value.trim()
  if (!code) return
  loading.value = true
  error.value = ''
  report.value = null

  try {
    let res
    if (code.startsWith('TM')) {
      res = await traceQueryPublic(code)
    } else {
      res = await traceByBatchCodePublic(code)
    }
    if (res.ok) {
      report.value = res.report
    } else {
      error.value = res.detail || '未查询到对应追溯信息'
    }
  } catch (e) {
    error.value = e.message || '溯源码无效或已失效'
  } finally {
    loading.value = false
  }
}

async function toggleScanner() {
  if (showScanner.value) {
    stopScanner()
    return
  }
  showScanner.value = true
  await nextTick()
  startScanner()
}

function startScanner() {
  import('html5-qrcode').then(({ Html5Qrcode }) => {
    html5QrScanner = new Html5Qrcode('qr-reader')
    html5QrScanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        queryCode.value = decodedText
        stopScanner()
        handleQuery()
      },
      () => {}
    ).catch(() => {
      error.value = '无法访问摄像头，请检查浏览器权限设置'
      showScanner.value = false
    })
  })
}

function stopScanner() {
  if (html5QrScanner) {
    html5QrScanner.stop().then(() => {
      html5QrScanner.clear()
      html5QrScanner = null
    }).catch(() => {})
  }
  showScanner.value = false
}

onBeforeUnmount(() => {
  stopScanner()
})
</script>

<style lang="less" scoped>
.trace-query-page {
  min-height: 100vh;
  background: #f1f1ec;
  color: #222;
  font-family: Arial, "Microsoft YaHei", sans-serif;
}

.site-header {
  background: #2f6f3f;
  border-bottom: 4px solid #d7b35a;
  color: #fff;
}

.header-inner {
  max-width: 960px;
  margin: 0 auto;
  padding: 22px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.site-kicker {
  margin: 0 0 6px;
  font-size: 13px;
  color: #dcebdd;
}

h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
}

.header-stamp {
  flex-shrink: 0;
  padding: 7px 12px;
  border: 1px solid rgba(255, 255, 255, .6);
  font-size: 13px;
}

.page-body {
  max-width: 960px;
  margin: 0 auto;
  padding: 18px 20px 42px;
}

.notice-box,
.query-panel,
.result-panel {
  background: #fff;
  border: 1px solid #cfcfc7;
}

.notice-box {
  padding: 12px 14px;
  margin-bottom: 14px;
  color: #444;
  font-size: 14px;
  line-height: 1.7;
}

.query-panel {
  margin-bottom: 14px;
}

.panel-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #cfcfc7;
  background: #f7f7f2;
  color: #1f5f35;
  font-weight: 700;
}

.panel-title small {
  color: #777;
  font-weight: 400;
}

.query-table {
  display: grid;
  grid-template-columns: 150px 1fr;
  border-bottom: 1px solid #e2e2dc;
}

.query-table label {
  padding: 18px 14px;
  background: #f7f7f2;
  border-right: 1px solid #e2e2dc;
  font-size: 14px;
  font-weight: 700;
}

.query-control {
  display: flex;
  gap: 8px;
  padding: 12px;
}

.query-control input {
  flex: 1;
  min-width: 0;
  height: 38px;
  padding: 0 10px;
  border: 1px solid #aaa;
  border-radius: 2px;
  font-size: 14px;
}

.primary-btn,
.secondary-btn {
  height: 38px;
  border-radius: 2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 16px;
  font-size: 14px;
  cursor: pointer;
}

.primary-btn {
  border: 1px solid #235f34;
  background: #2f6f3f;
  color: #fff;
}

.primary-btn:disabled {
  opacity: .55;
  cursor: not-allowed;
}

.secondary-btn {
  border: 1px solid #aaa;
  background: #f5f5f0;
  color: #333;
}

.scanner-section {
  padding: 14px;
  border-top: 1px solid #e2e2dc;
  text-align: center;
}

.scanner-box {
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
  border: 1px solid #bbb;
}

.scanner-section p {
  margin: 8px 0 0;
  color: #666;
  font-size: 13px;
}

.status-line,
.error-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  margin-bottom: 14px;
  border: 1px solid #cfcfc7;
  background: #fff;
  font-size: 14px;
}

.error-line {
  border-color: #d8a5a0;
  background: #fff6f4;
  color: #a22f25;
}

.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2f6f3f;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  50% { opacity: .35; }
}

.result-panel {
  padding-bottom: 16px;
}

.result-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-bottom: 1px solid #cfcfc7;
  background: #f7f7f2;
}

.result-title h2 {
  margin: 0 0 4px;
  font-size: 20px;
}

.result-title p {
  margin: 0;
  color: #555;
  font-size: 13px;
}

.verify-badge {
  border: 1px solid #999;
  padding: 5px 10px;
  font-size: 13px;
  font-weight: 700;
  background: #eee;
}

.verify-badge.pass {
  border-color: #2f6f3f;
  background: #e8f3e9;
  color: #1f5f35;
}

.verify-badge.fail {
  border-color: #ba4b42;
  background: #fff0ee;
  color: #9b2f27;
}

.info-table,
.list-table {
  width: calc(100% - 28px);
  margin: 14px;
  border-collapse: collapse;
  background: #fff;
}

.info-table th,
.info-table td,
.list-table th,
.list-table td {
  border: 1px solid #cfcfc7;
  padding: 9px 10px;
  font-size: 14px;
  line-height: 1.45;
  text-align: left;
}

.info-table th,
.list-table th {
  background: #f7f7f2;
  color: #333;
  font-weight: 700;
}

.info-table th {
  width: 120px;
}

.mono {
  font-family: "SF Mono", Consolas, monospace;
}

.section-block {
  margin-top: 12px;
}

.section-block h3 {
  margin: 0 14px;
  padding: 9px 10px;
  border: 1px solid #cfcfc7;
  border-bottom: none;
  background: #eef3ed;
  color: #1f5f35;
  font-size: 15px;
}

.section-block .list-table {
  margin-top: 0;
}

.plain-tag {
  display: inline-block;
  min-width: 44px;
  padding: 2px 8px;
  border: 1px solid #c9958f;
  background: #fff4f2;
  color: #9b2f27;
  text-align: center;
}

.plain-tag.pass {
  border-color: #82b184;
  background: #edf7ee;
  color: #1f6b36;
}

.empty-cell {
  color: #777;
  text-align: center;
}

.photo-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
  margin: 0 14px 14px;
  padding: 12px;
  border: 1px solid #cfcfc7;
}

.photo-list figure {
  margin: 0;
  border: 1px solid #d7d7d0;
  background: #fafafa;
}

.photo-list img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.photo-list figcaption {
  padding: 6px 8px;
  color: #555;
  font-size: 13px;
}

.verify-panel {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  margin: 16px 14px 0;
  border: 1px solid #cfcfc7;
}

.verify-panel div {
  padding: 10px 12px;
  border-right: 1px solid #cfcfc7;
}

.verify-panel div:last-child {
  border-right: none;
}

.verify-panel span {
  display: block;
  margin-bottom: 4px;
  color: #666;
  font-size: 13px;
}

.verify-panel strong {
  color: #222;
  font-size: 15px;
}

.fold-enter-active,
.fold-leave-active {
  transition: opacity .18s ease;
}

.fold-enter-from,
.fold-leave-to {
  opacity: 0;
}

@media (max-width: 720px) {
  .header-inner,
  .result-title,
  .query-control {
    align-items: stretch;
    flex-direction: column;
  }

  .query-table {
    grid-template-columns: 1fr;
  }

  .query-table label {
    border-right: none;
    border-bottom: 1px solid #e2e2dc;
    padding: 11px 12px;
  }

  .primary-btn,
  .secondary-btn {
    width: 100%;
  }

  .info-table,
  .info-table tbody,
  .info-table tr,
  .info-table th,
  .info-table td {
    display: block;
    width: auto;
  }

  .info-table th {
    border-bottom: none;
  }

  .info-table td {
    border-top: none;
  }

  .list-table {
    display: block;
    overflow-x: auto;
  }

  .verify-panel {
    grid-template-columns: 1fr;
  }

  .verify-panel div {
    border-right: none;
    border-bottom: 1px solid #cfcfc7;
  }

  .verify-panel div:last-child {
    border-bottom: none;
  }
}
</style>
