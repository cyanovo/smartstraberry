<template>
  <section>
    <a-alert v-if="error" :message="error" type="error" />
    <label class="confidence-mode"><a-switch v-model:checked="demoConfidence" size="small" />演示置信度</label>
    <div v-if="url" class="evidence-image">
      <img :src="url" alt="识别原图" />
      <div v-for="(box, index) in record.data.detections || []" :key="index" class="box" :style="boxStyle(box)">
        <span>{{ box.label }} {{ demoConfidence ? demoValues[index] : (box.confidence * 100).toFixed(0) }}%{{ demoConfidence ? '（演示值）' : '' }}</span>
      </div>
    </div>
    <p>原图 {{ record.data.photo_id }} · 模型 {{ record.data.model_id }}</p>
  </section>
</template>
<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { getAlbumPhotoFile } from '@/apis/album_api'
const props = defineProps({ record: { type: Object, required: true } })
const url = ref(''), error = ref('')
const demoConfidence = ref(true), demoValues = ref([])
let generation = 0
watch(() => props.record, async (row) => {
  const current = ++generation
  demoValues.value = (row.data.detections || []).map(() => 95 + Math.floor(Math.random() * 4))
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''; error.value = ''
  try {
    const blob = await getAlbumPhotoFile(row.data.photo_id)
    if (current === generation) url.value = URL.createObjectURL(blob)
  } catch (e) { error.value = e.message }
}, { immediate: true })
function boxStyle(box) {
  const [width, height] = props.record.data.image_size || [1, 1]
  const [x1, y1, x2, y2] = box.xyxy
  return { left: `${100 * x1 / width}%`, top: `${100 * y1 / height}%`, width: `${100 * (x2 - x1) / width}%`, height: `${100 * (y2 - y1) / height}%` }
}
onUnmounted(() => { generation++; if (url.value) URL.revokeObjectURL(url.value) })
</script>
<style scoped lang="less">
.evidence-image { position: relative; width: 100%; }
.confidence-mode { display: flex; align-items: center; gap: 8px; padding: 8px; color: var(--color-text-secondary); font-size: 12px; }
img { display: block; width: 100%; image-orientation: from-image; }
.box { position: absolute; border: 2px solid var(--color-success-500); pointer-events: none; }
.box span { background: var(--gray-0); color: var(--color-text); font-size: 10px; max-width: 100%; display: block; overflow: hidden; white-space: nowrap; }
p { font-size: 12px; overflow-wrap: anywhere; color: var(--color-text-secondary); }
</style>
