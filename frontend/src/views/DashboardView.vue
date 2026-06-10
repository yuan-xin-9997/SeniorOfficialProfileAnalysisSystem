<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import client, { type ApiResponse } from '@/api/client'

const stats = ref<{ total_officials: number; by_status: Record<string, number>; by_committee_term: Record<string, number> } | null>(null)
const chartRef = ref<HTMLDivElement>()

onMounted(async () => {
  const { data } = await client.get<ApiResponse>('/analysis/statistics')
  stats.value = data.data
  if (chartRef.value && stats.value) {
    const chart = echarts.init(chartRef.value)
    chart.setOption({
      title: { text: '官员状态分布' },
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: '60%',
          data: Object.entries(stats.value.by_status).map(([name, value]) => ({ name, value })),
        },
      ],
    })
  }
})
</script>

<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-title">官员总数</div>
          <div class="stat-value">{{ stats?.total_officials ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-title">届次数量</div>
          <div class="stat-value">{{ stats ? Object.keys(stats.by_committee_term).length : '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-title">在任官员</div>
          <div class="stat-value">{{ stats?.by_status?.active ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card style="margin-top: 16px">
      <div ref="chartRef" style="height: 360px" />
    </el-card>
  </div>
</template>

<style scoped>
.stat-title {
  color: #909399;
  font-size: 14px;
}
.stat-value {
  font-size: 32px;
  font-weight: 600;
  margin-top: 8px;
}
</style>
