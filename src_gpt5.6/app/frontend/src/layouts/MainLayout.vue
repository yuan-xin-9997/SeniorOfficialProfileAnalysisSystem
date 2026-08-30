<template>
  <div class="app-shell">
    <aside>
      <div class="logo">
        <div class="brand-mark small">履</div>
        <div><strong>高级官员履历</strong><small>SOPAS</small></div>
      </div>
      <nav>
        <button
          v-for="item in visibleMenus"
          :key="item.path"
          :class="{ active: activeMenu === item.path }"
          @click="go(item.path)"
        >
          <span>{{ item.icon }}</span>{{ item.title }}
        </button>
      </nav>
      <div class="account">
        <div class="avatar">{{ (auth.user?.username || '?').slice(0, 1).toUpperCase() }}</div>
        <div>
          <strong>{{ auth.user?.username }}</strong>
          <small>{{ auth.isAdmin ? '管理员' : '普通用户' }} · v{{ appVersion }}</small>
        </div>
        <button title="退出" @click="onLogout">↗</button>
      </div>
    </aside>

    <section class="workspace">
      <header>
        <div>
          <p class="eyebrow">SENIOR OFFICIAL PROFILE ANALYSIS</p>
          <h1>{{ currentTitle[0] }}</h1>
          <p>{{ currentTitle[1] }}</p>
        </div>
        <div class="header-status" :class="{ down: !serviceOk }">
          <i></i>{{ serviceOk ? '服务运行中' : '服务异常' }}
        </div>
      </header>
      <section class="content">
        <router-view />
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import request from '@/api/request'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const serviceOk = ref(true)
const appVersion = ref('…')

const allMenus = [
  { path: '/dashboard', page: 'dashboard', icon: '概', title: '概览' },
  { path: '/officials', page: 'officials', icon: '人', title: '履历档案' },
  { path: '/timeline', page: 'timeline', icon: '时', title: '时间线' },
  { path: '/relations', page: 'relations', icon: '网', title: '关系图谱' },
  { path: '/info-sources', page: 'info_sources', icon: '源', title: '信息源管理' },
  { path: '/analysis', icon: '析', page: 'analysis', title: '智能分析' },
  { path: '/task-center', icon: '务', page: 'task_center', title: '任务中心' },
  { path: '/permission', icon: '权', page: 'permission', title: '权限管理' },
  { path: '/system-config', icon: '置', page: 'system_config', title: '系统配置' },
]

const pageMeta: Record<string, [string, string]> = {
  dashboard: ['概览', '信息源、分析任务与最近运行的整体情况'],
  officials: ['履历档案', '检索、维护和浏览高级官员结构化履历'],
  timeline: ['时间线', '按年月对齐并横向比较多位人物的任职履历'],
  relations: ['关系图谱', '发现人物之间的同事、上下级与地域关系'],
  info_sources: ['信息源管理', '管理履历采集所需的官方网站、本地文件夹与 FreshRSS'],
  analysis: ['智能分析', '绑定信息源触发智能分析，并查看逐条与汇总结果'],
  task_center: ['任务中心', '查看采集、分析与履历刷新任务的运行状态及日志'],
  permission: ['权限管理', '维护用户角色与可访问页面'],
  system_config: ['系统配置', '查看运行配置（敏感字段已脱敏）'],
}

const visibleMenus = computed(() => allMenus.filter((m) => auth.pages.includes(m.page)))
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => {
  const page = (route.meta.page as string) || 'dashboard'
  return pageMeta[page] || ['', '']
})

function go(path: string) {
  router.push(path)
}

function onLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  try {
    const health = await request.get<unknown, { status: string; version?: string }>('/api/health')
    serviceOk.value = health?.status === 'ok'
    if (health?.version) appVersion.value = health.version
  } catch {
    serviceOk.value = false
  }
})
</script>
