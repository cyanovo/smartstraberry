<script setup>
import { computed, ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import { list } from '@/apis/strawberry_api'

const props = defineProps({ resource: { type: String, required: true } })
const schema = {
  area: { title: '场地管理', columns: [['areaId', '编号'], ['areaName', '场地名称'], ['areaAddress', '地址'], ['areaType', '类型'], ['areaSquare', '面积'], ['areaState', '状态'], ['createDate', '创建日期']] },
  plant: { title: '植物管理', columns: [['plantId', '编号'], ['plantName', '植物名称'], ['plantType', '类型'], ['areaName', '所属场地'], ['plantLifecycle', '生命周期（月）']] },
  device: { title: '设备管理', columns: [['deviceId', '编号'], ['deviceName', '设备名称'], ['deviceNumber', '设备编号'], ['deviceType', '类型'], ['areaName', '所属场地'], ['deviceState', '设备状态']] },
  record: { title: '环境监测', columns: [['createDate', '记录时间'], ['areaName', '场地'], ['airTemperature', '空气温度 °C'], ['airHumidity', '空气湿度 %'], ['lightLux', '光照 lx'], ['soilTemperature', '土壤温度 °C'], ['soilHumidity', '土壤湿度 %'], ['soilPh', '土壤 pH']] },
  disease: { title: '病虫害记录', columns: [['id', '编号'], ['clusterId', '果簇编号'], ['objectType', '检测对象'], ['pestDiseaseClass', '病虫害'], ['severityLevel', '严重程度'], ['confidence', '置信度'], ['detectedTime', '检测时间']] },
  starryCluster: { title: '草莓果簇记录', columns: [['id', '编号'], ['clusterId', '果簇编号'], ['clusterName', '果簇名称'], ['locationArea', '所在区域'], ['totalCount', '总数'], ['ripeCount', '成熟数'], ['lastUpdate', '更新时间']] }
}
const config = computed(() => schema[props.resource])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await list(props.resource, { pageNum: page.value, pageSize: 10 })
    rows.value = response.rows || []
    total.value = response.total || 0
  } catch (e) {
    rows.value = []
    total.value = 0
    error.value = e.message
  } finally { loading.value = false }
}

watch(() => props.resource, () => { page.value = 1; load() }, { immediate: true })
function changePage(value) { page.value = value; load() }
</script>

<template>
  <main class="records">
    <PageHeader :title="config.title" :loading="loading" show-border>
      <template #info><span>{{ total }} 条</span></template>
      <template #actions><a-button title="刷新数据" :loading="loading" @click="load"><RefreshCw :size="16" /></a-button></template>
    </PageHeader>
    <div class="records-content">
    <a-alert v-if="error" type="error" :message="error" show-icon class="notice" />
    <div class="table-wrap">
      <a-table :data-source="rows" :columns="config.columns.map(([dataIndex, title]) => ({ dataIndex, title, key: dataIndex, ellipsis: true }))" :row-key="row => row.id ?? row.recordId ?? row.deviceId ?? row.plantId ?? row.areaId" :loading="loading" :pagination="false" :scroll="{ x: 'max-content' }" size="middle" />
    </div>
    <a-pagination v-if="total > 10" :current="page" :total="total" :page-size="10" show-less-items class="pagination" @change="changePage" />
    </div>
  </main>
</template>

<style scoped lang="less">
.records-content { padding: var(--page-padding); }
.table-wrap { background: var(--gray-0); border: 1px solid var(--gray-200); }
.pagination { display: flex; justify-content: flex-end; margin-top: 18px; }
.notice { margin-bottom: 16px; }
@media (max-width: 600px) {
  :deep(.page-header) { flex-wrap: wrap; }
}
</style>
