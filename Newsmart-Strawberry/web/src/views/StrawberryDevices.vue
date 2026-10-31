<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Plus, RefreshCw, Search, Download, Pencil, Trash2, Eye } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import { list, getUser } from '@/apis/strawberry_api'
import { deviceDetail, saveDevice, deleteDevice, deviceOptions, exportDevices } from '@/apis/strawberry_hardware'

const rows = ref([]), total = ref(0), loading = ref(false), error = ref(''), permissions = ref([])
const page = ref(1), pageSize = ref(10), plants = ref([]), areas = ref([])
const filters = reactive({ deviceName: '', deviceNumber: '', deviceState: undefined, plantId: undefined })
const applied = ref({})
const open = ref(false), readonly = ref(false), saving = ref(false), exporting = ref(false), formRef = ref(), form = ref({})
const can = action => permissions.value.includes('*:*:*') || permissions.value.includes(`system:device:${action}`)
const states = [{ value: 1, label: '正常使用' }, { value: 0, label: '停用' }]
const columns = [
  ['deviceName', '设备名称'], ['deviceNumber', '设备编号'], ['deviceType', '类型'], ['plantName', '监控植物'], ['areaName', '所属场地'], ['deviceState', '档案状态'], ['createDate', '创建时间'], ['updateDate', '更新时间'], ['actions', '操作']
].map(([dataIndex, title]) => ({ dataIndex, title, key: dataIndex, width: dataIndex === 'actions' ? 150 : 140 }))
const rules = Object.fromEntries(['deviceName', 'deviceNumber', 'deviceState', 'plantId', 'areaId'].map(key => [key, [{ required: true, message: '此项不能为空' }]]))
async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await list('device', { ...applied.value, pageNum: page.value, pageSize: pageSize.value })
    rows.value = result.rows
    total.value = result.total
  } catch (e) { rows.value = []; total.value = 0; error.value = e.message } finally { loading.value = false }
}
function search(reset = false) {
  if (reset) Object.assign(filters, { deviceName: '', deviceNumber: '', deviceState: undefined, plantId: undefined })
  applied.value = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== '' && value !== null))
  page.value = 1
  load()
}
async function edit(row, view = false) {
  readonly.value = view
  try {
    form.value = row ? { ...(await deviceDetail(row.deviceId)).data } : { deviceState: 1, createDate: new Date().toLocaleDateString('en-CA') }
    if (form.value.deviceState != null) form.value.deviceState = Number(form.value.deviceState)
    open.value = true
  } catch (e) { message.error(e.message) }
}
async function save() {
  try { await formRef.value.validate() } catch { return }
  if (saving.value) return
  saving.value = true
  try {
    // Send only editable device fields, never ownership or deletion metadata.
    const keys = ['deviceId', 'deviceName', 'deviceNumber', 'deviceType', 'deviceState', 'plantId', 'areaId', 'createDate', 'updateDate']
    await saveDevice(Object.fromEntries(keys.filter(key => form.value[key] != null).map(key => [key, form.value[key]])))
    open.value = false
    message.success('设备已保存')
    await load()
  } catch (e) { message.error(e.message) } finally { saving.value = false }
}
function remove(row) {
  Modal.confirm({ title: `删除设备“${row.deviceName}”？`, content: `设备编号：${row.deviceNumber}`, okText: '删除', okType: 'danger', cancelText: '取消', async onOk() {
    try {
      await deleteDevice(row.deviceId)
      if (rows.value.length === 1 && page.value > 1) page.value--
      message.success('设备已删除')
      await load()
    } catch (e) { message.error(e.message); throw e }
  } })
}
async function download() {
  exporting.value = true
  try { await exportDevices(applied.value) } catch (e) { message.error(e.message) } finally { exporting.value = false }
}
onMounted(async () => {
  load()
  try {
    const info = await getUser()
    permissions.value = info.permissions || []
    const options = await Promise.all([deviceOptions('plantId'), deviceOptions('areaName')])
    plants.value = options[0].map(row => ({ value: row.plantId, label: row.plantName }))
    areas.value = options[1].map(row => ({ value: row.areaId, label: row.areaName }))
  } catch (e) { error.value = e.message }
})
</script>

<template>
  <div class="industrial-iot-view layout-container">
    <PageHeader title="设备管理" :show-border="true" :loading="loading">
      <template #actions>
        <a-button v-if="can('add')" type="primary" class="lucide-icon-btn" @click="edit()"><Plus :size="16" />新增设备</a-button>
        <a-button v-if="can('export')" title="导出设备列表" :loading="exporting" @click="download"><Download :size="16" /></a-button>
        <a-button title="刷新设备" :loading="loading" @click="load"><RefreshCw :size="16" /></a-button>
      </template>
    </PageHeader>
    <main class="iot-content">
      <a-alert v-if="error" type="error" :message="error" show-icon />
      <a-form :model="filters" layout="inline" class="device-filters" @finish="search()">
        <a-form-item label="设备名称"><a-input v-model:value="filters.deviceName" allow-clear /></a-form-item>
        <a-form-item label="设备编号"><a-input v-model:value="filters.deviceNumber" allow-clear /></a-form-item>
        <a-form-item label="监控植物"><a-select v-model:value="filters.plantId" :options="plants" allow-clear /></a-form-item>
        <a-form-item label="档案状态"><a-select v-model:value="filters.deviceState" :options="states" allow-clear /></a-form-item>
        <a-space><a-button html-type="submit" class="lucide-icon-btn"><Search :size="16" />查询</a-button><a-button title="重置查询" @click="search(true)"><RefreshCw :size="16" /></a-button></a-space>
      </a-form>
      <a-table :columns="columns" :data-source="rows" row-key="deviceId" :loading="loading" :scroll="{ x: 1270 }" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'deviceState'"><a-tag :color="Number(record.deviceState) === 1 ? 'green' : undefined">{{ record.deviceState == null ? '未知' : Number(record.deviceState) === 1 ? '正常使用' : '停用' }}</a-tag></template>
          <a-space v-else-if="column.key === 'actions'">
            <a-button v-if="can('query')" type="text" title="设备详情" @click="edit(record, true)"><Eye :size="16" /></a-button>
            <a-button v-if="can('edit') && can('query')" type="text" title="修改设备" @click="edit(record)"><Pencil :size="16" /></a-button>
            <a-button v-if="can('remove')" type="text" danger title="删除设备" @click="remove(record)"><Trash2 :size="16" /></a-button>
          </a-space>
        </template>
      </a-table>
      <a-pagination v-model:current="page" v-model:page-size="pageSize" :total="total" show-size-changer :show-total="n => `共 ${n} 条`" @change="load" />
    </main>
    <a-modal v-model:open="open" :title="readonly ? '设备详情' : form.deviceId ? '修改设备' : '新增设备'" :confirm-loading="saving" :footer="readonly ? null : undefined" :mask-closable="!saving" :closable="!saving" :cancel-button-props="{ disabled: saving }" ok-text="保存" cancel-text="取消" destroy-on-close @ok="save">
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical" :disabled="readonly || saving">
        <a-form-item label="设备名称" name="deviceName"><a-input v-model:value="form.deviceName" /></a-form-item>
        <a-form-item label="设备编号" name="deviceNumber"><a-input v-model:value="form.deviceNumber" /></a-form-item>
        <a-form-item label="设备类型" name="deviceType"><a-input v-model:value="form.deviceType" /></a-form-item>
        <a-form-item label="档案状态" name="deviceState"><a-select v-model:value="form.deviceState" :options="states" /></a-form-item>
        <a-form-item label="监控植物" name="plantId"><a-select v-model:value="form.plantId" :options="plants" /></a-form-item>
        <a-form-item label="所属场地" name="areaId"><a-select v-model:value="form.areaId" :options="areas" /></a-form-item>
        <a-form-item label="创建时间"><a-date-picker v-model:value="form.createDate" value-format="YYYY-MM-DD" /></a-form-item>
        <a-form-item label="更新时间"><a-date-picker v-model:value="form.updateDate" value-format="YYYY-MM-DD" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style lang="less" scoped src="./IndustrialIotView.less"></style>
<style lang="less" scoped>
.device-filters { gap: 12px; }
.device-filters :deep(.ant-select) { min-width: 130px; }
.device-filters :deep(.ant-input-affix-wrapper) { width: 160px; }
:deep(.page-header) { flex-wrap: wrap; }
:deep(.ant-pagination) { display: flex; flex-wrap: wrap; gap: 4px; }
</style>
