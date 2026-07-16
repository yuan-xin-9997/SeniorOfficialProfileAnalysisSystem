<template>
  <div>
    <section class="metric-grid">
      <article><div class="metric-icon navy">人</div><div><span>履历总数</span><strong>{{ stats.official_count }}</strong><small>结构化人物档案</small></div></article>
      <article><div class="metric-icon green">任</div><div><span>在任官员</span><strong>{{ stats.active_count }}</strong><small>当前状态为在任</small></div></article>
      <article><div class="metric-icon amber">机</div><div><span>覆盖机构</span><strong>{{ stats.organization_count }}</strong><small>去重统计</small></div></article>
      <article><div class="metric-icon violet">联</div><div><span>人物关系</span><strong>{{ stats.relation_count }}</strong><small>{{ stats.career_count }} 条任职经历</small></div></article>
    </section>
    <section class="dashboard-grid">
      <div class="panel">
        <div class="panel-head"><div><p class="eyebrow">RECENT PROFILES</p><h2>最近更新履历</h2></div><button @click="$router.push('/officials')">查看全部 →</button></div>
        <div v-if="!stats.recent_officials.length" class="empty compact">暂无人物履历</div>
        <div v-for="o in stats.recent_officials" :key="o.id" class="recent-profile" @click="$router.push('/officials')"><div class="profile-avatar small-avatar">{{ o.name.slice(0, 1) }}</div><div><strong>{{ o.name }}</strong><p>{{ o.current_position || '职务待补充' }}</p></div><span>{{ o.organization || '-' }}</span><time>{{ o.updated_at.slice(0, 10) }}</time></div>
      </div>
      <div class="panel insight-panel">
        <div class="panel-head"><div><p class="eyebrow">DATA INSIGHT</p><h2>数据完整度提示</h2></div></div>
        <div class="insight-number">{{ completion }}<small>%</small></div><p>最近录入人物中，具备机构与现任职务信息的比例。</p>
        <div class="progress"><i :style="{ width: `${completion}%` }"></i></div>
        <div class="insight-actions"><button @click="$router.push('/info-sources')">管理采集源</button><button class="primary" @click="$router.push('/analysis-tasks')">运行智能分析</button></div>
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getDashboardApi, type DashboardStats } from '@/api/officials'
const stats = ref<DashboardStats>({ official_count: 0, active_count: 0, organization_count: 0, career_count: 0, relation_count: 0, recent_officials: [] })
const completion = computed(() => stats.value.recent_officials.length ? Math.round(stats.value.recent_officials.filter((o) => o.organization && o.current_position).length / stats.value.recent_officials.length * 100) : 0)
onMounted(async () => { stats.value = await getDashboardApi() })
</script>
