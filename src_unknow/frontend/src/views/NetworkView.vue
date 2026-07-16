<script setup lang="ts">
import { onMounted, ref } from 'vue'
import client, { type ApiResponse } from '@/api/client'

interface Official {
  id: string
  name: string
}

const officials = ref<Official[]>([])
const selectedId = ref('')
const connections = ref<Array<{ id: string; name: string; strength: number; rel_type: string }>>([])

onMounted(async () => {
  const { data } = await client.get<ApiResponse>('/officials', { params: { page_size: 100 } })
  officials.value = data.data.items
  if (officials.value.length) {
    selectedId.value = officials.value[0].id
    await loadConnections()
  }
})

async function loadConnections() {
  if (!selectedId.value) return
  const { data } = await client.get<ApiResponse>('/analysis/connections', {
    params: { official_id: selectedId.value, min_strength: 0.3 },
  })
  connections.value = data.data.connections || []
}
</script>

<template>
  <el-card>
    <template #header>关系网络</template>
    <el-select v-model="selectedId" filterable placeholder="选择官员" style="width: 240px; margin-bottom: 16px" @change="loadConnections">
      <el-option v-for="o in officials" :key="o.id" :label="o.name" :value="o.id" />
    </el-select>
    <div class="network-graph">
      <div class="center-node">{{ officials.find(o => o.id === selectedId)?.name || '中心' }}</div>
      <div class="connections">
        <div v-for="c in connections" :key="c.id" class="conn-node">
          <span>{{ c.name }}</span>
          <small>{{ c.rel_type }} · {{ (c.strength * 100).toFixed(0) }}%</small>
        </div>
        <el-empty v-if="!connections.length" description="暂无关联数据，请先添加官员或运行抓取任务" />
      </div>
    </div>
    <p class="hint">完整力导向图将在后续版本接入 D3.js 渲染</p>
  </el-card>
</template>

<style scoped>
.network-graph {
  min-height: 320px;
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
  padding: 24px;
  background: #fafafa;
}
.center-node {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  padding: 16px;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}
.connections {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}
.conn-node {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
  min-width: 120px;
}
.conn-node small {
  display: block;
  color: #909399;
  margin-top: 4px;
}
.hint {
  color: #909399;
  font-size: 12px;
  margin-top: 12px;
}
</style>
