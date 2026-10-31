<template>
  <div class="traceability layout-container">
    <PageHeader title="产品溯源" :show-border="true">
      <template #info>
        <span class="status-pill" v-if="stats">
          <Fingerprint :size="14" />
          {{ stats.total_batches }} 个批次
        </span>
      </template>
    </PageHeader>

    <main class="trace-content">
      <!-- 统计卡片 -->
      <section class="stats-grid" v-if="stats">
        <article class="stat-card" v-for="item in statItems" :key="item.label">
          <component :is="item.icon" :size="20" />
          <div>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </article>
      </section>

      <!-- 标签页导航 -->
      <section class="tabs-nav">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" :size="16" />
          {{ tab.label }}
        </button>
      </section>

      <!-- 标签页内容 -->
      <section class="tab-content">
        <!-- 仪表盘 -->
        <div v-if="activeTab === 'dashboard'" class="tab-panel">
          <div class="dashboard-grid">
            <article class="blockchain-card">
              <div class="card-header">
                <Shield :size="16" />
                <h3>区块链状态</h3>
              </div>
              <div class="blockchain-info" v-if="stats">
                <div class="bc-status" :class="{ valid: stats.blockchain_valid }">
                  <component :is="stats.blockchain_valid ? CheckCircle : AlertCircle" :size="20" />
                  <span>{{ stats.blockchain_valid ? '链完整' : '链异常' }}</span>
                </div>
                <div class="bc-stat">
                  <span>区块数量</span>
                  <strong>{{ stats.blockchain_blocks }}</strong>
                </div>
              </div>
            </article>

            <article class="trace-query-card">
              <div class="card-header">
                <Search :size="16" />
                <h3>溯源查询</h3>
                <button class="consumer-link-btn" @click="openConsumerPage">
                  <ExternalLink :size="14" />
                  <span>消费者查询页</span>
                </button>
              </div>
              <div class="query-form">
                <input
                  v-model="queryCode"
                  class="query-input"
                  placeholder="输入溯源码或批次编号"
                  @keyup.enter="handleQuery"
                />
                <button class="query-btn" @click="handleQuery" :disabled="!queryCode.trim()">
                  <Search :size="14" />
                  查询
                </button>
              </div>
              <div v-if="queryResult" class="query-result">
                <!-- 篡改警告 -->
                <div v-if="queryResult.tamper_detected" class="tamper-alert">
                  <AlertCircle :size="16" />
                  <span>数据完整性校验失败：检测到数据可能被篡改</span>
                </div>
                <div class="result-header">
                  <strong>{{ queryResult.batch_code }}</strong>
                  <div class="result-badges">
                    <span class="result-badge" :class="{ verified: queryResult.blockchain_verified }">
                      {{ queryResult.blockchain_verified ? '已上链' : '未上链' }}
                    </span>
                    <span class="result-badge" :class="{ verified: queryResult.hash_verified, tampered: !queryResult.hash_verified }">
                      {{ queryResult.hash_verified ? '数据完整' : '数据异常' }}
                    </span>
                  </div>
                </div>
                <div class="result-info">
                  <div class="info-row">
                    <span>品种</span>
                    <strong>{{ queryResult.seed_variety }}</strong>
                  </div>
                  <div class="info-row">
                    <span>地块</span>
                    <strong>{{ queryResult.plot_name }}</strong>
                  </div>
                  <div class="info-row">
                    <span>种植日期</span>
                    <strong>{{ queryResult.plant_date }}</strong>
                  </div>
                  <div class="info-row" v-if="queryResult.harvest_date">
                    <span>采摘日期</span>
                    <strong>{{ queryResult.harvest_date }}</strong>
                  </div>
                  <div class="info-row" v-if="queryResult.harvest_grade">
                    <span>等级</span>
                    <strong>{{ queryResult.harvest_grade }}</strong>
                  </div>
                </div>
                <div v-if="queryResult.package_info" class="result-package">
                  <span>包装信息</span>
                  <strong>{{ queryResult.package_info.lot_number }} · {{ queryResult.package_info.weight_kg }}kg</strong>
                </div>
              </div>
            </article>

            <!-- 二维码生成 -->
            <article class="qr-card">
              <div class="card-header">
                <QrCode :size="16" />
                <h3>二维码生成</h3>
              </div>
              <div class="qr-form">
                <input
                  v-model="qrGenCode"
                  class="query-input"
                  placeholder="输入溯源码生成二维码"
                />
                <button class="query-btn" @click="handleGenerateQR" :disabled="!qrGenCode.trim()">
                  生成
                </button>
              </div>
              <div v-if="generatedQR" class="qr-preview">
                <img :src="generatedQR" alt="生成的二维码" />
                <p>{{ qrGenCode }}</p>
                <button class="download-btn" @click="downloadQR">下载二维码</button>
              </div>
            </article>

            <!-- 二维码识别 -->
            <article class="qr-card">
              <div class="card-header">
                <ScanLine :size="16" />
                <h3>二维码识别</h3>
              </div>
              <div class="qr-scan">
                <div
                  class="upload-area"
                  @click="triggerQRUpload"
                  @dragover.prevent
                  @drop.prevent="handleQRDrop"
                >
                  <Upload :size="24" />
                  <span>点击或拖拽图片到此处</span>
                  <span class="upload-hint">支持 JPG、PNG 等图片格式</span>
                </div>
                <input
                  ref="qrFileInput"
                  type="file"
                  accept="image/*"
                  style="display: none"
                  @change="handleQRFileSelect"
                />
                <div v-if="scanResult" class="scan-result">
                  <div class="scan-status" :class="{ success: scanResult.ok }">
                    <component :is="scanResult.ok ? CheckCircle : AlertCircle" :size="16" />
                    <span>{{ scanResult.ok ? '识别成功' : '识别失败' }}</span>
                  </div>
                  <div v-if="scanResult.ok" class="scan-data">
                    <span>识别内容：</span>
                    <strong>{{ scanResult.decoded_data }}</strong>
                    <button class="query-btn" @click="queryCode = scanResult.decoded_data; handleQuery()">
                      查询溯源
                    </button>
                  </div>
                  <div v-else class="scan-error">
                    {{ scanResult.detail }}
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>

        <!-- 地块管理 -->
        <div v-if="activeTab === 'plots'" class="tab-panel">
          <div class="panel-header">
            <h3>地块列表</h3>
            <button class="add-btn" @click="showPlotForm = true">
              <Plus :size="14" />
              新增地块
            </button>
          </div>
          <div class="data-table">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>名称</th>
                  <th>位置</th>
                  <th>面积（亩）</th>
                  <th>土壤类型</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="plot in plots" :key="plot.id">
                  <td>{{ plot.id }}</td>
                  <td>{{ plot.name }}</td>
                  <td>{{ plot.location }}</td>
                  <td>{{ plot.area_mu || '-' }}</td>
                  <td>{{ plot.soil_type || '-' }}</td>
                  <td>
                    <button class="action-btn" @click="handleDeletePlot(plot.id)">删除</button>
                  </td>
                </tr>
                <tr v-if="!plots.length">
                  <td colspan="6" class="empty-row">暂无地块数据</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 新增地块表单 -->
          <div v-if="showPlotForm" class="modal-overlay" @click.self="showPlotForm = false">
            <div class="modal-content">
              <h3>新增地块</h3>
              <div class="form-group">
                <label>地块名称</label>
                <input v-model="plotForm.name" placeholder="如：3号大棚" />
              </div>
              <div class="form-group">
                <label>位置描述</label>
                <input v-model="plotForm.location" placeholder="如：温室区东侧" />
              </div>
              <div class="form-group">
                <label>面积（亩）</label>
                <input v-model.number="plotForm.area_mu" type="number" placeholder="可选" />
              </div>
              <div class="form-group">
                <label>土壤类型</label>
                <input v-model="plotForm.soil_type" placeholder="如：沙壤土" />
              </div>
              <div class="form-actions">
                <button class="cancel-btn" @click="showPlotForm = false">取消</button>
                <button class="submit-btn" @click="handleCreatePlot">确定</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 种子管理 -->
        <div v-if="activeTab === 'seeds'" class="tab-panel">
          <div class="panel-header">
            <h3>种子列表</h3>
            <button class="add-btn" @click="showSeedForm = true">
              <Plus :size="14" />
              新增种子
            </button>
          </div>
          <div class="data-table">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>品种</th>
                  <th>供应商</th>
                  <th>批次号</th>
                  <th>认证信息</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="seed in seeds" :key="seed.id">
                  <td>{{ seed.id }}</td>
                  <td>{{ seed.variety }}</td>
                  <td>{{ seed.supplier || '-' }}</td>
                  <td>{{ seed.batch_no || '-' }}</td>
                  <td>{{ seed.cert_info || '-' }}</td>
                  <td>
                    <button class="action-btn" @click="handleDeleteSeed(seed.id)">删除</button>
                  </td>
                </tr>
                <tr v-if="!seeds.length">
                  <td colspan="6" class="empty-row">暂无种子数据</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 新增种子表单 -->
          <div v-if="showSeedForm" class="modal-overlay" @click.self="showSeedForm = false">
            <div class="modal-content">
              <h3>新增种子</h3>
              <div class="form-group">
                <label>品种名称</label>
                <input v-model="seedForm.variety" placeholder="如：番茄" />
              </div>
              <div class="form-group">
                <label>供应商</label>
                <input v-model="seedForm.supplier" placeholder="可选" />
              </div>
              <div class="form-group">
                <label>批次号</label>
                <input v-model="seedForm.batch_no" placeholder="可选" />
              </div>
              <div class="form-group">
                <label>认证信息</label>
                <input v-model="seedForm.cert_info" placeholder="如：有机认证" />
              </div>
              <div class="form-actions">
                <button class="cancel-btn" @click="showSeedForm = false">取消</button>
                <button class="submit-btn" @click="handleCreateSeed">确定</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 种植批次管理 -->
        <div v-if="activeTab === 'batches'" class="tab-panel">
          <div class="panel-header">
            <h3>种植批次</h3>
            <button class="add-btn" @click="showBatchForm = true">
              <Plus :size="14" />
              新增批次
            </button>
          </div>
          <div class="data-table">
            <table>
              <thead>
                <tr>
                  <th>批次编号</th>
                  <th>地块</th>
                  <th>品种</th>
                  <th>种植日期</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="batch in batches" :key="batch.id">
                  <td>{{ batch.batch_code }}</td>
                  <td>{{ batch.plot?.name || '-' }}</td>
                  <td>{{ batch.seed?.variety || '-' }}</td>
                  <td>{{ batch.plant_date || '-' }}</td>
                  <td>
                    <span class="status-badge" :class="batch.status">{{ statusText(batch.status) }}</span>
                  </td>
                  <td>
                    <button class="action-btn detail-btn" @click="viewBatchDetail(batch)">详情</button>
                    <button class="action-btn" @click="handleDeleteBatch(batch.id)">删除</button>
                  </td>
                </tr>
                <tr v-if="!batches.length">
                  <td colspan="6" class="empty-row">暂无批次数据</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 新增批次表单 -->
          <div v-if="showBatchForm" class="modal-overlay" @click.self="showBatchForm = false">
            <div class="modal-content">
              <h3>新增种植批次</h3>
              <div class="form-group">
                <label>批次编号</label>
                <input v-model="batchForm.batch_code" placeholder="如：BATCH-2026-001" />
              </div>
              <div class="form-group">
                <label>地块</label>
                <select v-model="batchForm.plot_id">
                  <option value="">请选择地块</option>
                  <option v-for="p in plots" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>种子</label>
                <select v-model="batchForm.seed_id">
                  <option value="">请选择种子</option>
                  <option v-for="s in seeds" :key="s.id" :value="s.id">{{ s.variety }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>种植日期</label>
                <input v-model="batchForm.plant_date" type="date" />
              </div>
              <div class="form-group">
                <label>种植方式</label>
                <input v-model="batchForm.planting_method" placeholder="如：大棚种植" />
              </div>
              <div class="form-actions">
                <button class="cancel-btn" @click="showBatchForm = false">取消</button>
                <button class="submit-btn" @click="handleCreateBatch">确定</button>
              </div>
            </div>
          </div>

          <!-- 批次详情弹窗 -->
          <div v-if="showBatchDetail" class="modal-overlay" @click.self="showBatchDetail = false">
            <div class="modal-content modal-large">
              <div class="detail-header">
                <h3>批次详情：{{ selectedBatch?.batch_code }}</h3>
                <button class="close-btn" @click="showBatchDetail = false">✕</button>
              </div>
              <div class="detail-tabs">
                <button
                  v-for="dt in detailTabs"
                  :key="dt.key"
                  class="detail-tab"
                  :class="{ active: activeDetailTab === dt.key }"
                  @click="activeDetailTab = dt.key"
                >{{ dt.label }}</button>
              </div>
              <div class="detail-content">
                <!-- 农事记录 -->
                <div v-if="activeDetailTab === 'activities'">
                  <div class="sub-form">
                    <select v-model="newActivity.type">
                      <option value="浇水">浇水</option>
                      <option value="施肥">施肥</option>
                      <option value="打药">打药</option>
                      <option value="除草">除草</option>
                      <option value="其他">其他</option>
                    </select>
                    <input v-model="newActivity.detail" placeholder="操作内容" />
                    <input v-model="newActivity.materials" placeholder="使用物料" />
                    <input v-model="newActivity.datetime" type="datetime-local" />
                    <button class="submit-btn" @click="handleAddActivity">添加</button>
                  </div>
                  <div class="data-list">
                    <div v-for="a in batchActivities" :key="a.id" class="data-item">
                      <span class="item-type">{{ a.type }}</span>
                      <span class="item-detail">{{ a.detail }}</span>
                      <span class="item-materials">{{ a.materials }}</span>
                      <span class="item-time">{{ a.datetime }}</span>
                    </div>
                    <div v-if="!batchActivities.length" class="empty-text">暂无农事记录</div>
                  </div>
                </div>

                <!-- 环境数据 -->
                <div v-if="activeDetailTab === 'environment'">
                  <div class="sub-form">
                    <input v-model.number="newEnv.temperature" type="number" placeholder="温度℃" />
                    <input v-model.number="newEnv.humidity" type="number" placeholder="湿度%" />
                    <input v-model="newEnv.datetime" type="datetime-local" />
                    <button class="submit-btn" @click="handleAddEnvironment">添加</button>
                  </div>
                  <div class="data-list">
                    <div v-for="e in batchEnvironments" :key="e.id" class="data-item">
                      <span>🌡️ {{ e.temperature }}℃</span>
                      <span>💧 {{ e.humidity }}%</span>
                      <span class="item-time">{{ e.datetime }}</span>
                    </div>
                    <div v-if="!batchEnvironments.length" class="empty-text">暂无环境数据</div>
                  </div>
                </div>

                <!-- 采摘记录 -->
                <div v-if="activeDetailTab === 'harvest'">
                  <div class="sub-form">
                    <input v-model="newHarvest.harvest_date" type="date" />
                    <input v-model.number="newHarvest.yield_kg" type="number" placeholder="产量kg" />
                    <select v-model="newHarvest.grade">
                      <option value="">等级</option>
                      <option value="特级">特级</option>
                      <option value="一级">一级</option>
                      <option value="二级">二级</option>
                      <option value="三级">三级</option>
                    </select>
                    <button class="submit-btn" @click="handleAddHarvest">添加</button>
                  </div>
                  <div class="data-list">
                    <div v-for="h in batchHarvests" :key="h.id" class="data-item">
                      <span>📅 {{ h.harvest_date }}</span>
                      <span>⚖️ {{ h.yield_kg }}kg</span>
                      <span>🏷️ {{ h.grade }}</span>
                    </div>
                    <div v-if="!batchHarvests.length" class="empty-text">暂无采摘记录</div>
                  </div>
                </div>

                <!-- 质检记录 -->
                <div v-if="activeDetailTab === 'inspection'">
                  <div class="sub-form">
                    <select v-model="newInspection.inspection_type">
                      <option value="农残">农残</option>
                      <option value="重金属">重金属</option>
                      <option value="微生物">微生物</option>
                      <option value="外观">外观</option>
                    </select>
                    <select v-model="newInspection.result">
                      <option value="合格">合格</option>
                      <option value="不合格">不合格</option>
                    </select>
                    <input v-model="newInspection.lab_name" placeholder="检测机构" />
                    <button class="submit-btn" @click="handleAddInspection">添加</button>
                  </div>
                  <div class="data-list">
                    <div v-for="i in batchInspections" :key="i.id" class="data-item">
                      <span>{{ i.inspection_type }}</span>
                      <span class="item-result" :class="{ pass: i.result === '合格' }">{{ i.result }}</span>
                      <span>{{ i.lab_name }}</span>
                    </div>
                    <div v-if="!batchInspections.length" class="empty-text">暂无质检记录</div>
                  </div>
                </div>

                <!-- 包装记录 -->
                <div v-if="activeDetailTab === 'trace'">
                  <div class="sub-form">
                    <input v-model="newPackage.package_date" type="date" />
                    <input v-model.number="newPackage.weight_kg" type="number" placeholder="重量kg" />
                    <input v-model="newPackage.lot_number" placeholder="批次号" />
                    <input v-model="newPackage.package_spec" placeholder="规格" />
                    <button class="submit-btn" @click="handleAddPackage">添加包装</button>
                  </div>
                  <div class="data-list">
                    <div v-for="pkg in batchPackages" :key="pkg.id" class="trace-item">
                      <div class="trace-info">
                        <span>📦 {{ pkg.package_date }}</span>
                        <span>⚖️ {{ pkg.weight_kg }}kg</span>
                        <span>📋 {{ pkg.lot_number }}</span>
                      </div>
                      <div v-if="pkg.trace_code" class="trace-code">
                        <span class="code">{{ pkg.trace_code }}</span>
                        <button class="qr-btn" @click="showQR(pkg.trace_code)">查看二维码</button>
                      </div>
                    </div>
                    <div v-if="!batchPackages.length" class="empty-text">暂无包装记录</div>
                  </div>
                </div>

                <!-- 照片 -->
                <div v-if="activeDetailTab === 'photos'">
                  <div class="sub-form">
                    <select v-model="photoType">
                      <option value="growth">生长照片</option>
                      <option value="harvest">采摘照片</option>
                    </select>
                    <input v-model="photoDate" type="date" placeholder="照片日期" />
                    <input ref="photoFileInput" type="file" accept="image/*" style="display:none" @change="handlePhotoUpload" />
                    <button class="submit-btn" @click="triggerPhotoUpload">上传照片</button>
                  </div>
                  <div class="photo-grid">
                    <div v-for="photo in batchPhotos" :key="photo.id" class="photo-item">
                      <img :src="photo.file_path" :alt="photo.photo_type" />
                      <div class="photo-info">
                        <span>{{ photo.photo_type === 'growth' ? '生长' : '采摘' }}</span>
                        <span>{{ photo.photo_date }}</span>
                        <button class="delete-btn" @click="handleDeletePhoto(photo.id)">删除</button>
                      </div>
                    </div>
                    <div v-if="!batchPhotos.length" class="empty-text">暂无照片</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- 二维码弹窗 -->
    <div v-if="showQRModal" class="modal-overlay" @click.self="showQRModal = false">
      <div class="modal-content modal-qr">
        <h3>溯源二维码</h3>
        <div class="qr-display" v-if="qrImage">
          <img :src="qrImage" alt="溯源二维码" />
          <p class="qr-code-text">{{ qrCodeText }}</p>
        </div>
        <button class="cancel-btn" @click="showQRModal = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Fingerprint, Shield, Search, CheckCircle, AlertCircle,
  Plus, MapPin, Sprout, Package, ClipboardList, BarChart3,
  QrCode, ScanLine, Upload, ExternalLink
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import * as traceApi from '@/apis/trace_api'

// 统计数据
const stats = ref(null)

// 标签页
const activeTab = ref('dashboard')
const tabs = [
  { key: 'dashboard', label: '仪表盘', icon: BarChart3 },
  { key: 'plots', label: '地块管理', icon: MapPin },
  { key: 'seeds', label: '种子管理', icon: Sprout },
  { key: 'batches', label: '种植批次', icon: Package }
]

// 统计卡片
const statItems = computed(() => {
  if (!stats.value) return []
  return [
    { label: '地块', value: stats.value.total_plots, icon: MapPin },
    { label: '种子', value: stats.value.total_seeds, icon: Sprout },
    { label: '批次', value: stats.value.total_batches, icon: Package },
    { label: '溯源码', value: stats.value.total_trace_codes, icon: Fingerprint }
  ]
})

// 地块
const plots = ref([])
const showPlotForm = ref(false)
const plotForm = ref({ name: '', location: '', area_mu: null, soil_type: '' })

// 种子
const seeds = ref([])
const showSeedForm = ref(false)
const seedForm = ref({ variety: '', supplier: '', batch_no: '', cert_info: '' })

// 批次
const batches = ref([])
const showBatchForm = ref(false)
const batchForm = ref({ batch_code: '', plot_id: '', seed_id: '', plant_date: '', planting_method: '' })

// 批次详情
const showBatchDetail = ref(false)
const selectedBatch = ref(null)
const activeDetailTab = ref('activities')
const detailTabs = [
  { key: 'activities', label: '农事记录' },
  { key: 'environment', label: '环境数据' },
  { key: 'harvest', label: '采摘记录' },
  { key: 'inspection', label: '质检记录' },
  { key: 'trace', label: '溯源码' },
  { key: 'photos', label: '照片' }
]

const batchActivities = ref([])
const batchEnvironments = ref([])
const batchHarvests = ref([])
const batchInspections = ref([])
const batchPackages = ref([])
const batchPhotos = ref([])

const newActivity = ref({ type: '浇水', detail: '', materials: '', datetime: '' })
const newEnv = ref({ temperature: null, humidity: null, datetime: '' })
const newHarvest = ref({ harvest_date: '', yield_kg: null, grade: '' })
const newInspection = ref({ inspection_type: '农残', result: '合格', lab_name: '' })
const newPackage = ref({ package_date: '', weight_kg: null, lot_number: '', package_spec: '' })

// 照片上传
const photoType = ref('growth')
const photoDate = ref('')
const photoFileInput = ref(null)

// 溯源查询
const queryCode = ref('')
const queryResult = ref(null)

// 二维码
const showQRModal = ref(false)
const qrImage = ref('')
const qrCodeText = ref('')
const qrGenCode = ref('')
const generatedQR = ref('')
const qrFileInput = ref(null)
const scanResult = ref(null)

// 加载数据
async function loadStats() {
  try {
    const res = await traceApi.fetchTraceStats()
    if (res.ok) stats.value = res
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

async function loadPlots() {
  try {
    const res = await traceApi.listPlots()
    if (res.ok) plots.value = res.plots
  } catch (e) {
    console.error('加载地块失败:', e)
  }
}

async function loadSeeds() {
  try {
    const res = await traceApi.listSeeds()
    if (res.ok) seeds.value = res.seeds
  } catch (e) {
    console.error('加载种子失败:', e)
  }
}

async function loadBatches() {
  try {
    const res = await traceApi.listBatches()
    if (res.ok) batches.value = res.batches
  } catch (e) {
    console.error('加载批次失败:', e)
  }
}

// 地块操作
async function handleCreatePlot() {
  try {
    const res = await traceApi.createPlot(plotForm.value)
    if (res.ok) {
      showPlotForm.value = false
      plotForm.value = { name: '', location: '', area_mu: null, soil_type: '' }
      await loadPlots()
      await loadStats()
    }
  } catch (e) {
    console.error('创建地块失败:', e)
  }
}

async function handleDeletePlot(id) {
  if (!confirm('确定删除该地块？')) return
  try {
    await traceApi.deletePlot(id)
    await loadPlots()
    await loadStats()
  } catch (e) {
    console.error('删除地块失败:', e)
  }
}

// 种子操作
async function handleCreateSeed() {
  try {
    const res = await traceApi.createSeed(seedForm.value)
    if (res.ok) {
      showSeedForm.value = false
      seedForm.value = { variety: '', supplier: '', batch_no: '', cert_info: '' }
      await loadSeeds()
      await loadStats()
    }
  } catch (e) {
    console.error('创建种子失败:', e)
  }
}

async function handleDeleteSeed(id) {
  if (!confirm('确定删除该种子？')) return
  try {
    await traceApi.deleteSeed(id)
    await loadSeeds()
    await loadStats()
  } catch (e) {
    console.error('删除种子失败:', e)
  }
}

// 批次操作
async function handleCreateBatch() {
  try {
    const res = await traceApi.createBatch(batchForm.value)
    if (res.ok) {
      showBatchForm.value = false
      batchForm.value = { batch_code: '', plot_id: '', seed_id: '', plant_date: '', planting_method: '' }
      await loadBatches()
      await loadStats()
    }
  } catch (e) {
    console.error('创建批次失败:', e)
  }
}

async function handleDeleteBatch(id) {
  if (!confirm('确定删除该批次及其所有关联数据？')) return
  try {
    await traceApi.deleteBatch(id)
    await loadBatches()
    await loadStats()
  } catch (e) {
    console.error('删除批次失败:', e)
  }
}

function statusText(status) {
  const map = { growing: '种植中', harvested: '已采摘', packaged: '已包装', sold: '已销售' }
  return map[status] || status
}

// 批次详情
async function viewBatchDetail(batch) {
  selectedBatch.value = batch
  showBatchDetail.value = true
  activeDetailTab.value = 'activities'
  await loadBatchDetailData(batch.id)
}

async function loadBatchDetailData(batchId) {
  try {
    const [actRes, envRes, hvRes, insRes, pkgRes, photoRes] = await Promise.all([
      traceApi.listActivities(batchId),
      traceApi.listEnvironments(batchId),
      traceApi.listHarvests(batchId),
      traceApi.listInspections(batchId),
      traceApi.listPackages(batchId),
      traceApi.listPhotos(batchId)
    ])
    if (actRes.ok) batchActivities.value = actRes.activities
    if (envRes.ok) batchEnvironments.value = envRes.environments
    if (hvRes.ok) batchHarvests.value = hvRes.harvests
    if (insRes.ok) batchInspections.value = insRes.inspections
    if (pkgRes.ok) batchPackages.value = pkgRes.packages
    if (photoRes.ok) batchPhotos.value = photoRes.photos
  } catch (e) {
    console.error('加载批次详情失败:', e)
  }
}

async function handleAddActivity() {
  try {
    await traceApi.addActivity({ ...newActivity.value, batch_id: selectedBatch.value.id })
    newActivity.value = { type: '浇水', detail: '', materials: '', datetime: '' }
    await loadBatchDetailData(selectedBatch.value.id)
  } catch (e) {
    console.error('添加农事记录失败:', e)
  }
}

async function handleAddEnvironment() {
  try {
    await traceApi.addEnvironment({ ...newEnv.value, batch_id: selectedBatch.value.id })
    newEnv.value = { temperature: null, humidity: null, datetime: '' }
    await loadBatchDetailData(selectedBatch.value.id)
  } catch (e) {
    console.error('添加环境数据失败:', e)
  }
}

async function handleAddHarvest() {
  try {
    await traceApi.addHarvest({ ...newHarvest.value, batch_id: selectedBatch.value.id })
    newHarvest.value = { harvest_date: '', yield_kg: null, grade: '' }
    await loadBatchDetailData(selectedBatch.value.id)
    await loadBatches()
  } catch (e) {
    console.error('添加采摘记录失败:', e)
  }
}

async function handleAddInspection() {
  try {
    await traceApi.addInspection({ ...newInspection.value, batch_id: selectedBatch.value.id })
    newInspection.value = { inspection_type: '农残', result: '合格', lab_name: '' }
    await loadBatchDetailData(selectedBatch.value.id)
  } catch (e) {
    console.error('添加质检记录失败:', e)
  }
}

async function handleAddPackage() {
  try {
    await traceApi.addPackage({ ...newPackage.value, batch_id: selectedBatch.value.id })
    newPackage.value = { package_date: '', weight_kg: null, lot_number: '', package_spec: '' }
    await loadBatchDetailData(selectedBatch.value.id)
    await loadStats()
  } catch (e) {
    console.error('添加包装记录失败:', e)
  }
}

// 照片上传
function triggerPhotoUpload() {
  photoFileInput.value?.click()
}

async function handlePhotoUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('photo_type', photoType.value)
    formData.append('photo_date', photoDate.value || new Date().toISOString().split('T')[0])

    await traceApi.uploadPhoto(selectedBatch.value.id, formData)
    photoDate.value = ''
    e.target.value = ''
    await loadBatchDetailData(selectedBatch.value.id)
  } catch (e) {
    console.error('上传照片失败:', e)
  }
}

async function handleDeletePhoto(photoId) {
  if (!confirm('确定删除这张照片？')) return
  try {
    await traceApi.deletePhoto(photoId)
    await loadBatchDetailData(selectedBatch.value.id)
  } catch (e) {
    console.error('删除照片失败:', e)
  }
}

// 打开消费者查询页
function openConsumerPage() {
  window.open('/trace-query', '_blank')
}

// 溯源查询
async function handleQuery() {
  if (!queryCode.value.trim()) return
  try {
    const code = queryCode.value.trim()
    let res
    if (code.startsWith('TM')) {
      res = await traceApi.traceQuery(code)
    } else {
      res = await traceApi.traceByBatchCode(code)
    }
    if (res.ok) queryResult.value = res.report
  } catch (e) {
    console.error('溯源查询失败:', e)
    queryResult.value = null
  }
}

// 二维码
async function showQR(traceCode) {
  try {
    const res = await traceApi.generateQR(traceCode)
    if (res.ok) {
      qrImage.value = res.image_base64
      qrCodeText.value = traceCode
      showQRModal.value = true
    }
  } catch (e) {
    console.error('生成二维码失败:', e)
  }
}

async function handleGenerateQR() {
  if (!qrGenCode.value.trim()) return
  try {
    const res = await traceApi.generateQR(qrGenCode.value.trim())
    if (res.ok) {
      generatedQR.value = res.image_base64
    }
  } catch (e) {
    console.error('生成二维码失败:', e)
    generatedQR.value = ''
  }
}

function downloadQR() {
  if (!generatedQR.value) return
  const link = document.createElement('a')
  link.href = generatedQR.value
  link.download = `qr_${qrGenCode.value}.png`
  link.click()
}

function triggerQRUpload() {
  qrFileInput.value?.click()
}

function handleQRFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) decodeQRFile(file)
}

function handleQRDrop(e) {
  const file = e.dataTransfer.files?.[0]
  if (file) decodeQRFile(file)
}

async function decodeQRFile(file) {
  scanResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await traceApi.decodeQR(formData)
    scanResult.value = res
  } catch (e) {
    console.error('识别二维码失败:', e)
    scanResult.value = { ok: false, detail: '识别失败：' + (e.message || '未知错误') }
  }
}

// 初始化
onMounted(async () => {
  await Promise.all([loadStats(), loadPlots(), loadSeeds(), loadBatches()])
})
</script>

<style scoped lang="less">
.traceability {
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
  background: var(--main-50);
  color: var(--main-700);
  font-size: 12px;
  font-weight: 600;
}

.trace-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  color: var(--main-color);
}

.stat-card div {
  display: flex;
  flex-direction: column;
}

.stat-card span {
  font-size: 12px;
  color: var(--gray-600);
}

.stat-card strong {
  font-size: 22px;
  font-weight: 700;
  color: var(--gray-1000);
}

.tabs-nav {
  display: flex;
  gap: 4px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 4px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-600);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: var(--gray-50);
  color: var(--gray-1000);
}

.tab-btn.active {
  background: var(--main-color);
  color: var(--gray-0);
}

.tab-content {
  min-height: 400px;
}

.tab-panel {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 18px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.blockchain-card,
.trace-query-card,
.qr-card {
  padding: 16px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--main-color);
}

.card-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
  color: var(--gray-1000);
}

.consumer-link-btn {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: transparent;
  color: var(--gray-600);
  font-size: 12px;
  cursor: pointer;
  transition: all .2s;
  &:hover {
    border-color: var(--main-400);
    color: var(--main-700);
    background: var(--main-50);
  }
}

.blockchain-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bc-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 6px;
  background: var(--color-error-50);
  color: var(--color-error-700);
}

.bc-status.valid {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.bc-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bc-stat span {
  font-size: 12px;
  color: var(--gray-600);
}

.bc-stat strong {
  font-size: 18px;
  font-weight: 700;
}

.query-form {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.query-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}

.query-input:focus {
  border-color: var(--main-color);
}

.query-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.query-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.query-result {
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-0);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.result-header strong {
  font-size: 16px;
  font-weight: 700;
}

.result-badges {
  display: flex;
  gap: 6px;
}

.result-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: var(--color-warning-50);
  color: var(--color-warning-700);
}

.result-badge.verified {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.result-badge.tampered {
  background: var(--color-error-50);
  color: var(--color-error-700);
}

.tamper-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: var(--color-error-50);
  border: 1px solid var(--color-error-200);
  border-radius: 6px;
  color: var(--color-error-700);
  font-size: 13px;
  font-weight: 500;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-row span {
  color: var(--gray-600);
}

.info-row strong {
  color: var(--gray-1000);
}

.result-package {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--gray-150);
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.result-package span {
  color: var(--gray-600);
}

.qr-form {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.qr-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-0);
}

.qr-preview img {
  width: 160px;
  height: 160px;
}

.qr-preview p {
  margin: 0;
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-700);
}

.download-btn {
  padding: 6px 12px;
  border: 1px solid var(--main-color);
  border-radius: 4px;
  background: transparent;
  color: var(--main-color);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.download-btn:hover {
  background: var(--main-color);
  color: var(--gray-0);
}

.qr-scan {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  border: 2px dashed var(--gray-200);
  border-radius: 8px;
  background: var(--gray-0);
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: var(--main-color);
  background: var(--main-50);
}

.upload-area span {
  font-size: 13px;
  color: var(--gray-600);
}

.upload-hint {
  font-size: 11px !important;
  color: var(--gray-500) !important;
}

.scan-result {
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-0);
}

.scan-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  color: var(--color-error-700);
}

.scan-status.success {
  color: var(--color-success-700);
}

.scan-data {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.scan-data span {
  font-size: 12px;
  color: var(--gray-600);
}

.scan-data strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-1000);
  word-break: break-all;
}

.scan-error {
  font-size: 12px;
  color: var(--color-error-700);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 650;
  color: var(--gray-1000);
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.data-table {
  overflow-x: auto;
}

.data-table table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
  border-bottom: 1px solid var(--gray-150);
}

.data-table td {
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid var(--gray-100);
}

.empty-row {
  text-align: center;
  color: var(--gray-500);
  padding: 30px !important;
}

.action-btn {
  padding: 4px 8px;
  border: 1px solid var(--gray-200);
  border-radius: 4px;
  background: var(--gray-0);
  color: var(--gray-600);
  font-size: 12px;
  cursor: pointer;
  margin-right: 4px;
}

.action-btn:hover {
  border-color: var(--main-color);
  color: var(--main-color);
}

.detail-btn {
  border-color: var(--main-color);
  color: var(--main-color);
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.growing {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.status-badge.harvested {
  background: var(--color-warning-50);
  color: var(--color-warning-700);
}

.status-badge.packaged {
  background: var(--color-info-50);
  color: var(--color-info-700);
}

.status-badge.sold {
  background: var(--gray-100);
  color: var(--gray-700);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--gray-0);
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 480px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 800px;
}

.modal-qr {
  max-width: 360px;
  text-align: center;
}

.modal-content h3 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 700;
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-700);
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}

.form-group input:focus,
.form-group select:focus {
  border-color: var(--main-color);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.cancel-btn {
  padding: 8px 16px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-600);
  font-size: 13px;
  cursor: pointer;
}

.submit-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: var(--gray-100);
  color: var(--gray-600);
  cursor: pointer;
  font-size: 14px;
}

.detail-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--gray-150);
  padding-bottom: 8px;
}

.detail-tab {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--gray-600);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.detail-tab:hover {
  background: var(--gray-50);
}

.detail-tab.active {
  background: var(--main-color);
  color: var(--gray-0);
}

.sub-form {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.sub-form input,
.sub-form select {
  padding: 6px 10px;
  border: 1px solid var(--gray-200);
  border-radius: 4px;
  font-size: 12px;
  outline: none;
  min-width: 100px;
}

.sub-form input:focus,
.sub-form select:focus {
  border-color: var(--main-color);
}

.data-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.data-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-10);
  font-size: 12px;
}

.item-type {
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--main-50);
  color: var(--main-700);
  font-weight: 600;
}

.item-detail {
  flex: 1;
  color: var(--gray-1000);
}

.item-materials {
  color: var(--gray-600);
}

.item-time {
  color: var(--gray-500);
  font-size: 11px;
}

.item-result {
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-error-50);
  color: var(--color-error-700);
  font-weight: 600;
}

.item-result.pass {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.empty-text {
  text-align: center;
  color: var(--gray-500);
  padding: 20px;
  font-size: 13px;
}

.trace-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-10);
}

.trace-info {
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.trace-code {
  display: flex;
  align-items: center;
  gap: 8px;
}

.code {
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--main-50);
  color: var(--main-700);
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
}

.qr-btn {
  padding: 4px 8px;
  border: 1px solid var(--main-color);
  border-radius: 4px;
  background: transparent;
  color: var(--main-color);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.qr-display {
  margin: 16px 0;
}

.qr-display img {
  width: 200px;
  height: 200px;
}

.qr-code-text {
  margin-top: 8px;
  font-family: monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-700);
}

@media (max-width: 1180px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.photo-item {
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  overflow: hidden;
  background: var(--gray-0);
}

.photo-item img {
  width: 100%;
  height: 150px;
  object-fit: cover;
}

.photo-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--gray-600);
}

.photo-info .delete-btn {
  padding: 2px 6px;
  border: 1px solid var(--color-error-300);
  border-radius: 4px;
  background: transparent;
  color: var(--color-error-600);
  font-size: 11px;
  cursor: pointer;
}

.photo-info .delete-btn:hover {
  background: var(--color-error-50);
}
</style>
