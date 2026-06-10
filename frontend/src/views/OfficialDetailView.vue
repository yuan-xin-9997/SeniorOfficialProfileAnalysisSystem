<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import client, { type ApiResponse } from '@/api/client'

const route = useRoute()
const official = ref<Record<string, unknown> | null>(null)
const connections = ref<Array<{ id: string; name: string; strength: number; rel_type: string }>>([])

onMounted(async () => {
  const id = route.params.id as string
  const [detailRes, connRes] = await Promise.all([
    client.get<ApiResponse>(`/officials/${id}`),
    client.get<ApiResponse>('/analysis/connections', { params: { official_id: id, min_strength: 0.3 } }),
  ])
  official.value = detailRes.data.data
  connections.value = connRes.data.data.connections || []
})
</script>

<template>
  <div v-if="official">
    <el-card>
      <template #header>
        <h3>{{ official.name }}</h3>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="出生地">{{ official.birth_place }}</el-descriptions-item>
        <el-descriptions-item label="出生日期">{{ official.birth_date }}</el-descriptions-item>
        <el-descriptions-item label="届次">{{ official.committee_term }}</el-descriptions-item>
        <el-descriptions-item label="委员类型">{{ official.committee_type }}</el-descriptions-item>
        <el-descriptions-item label="现任职务">{{ official.current_position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ official.status }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>履历时间线</template>
      <el-timeline>
        <el-timeline-item
          v-for="entry in (official.career_entries as Array<Record<string, unknown>>)"
          :key="entry.id as string"
          :timestamp="`${entry.start_year} - ${entry.end_year || '至今'}`"
        >
          <strong>{{ entry.entry_type }}</strong>：{{ entry.description }}
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>关联官员</template>
      <el-table :data="connections">
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="rel_type" label="关系类型" />
        <el-table-column prop="strength" label="关系强度">
          <template #default="{ row }">{{ (row.strength * 100).toFixed(0) }}%</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
