<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const showNav = computed(() => route.path !== '/login')

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container v-if="showNav" class="layout">
    <el-header class="header">
      <div class="brand">SOPAS 高级官员履历分析系统</div>
      <el-menu mode="horizontal" :router="true" :default-active="route.path" class="nav">
        <el-menu-item index="/dashboard">概览</el-menu-item>
        <el-menu-item index="/officials">官员列表</el-menu-item>
        <el-menu-item index="/network">关系网络</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/scraper">抓取管理</el-menu-item>
      </el-menu>
      <div class="user">
        <span>{{ auth.user?.username }}</span>
        <el-button link type="primary" @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
  <router-view v-else />
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid #eee;
  background: #fff;
}
.brand {
  font-weight: 600;
  white-space: nowrap;
}
.nav {
  flex: 1;
  border-bottom: none;
}
.user {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

<style>
body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background: #f5f7fa;
}
</style>
