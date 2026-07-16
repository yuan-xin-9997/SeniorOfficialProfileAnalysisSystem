<template>
  <main class="login-shell">
    <section class="login-brand">
      <div class="brand-mark">履</div>
      <p class="eyebrow">SENIOR OFFICIAL PROFILE ANALYSIS</p>
      <h1>读懂履历，<br /><span>看见关系与轨迹。</span></h1>
      <p>汇聚公开履历，结构化梳理任职轨迹、机构分布与人物关系，为研究判断提供可靠底座。</p>
      <div class="login-points">
        <span>履历档案</span><span>关系图谱</span><span>智能分析</span>
      </div>
    </section>
    <form class="login-card" @submit.prevent="onLogin">
      <div>
        <p class="eyebrow">WELCOME BACK</p>
        <h2>登录履历分析中心</h2>
        <p>账号由系统管理员在 password.txt 或权限页面维护。</p>
      </div>
      <label>用户名
        <input v-model.trim="form.username" autocomplete="username" autofocus required placeholder="请输入用户名" />
      </label>
      <label>密码
        <input v-model="form.password" type="password" autocomplete="current-password" required placeholder="请输入密码" />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="primary wide" :disabled="loading">{{ loading ? '登录中…' : '进入系统' }}</button>
      <small>默认部署账号请在首次登录后立即修改</small>
    </form>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '' })

async function onLogin() {
  if (!form.username || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.username, form.password)
    router.push('/dashboard')
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
