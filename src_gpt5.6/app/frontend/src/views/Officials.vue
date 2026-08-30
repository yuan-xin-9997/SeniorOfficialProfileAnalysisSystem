<template>
  <div>
    <div class="toolbar search-toolbar">
      <div class="search-box"><span>⌕</span><input v-model="keyword" placeholder="搜索姓名、职务或机构" @keyup.enter="search" /></div>
      <div class="button-row"><button @click="search">查询</button><button class="primary" @click="openCreate">＋ 新建履历</button></div>
    </div>

    <div class="filter-row">
      <span class="filter-label">状态</span>
      <button v-for="item in statuses" :key="item" :class="{ active: statusFilter === item }" @click="selectStatus(item)">{{ item || '全部' }}</button>
      <span class="muted">共 {{ total }} 人</span>
    </div>
    <div class="filter-row">
      <span class="filter-label">党内职务</span>
      <button v-for="item in partyRoles" :key="item" :class="{ active: partyRoleFilter === item }" @click="selectPartyRole(item)">{{ item || '全部' }}</button>
    </div>

    <div v-if="!officials.length" class="empty"><b>暂无履历档案</b><span>新建第一位高级官员的结构化履历。</span></div>
    <div v-else class="profile-grid">
      <article v-for="o in officials" :key="o.id" class="profile-card" @click="openDetail(o.id)">
        <div class="profile-avatar">{{ o.name.slice(0, 1) }}</div>
        <div class="profile-main">
          <div class="item-title"><h3>{{ o.name }}</h3><span :class="['pill', o.status === '在任' ? 'ok' : '']">{{ o.status }}</span></div>
          <strong class="position">{{ o.current_position || '职务待补充' }}</strong>
          <p>{{ o.organization || '机构待补充' }}</p>
          <div class="tags"><span v-for="tag in o.tags.slice(0, 3)" :key="tag">{{ tag }}</span></div>
        </div>
        <span class="profile-arrow">→</span>
      </article>
    </div>

    <div v-if="total > 0" class="toolbar" style="margin-top: 16px">
      <span class="muted">第 {{ page }} / {{ totalPages }} 页，每页 {{ pageSize }} 人</span>
      <div class="button-row">
        <button :disabled="page <= 1" @click="goToPage(page - 1)">上一页</button>
        <button :disabled="page >= totalPages" @click="goToPage(page + 1)">下一页</button>
      </div>
    </div>

    <div v-if="detail" class="modal" @click.self="detail = null">
      <div class="modal-card profile-detail">
        <div class="modal-head"><div><p class="eyebrow">OFFICIAL PROFILE</p><h2>{{ detail.name }}</h2></div><button @click="detail = null">×</button></div>
        <div class="detail-hero">
          <div class="profile-avatar large">{{ detail.name.slice(0, 1) }}</div>
          <div><h3>{{ detail.current_position || '职务待补充' }}</h3><p>{{ detail.organization }} · {{ detail.administrative_rank }}</p><span class="pill ok">{{ detail.status }}</span><span v-if="detail.party_role" class="pill role-pill">{{ detail.party_role }}</span></div>
        </div>
        <dl class="profile-facts"><dt>出生日期</dt><dd>{{ detail.birth_date || '-' }}</dd><dt>籍贯</dt><dd>{{ detail.native_place || '-' }}</dd><dt>民族</dt><dd>{{ detail.ethnicity || '-' }}</dd><dt>学历</dt><dd>{{ detail.education || '-' }}</dd></dl>
        <section class="summary"><h3>人物概述</h3><p>{{ detail.summary || '暂无概述' }}</p></section>
        <section><h3>履历时间轴</h3><div v-if="!detail.careers?.length" class="empty compact">暂无任职经历</div><div v-for="c in detail.careers" :key="c.id" class="career-row"><time>{{ c.start_date }} — {{ c.end_date }}</time><div><strong>{{ c.position }}</strong><p>{{ c.organization }}<span v-if="c.location"> · {{ c.location }}</span></p><small>{{ c.description }}</small></div></div></section>
        <div class="modal-actions"><button class="danger" @click="remove(detail)">删除</button><button @click="openEdit(detail)">编辑履历</button><button class="primary" @click="detail = null">关闭</button></div>
      </div>
    </div>

    <div v-if="editorOpen" class="modal" @click.self="editorOpen = false">
      <form class="modal-card large" @submit.prevent="save">
        <div class="modal-head"><div><p class="eyebrow">PROFILE EDITOR</p><h2>{{ form.id ? '编辑履历' : '新建履历' }}</h2></div><button type="button" @click="editorOpen = false">×</button></div>
        <div class="form-grid"><label>姓名<input v-model.trim="form.name" required /></label><label>状态<select v-model="form.status"><option>在任</option><option>离任</option><option>退休</option></select></label><label>党内职务<select v-model="form.party_role"><option value="">无</option><option>中央政治局常委</option><option>中央政治局委员</option><option>中央委员</option><option>中央候补委员</option></select></label><label>现任职务<input v-model="form.current_position" /></label><label>所属机构<input v-model="form.organization" /></label><label>行政级别<input v-model="form.administrative_rank" /></label><label>出生日期<input v-model="form.birth_date" type="date" /></label><label>籍贯<input v-model="form.native_place" /></label><label>民族<input v-model="form.ethnicity" /></label><label>学历<input v-model="form.education" /></label><label>标签（逗号分隔）<input v-model="tagText" /></label></div>
        <label>人物概述<textarea v-model="form.summary" rows="4"></textarea></label>
        <div class="panel-head career-title"><h2>任职经历</h2><button type="button" @click="addCareer">＋ 添加经历</button></div>
        <div v-for="(career, index) in form.careers" :key="index" class="career-editor"><div class="form-grid"><label>开始时间<input v-model="career.start_date" placeholder="2020.01" /></label><label>结束时间<input v-model="career.end_date" placeholder="至今" /></label><label>机构<input v-model="career.organization" /></label><label>职务<input v-model="career.position" required /></label></div><button type="button" class="danger link-button" @click="form.careers.splice(index, 1)">删除此经历</button></div>
        <div class="modal-actions"><button type="button" @click="editorOpen = false">取消</button><button class="primary">保存履历</button></div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { showToast } from '@/composables/toast'
import { createOfficialApi, deleteOfficialApi, getOfficialApi, listOfficialsApi, updateOfficialApi, type Career, type Official } from '@/api/officials'

const officials = ref<Official[]>([]); const total = ref(0); const keyword = ref(''); const statusFilter = ref(''); const partyRoleFilter = ref('')
const page = ref(1); const pageSize = 20; const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const statuses = ['', '在任', '离任', '退休']; const partyRoles = ['', '中央政治局常委', '中央政治局委员', '中央委员', '中央候补委员']
const detail = ref<Official | null>(null); const editorOpen = ref(false); const tagText = ref('')
const emptyCareer = (): Career => ({ start_date: '', end_date: '至今', organization: '', position: '', location: '', administrative_rank: '', description: '', sort_order: 0 })
const form = reactive<any>({ id: 0, name: '', gender: '', birth_date: '', ethnicity: '', native_place: '', education: '', current_position: '', organization: '', administrative_rank: '', status: '在任', party_role: '', summary: '', photo_url: '', source_url: '', tags: [], careers: [] })

onMounted(load)
async function load() {
  const data = await listOfficialsApi({ keyword: keyword.value, status: statusFilter.value, party_role: partyRoleFilter.value, page: page.value, page_size: pageSize })
  total.value = data.total
  if (page.value > totalPages.value) { page.value = totalPages.value; await load(); return }
  officials.value = data.items
}
async function search() { page.value = 1; await load() }
async function selectStatus(status: string) { statusFilter.value = status; page.value = 1; await load() }
async function selectPartyRole(role: string) { partyRoleFilter.value = role; page.value = 1; await load() }
async function goToPage(target: number) { if (target < 1 || target > totalPages.value || target === page.value) return; page.value = target; await load() }
async function openDetail(id: number) { detail.value = await getOfficialApi(id) }
function resetForm() { Object.assign(form, { id: 0, name: '', gender: '', birth_date: '', ethnicity: '', native_place: '', education: '', current_position: '', organization: '', administrative_rank: '', status: '在任', party_role: '', summary: '', photo_url: '', source_url: '', tags: [], careers: [] }); tagText.value = '' }
function openCreate() { resetForm(); editorOpen.value = true }
function openEdit(o: Official) { Object.assign(form, JSON.parse(JSON.stringify(o))); form.birth_date ||= ''; form.careers ||= []; tagText.value = o.tags.join(', '); detail.value = null; editorOpen.value = true }
function addCareer() { form.careers.push(emptyCareer()) }
async function save() { const payload = { ...form, birth_date: form.birth_date || null, tags: tagText.value.split(/[,，]/).map((v) => v.trim()).filter(Boolean) }; if (form.id) await updateOfficialApi(form.id, payload); else await createOfficialApi(payload); editorOpen.value = false; showToast('履历已保存'); await load() }
async function remove(o: Official) { if (!confirm(`确认删除「${o.name}」的履历？`)) return; await deleteOfficialApi(o.id); detail.value = null; showToast('履历已删除'); await load() }
</script>
