<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import client, { type ApiResponse } from '@/api/client'

interface Official {
  id: string
  name: string
  birth_place: string
  committee_term: string
  status: string
  current_position: string | null
}

const router = useRouter()
const loading = ref(false)
const officials = ref<Official[]>([])
const total = ref(0)
const filters = ref({ name: '', committee_term: '', status: '' })
const page = ref(1)

async function load() {
  loading.value = true
  try {
    const { data } = await client.get<ApiResponse>('/officials', {
      params: { ...filters.value, page: page.value, page_size: 20 },
    })
    officials.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

onMounted(load)

function viewDetail(row: Official) {
  router.push(`/officials/${row.id}`)
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="toolbar">
        <el-input v-model="filters.name" placeholder="姓名" clearable style="width: 160px" @change="load" />
        <el-input v-model="filters.committee_term" placeholder="届次" clearable style="width: 140px" @change="load" />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="load">
          <el-option label="在任" value="active" />
          <el-option label="退休" value="retired" />
        </el-select>
        <el-button type="primary" @click="load">搜索</el-button>
      </div>
    </template>
    <el-table :data="officials" v-loading="loading" @row-click="viewDetail" style="cursor: pointer">
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="birth_place" label="出生地" />
      <el-table-column prop="committee_term" label="届次" width="120" />
      <el-table-column prop="current_position" label="现任职务" />
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="20"
      layout="total, prev, pager, next"
      style="margin-top: 16px"
      @current-change="load"
    />
  </el-card>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
