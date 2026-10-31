<template>
  <div class="tomato-dashboard layout-container">
    <PageHeader title="草莓驾驶舱" :show-border="true" :loading="loading">
      <template #actions><a-button title="刷新数据" :loading="loading" @click="load"><RefreshCw :size="16" /></a-button></template>
    </PageHeader>
    <main class="dashboard-content">
      <a-alert v-if="error" type="error" :message="error" show-icon />
      <section class="hero-panel">
        <img class="hero-image" src="/images/strawberry-field.jpg" alt="草莓种植" />
        <div class="hero-overlay"></div>
        <div class="hero-copy"><p class="eyebrow">种植概况</p><h2>草莓种植管理</h2><p class="hero-desc">{{ latest ? `${latest.areaName || '未标记场地'} · ${latest.createDate || '未记录时间'}` : '暂无环境记录' }}</p></div>
        <div class="hero-metrics"><router-link v-for="item in metrics" :key="item.key" :to="item.path" class="hero-metric"><span>{{ item.label }}</span><strong>{{ item.count ?? '—' }}</strong></router-link></div>
      </section>
      <section class="metric-strip">
        <article v-for="item in fields" :key="item.key" class="metric-card"><component :is="item.icon" :size="20" /><div><span>{{ item.label }}</span><strong>{{ latest?.[item.key] ?? '—' }} {{ latest?.[item.key] == null ? '' : item.unit }}</strong></div></article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RefreshCw, Thermometer, Droplets, Sun, Gauge } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import { list } from '@/apis/strawberry_api'
const loading = ref(false)
const error = ref('')
const latest = ref(null)
const metrics = ref([
  { key: 'area', label: '场地', path: '/areas', count: null },
  { key: 'plant', label: '植物', path: '/plants', count: null },
  { key: 'device', label: '设备', path: '/devices', count: null },
  { key: 'record', label: '监测记录', path: '/records', count: null }
])
const fields = [
  { key: 'airTemperature', label: '空气温度', unit: '°C', icon: Thermometer },
  { key: 'airHumidity', label: '空气湿度', unit: '%', icon: Droplets },
  { key: 'lightLux', label: '光照', unit: 'lx', icon: Sun },
  { key: 'airCo2', label: 'CO₂', unit: 'ppm', icon: Gauge }
]
async function load() {
  loading.value = true
  error.value = ''
  latest.value = null
  const results = await Promise.allSettled(metrics.value.map(item => list(item.key, { pageNum: 1, pageSize: 1, ...(item.key === 'record' ? { orderByColumn: 'createDate', isAsc: 'desc' } : {}) })))
  results.forEach((result, index) => {
    metrics.value[index].count = result.status === 'fulfilled' ? result.value.total : null
    if (index === 3 && result.status === 'fulfilled') latest.value = result.value.rows?.[0] || null
  })
  error.value = results.find(result => result.status === 'rejected')?.reason.message || ''
  loading.value = false
}
onMounted(load)
</script>

<style lang="less" scoped src="./TomatoDashboardView.less"></style>
