<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client, { type ApiResponse } from '@/api/client'

const sources = ref<Array<{ id: string; name: string; base_url: string; status: string }>>([])
const tasks = ref<Array<{ id: string; name: string; status: string }>>([])
const logs = ref<Array<Record<string, unknown>>>([])
const newTaskName = ref('全量抓取')

async function load() {
  const [s, t, l] = await Promise.all([
    client.get<ApiResponse>('/scraper/sources'),
    client.get<ApiResponse>('/scraper/tasks'),
    client.get<ApiResponse>('/scraper/logs'),
  ])
  sources.value = s.data.data
  tasks.value = t.data.data
  logs.value = l.data.data
}

onMounted(load)

async function createTask() {
  await client.post('/scraper/tasks', { name: newTaskName.value })
  ElMessage.success('任务已创建')
  await load()
}

async function runTask(id: string) {
  await client.post(`/scraper/tasks/${id}/run`)
  ElMessage.success('抓取任务已触发')
  setTimeout(load, 2000)
}
</script>

<template>
  <el-row :gutter="16">
    <el-col :span="12">
      <el-card header="数据源">
        <el-table :data="sources" size="small">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="status" label="状态" width="80" />
        </el-table>
      </el-card>
    </el-col>
    <el-col :span="12">
      <el-card header="抓取任务">
        <div style="margin-bottom: 12px; display: flex; gap: 8px">
          <el-input v-model="newTaskName" placeholder="任务名称" />
          <el-button type="primary" @click="createTask">创建</el-button>
        </div>
        <el-table :data="tasks" size="small">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="runTask(row.id)">运行</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
  <el-card header="抓取日志" style="margin-top: 16px">
    <el-table :data="logs" size="small">
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="total" label="总数" width="80" />
      <el-table-column prop="updated_count" label="更新" width="80" />
      <el-table-column prop="failed_count" label="失败" width="80" />
      <el-table-column prop="message" label="消息" />
      <el-table-column prop="started_at" label="开始时间" width="180" />
    </el-table>
  </el-card>
</template>
