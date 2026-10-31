<template>
  <a-select
    class="disease-record-select"
    :value="value"
    mode="multiple"
    allow-clear
    show-search
    option-filter-prop="label"
    :virtual="false"
    :options="options"
    :loading="loading"
    placeholder="选择病虫害识别记录"
    aria-label="选择病虫害识别记录"
    @update:value="emit('update:value', $event)"
    @dropdown-visible-change="emit('dropdown-visible-change', $event)"
  >
    <template #option="option">
      <div class="record-option">
        <div class="record-time"><Clock3 :size="14" /><time>{{ option.time }}</time></div>
        <div class="record-result">{{ option.result }}</div>
        <div class="record-source">{{ option.album }} · {{ option.value.slice(0, 8) }}</div>
      </div>
    </template>
    <template #tagRender="{ value: id, closable, onClose }">
      <span class="selected-record">
        <span class="selected-record-text">
          <span class="record-time"><Clock3 :size="13" />{{ findOption(id)?.time || '时间待加载' }}</span>
          <span class="selected-detail">{{ findOption(id)?.result || id }} · {{ findOption(id)?.album || '记录加载中' }}</span>
        </span>
        <button v-if="closable" type="button" title="移除此记录" aria-label="移除此记录" @mousedown.prevent.stop @click.stop="onClose"><X :size="14" /></button>
      </span>
    </template>
    <template #notFoundContent><a-empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="暂无匹配的病虫害记录" /></template>
  </a-select>
</template>

<script setup>
import { Clock3, X } from 'lucide-vue-next'
import { Empty } from 'ant-design-vue'
const props = defineProps({ value: { type: Array, default: () => [] }, options: { type: Array, default: () => [] }, loading: Boolean })
const emit = defineEmits(['update:value', 'dropdown-visible-change'])
const findOption = id => props.options.find(option => option.value === id)
</script>

<style scoped lang="less">
.disease-record-select { width: 100%; min-width: 0; }
.record-option { padding: 6px 0; white-space: normal; overflow-wrap: anywhere; }
.record-time { display: flex; align-items: center; gap: 6px; font-size: 13px; font-variant-numeric: tabular-nums; color: var(--color-text); }
.record-time svg { flex-shrink: 0; }
.record-result { margin-top: 5px; font-weight: 500; }
.record-source, .selected-detail { font-size: 12px; color: var(--color-text-secondary); margin-top: 3px; overflow-wrap: anywhere; }
.selected-record { display: flex; width: 100%; align-items: center; gap: 8px; padding: 6px 8px; margin: 3px 0; background: var(--gray-50); border: 1px solid var(--gray-150); border-radius: 4px; white-space: normal; }
.selected-record-text { flex: 1; min-width: 0; }
.selected-detail { display: block; }
.selected-record button { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; flex-shrink: 0; border: 0; background: transparent; color: var(--color-text-secondary); cursor: pointer; border-radius: 4px; }
.selected-record button:hover { background: var(--gray-150); }
:deep(.ant-select-selection-overflow-item) { max-width: 100%; }
:deep(.ant-select-selection-overflow-item:not(.ant-select-selection-overflow-item-suffix)) { width: 100%; }
:deep(.ant-select-selector) { padding-right: 26px !important; }
</style>
