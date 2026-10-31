<script setup>
import { computed } from 'vue'
import { BookOpen, FileText, LoaderCircle, CircleAlert, Check } from 'lucide-vue-next'
import { summarizeKnowledgeRetrieval } from '@/utils/knowledgeRetrieval'
import { useDatabaseStore } from '@/stores/database'

const props = defineProps({ toolCall: { type: Object, required: true } })
const databaseStore = useDatabaseStore()
const summary = computed(() => summarizeKnowledgeRetrieval(props.toolCall))
const name = computed(() => summary.value.kbName || databaseStore.getDatabaseNameById(summary.value.kbId) || summary.value.kbId)
</script>

<template>
  <section class="retrieval-status" :class="summary.state" aria-label="知识库检索过程">
    <div class="retrieval-heading" role="status" aria-live="polite">
      <LoaderCircle v-if="summary.state === 'running'" class="spinning" :size="16" />
      <CircleAlert v-else-if="summary.state === 'error'" :size="16" />
      <Check v-else :size="16" />
      <strong>{{ summary.label }}</strong>
      <span v-if="summary.count">{{ summary.count }} 个相关片段 · {{ summary.files.length }} 个已知文件</span>
    </div>
    <div v-if="name" class="retrieval-library"><BookOpen :size="14" /><span>{{ name }}</span></div>
    <p v-if="summary.query" class="retrieval-query">{{ summary.query }}</p>
    <ul v-if="summary.files.length" class="retrieval-files">
      <li v-for="file in summary.files" :key="file"><FileText :size="14" /><span>{{ file }}</span></li>
    </ul>
    <p v-else-if="summary.count" class="retrieval-query">检索结果未提供文件名</p>
  </section>
</template>

<style scoped lang="less">
.retrieval-status { margin: 8px 0; padding: 10px 0 10px 12px; border-left: 2px solid var(--main-color); font-size: 13px; }
.retrieval-heading, .retrieval-library, .retrieval-files li { display: flex; align-items: center; gap: 8px; min-width: 0; }
.retrieval-heading { flex-wrap: wrap; color: var(--color-text); }
.retrieval-heading strong { font-weight: 600; }
.retrieval-heading > span, .retrieval-query { color: var(--color-text-secondary); font-size: 12px; }
.retrieval-library { margin-top: 8px; color: var(--main-color); }
.retrieval-query { margin: 6px 0 0; overflow-wrap: anywhere; }
.retrieval-files { list-style: none; padding: 0; margin: 8px 0 0; display: grid; gap: 6px; color: var(--color-text); }
.retrieval-status span { overflow-wrap: anywhere; }
.retrieval-status svg { flex-shrink: 0; }
.error { border-color: var(--color-error-500); }
.spinning { animation: retrieval-spin 1.2s linear infinite; }
@keyframes retrieval-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinning { animation: none; } }
</style>
