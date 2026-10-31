<template>
  <div class="tomato-growth layout-container">
    <PageHeader title="生长档案" :show-border="true">
      <template #info>
        <PageAgentDropdown default-agent="growth-tracker" />
        <span class="stage-pill">
          <Leaf :size="14" />
          番茄 · 膨果期
        </span>
      </template>
    </PageHeader>

    <main class="growth-content">
      <section class="growth-hero">
        <img
          src="/images/Tomato/tomato-growth-stages.png"
          alt="番茄生长阶段"
          class="growth-hero-image"
        />
        <div class="growth-hero-copy">
          <p>批次档案</p>
          <h2>A 区 2026 春茬番茄</h2>
          <span>定植 48 天 · 膨果期 · 预计 6 天后进入集中采收</span>
        </div>
      </section>

      <section class="stage-timeline">
        <article
          v-for="stage in stages"
          :key="stage.name"
          class="stage-item"
          :class="{ active: stage.active, done: stage.done }"
        >
          <span class="stage-dot"></span>
          <strong>{{ stage.name }}</strong>
          <p>{{ stage.date }}</p>
        </article>
      </section>

      <section class="growth-grid">
        <article v-for="metric in metrics" :key="metric.label" class="metric-card">
          <component :is="metric.icon" :size="20" />
          <div>
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <p>{{ metric.note }}</p>
          </div>
        </article>
      </section>

      <section class="record-panel">
        <div class="section-title">
          <ClipboardList :size="18" />
          <h3>近期操作记录</h3>
        </div>
        <div class="record-list">
          <div v-for="record in records" :key="record.title" class="record-row">
            <span>{{ record.time }}</span>
            <strong>{{ record.title }}</strong>
            <p>{{ record.note }}</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ClipboardList, Droplets, Flower2, Leaf, Scale, Sprout } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageAgentDropdown from '@/components/PageAgentDropdown.vue'

const stages = [
  { name: '缓苗期', date: '04-22', done: true },
  { name: '营养生长期', date: '05-02', done: true },
  { name: '现蕾期', date: '05-16', done: true },
  { name: '开花期', date: '05-24', done: true },
  { name: '膨果期', date: '06-03', active: true },
  { name: '采收期', date: '预计 06-14' }
]

const metrics = [
  { label: '株高', value: '24.6 cm', note: '较上周 +2.1 cm', icon: Sprout },
  { label: '开花率', value: '82%', note: '处于正常范围', icon: Flower2 },
  { label: '坐果率', value: '76%', note: '较目标 +4%', icon: Leaf },
  { label: '单果均重', value: '18.4 g', note: '膨果稳定', icon: Scale },
  { label: '畸形果率', value: '3.2%', note: '低于预警线', icon: Leaf },
  { label: '基质含水', value: '64%', note: '建议保持', icon: Droplets }
]

const records = [
  { time: '今天 09:30', title: '营养液巡检', note: 'pH 6.2，EC 1.8 mS/cm，维持当前配方。' },
  { time: '昨天 16:20', title: '修叶作业', note: 'A 区完成老叶清理，通风条件改善。' },
  { time: '06-06 10:10', title: '病害巡检', note: '未发现明显灰霉病扩散，建议继续观察湿度。' }
]
</script>

<style scoped lang="less">
.tomato-growth {
  min-height: 100%;
  background: var(--gray-25);
}

.stage-pill {
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

.growth-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

.growth-hero,
.record-panel,
.metric-card,
.stage-item {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.growth-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 460px);
  overflow: hidden;
}

.growth-hero-image {
  width: 100%;
  height: 260px;
  object-fit: cover;
}

.growth-hero-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 26px;
}

.growth-hero-copy p {
  margin: 0 0 8px;
  color: var(--main-color);
  font-size: 12px;
  font-weight: 700;
}

.growth-hero-copy h2 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.35;
}

.growth-hero-copy span {
  margin-top: 10px;
  color: var(--gray-600);
  font-size: 14px;
}

.stage-timeline {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.stage-item {
  padding: 14px;
}

.stage-dot {
  display: block;
  width: 10px;
  height: 10px;
  margin-bottom: 10px;
  border-radius: 50%;
  background: var(--gray-300);
}

.stage-item.done .stage-dot,
.stage-item.active .stage-dot {
  background: var(--main-color);
}

.stage-item.active {
  border-color: var(--main-200);
  background: color-mix(in srgb, var(--main-color) 5%, var(--gray-0));
}

.stage-item strong,
.metric-card strong,
.record-row strong {
  display: block;
  color: var(--gray-1000);
  font-weight: 700;
}

.stage-item p,
.metric-card p,
.record-row p {
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
}

.growth-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 108px;
  padding: 14px;
  color: var(--main-color);
}

.metric-card span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
}

.metric-card strong {
  margin-top: 6px;
  font-size: 24px;
  line-height: 30px;
}

.record-panel {
  padding: 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--main-color);
}

.section-title h3 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 16px;
  font-weight: 650;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-row {
  display: grid;
  grid-template-columns: 120px 150px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.record-row span {
  color: var(--gray-600);
  font-size: 12px;
}

@media (max-width: 1180px) {
  .growth-hero,
  .stage-timeline,
  .growth-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .growth-hero,
  .stage-timeline,
  .growth-grid,
  .record-row {
    grid-template-columns: 1fr;
  }
}
</style>
